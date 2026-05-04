"""
NEURAL LINK — Memory-Augmented Session Context
Provides real-time session stats AND Peacock Unified memory controls.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.config import MODEL_REGISTRY
from app.utils.token_counter import PeacockTokenCounter
from app.core.memory_engine import query_memory, get_memory_stats, DEFAULT_COLLECTIONS
from app.db.database import MemoryFeedbackDB

router = APIRouter()


class SessionMessage(BaseModel):
    role: str
    content: str


class SessionContextRequest(BaseModel):
    model: str
    messages: List[SessionMessage]
    active_streams: Optional[int] = 0


class MemoryQueryRequest(BaseModel):
    query: str
    collections: Optional[List[str]] = None
    n: int = 5


class MemoryConfigResponse(BaseModel):
    status: str
    collections: List[str]
    total_documents: int


class MemoryFeedbackRequest(BaseModel):
    conversation_id: Optional[str] = None
    query: str
    doc_id: str
    collection: str
    rating: int  # +1 or -1
    note: Optional[str] = None


@router.post("/session")
async def get_session_context(req: SessionContextRequest):
    model_cfg = next((m for m in MODEL_REGISTRY if m.id == req.model), None)
    
    full_text = "\n".join([f"{m.role}: {m.content}" for m in req.messages])
    try:
        tokens = PeacockTokenCounter.count_prompt_tokens(req.model, full_text, [])
    except Exception:
        tokens = len(full_text.split())  # fallback
    
    input_price = model_cfg.input_price_1m if model_cfg and model_cfg.input_price_1m else 0.0
    cost = (tokens / 1_000_000) * input_price
    
    return {
        "tokens": tokens,
        "cost": round(cost, 4),
        "active_streams": req.active_streams or 0,
        "model": req.model,
        "gateway": model_cfg.gateway if model_cfg else "unknown"
    }


@router.post("/memory/query")
async def memory_query(req: MemoryQueryRequest):
    """Direct memory query against Peacock Unified ChromaDB."""
    result = await query_memory(
        query=req.query,
        collections=req.collections,
        n=req.n,
    )
    return result


@router.get("/memory/stats")
async def memory_stats():
    """Get Peacock Unified memory collection statistics."""
    stats = await get_memory_stats()
    total = 0
    for name, info in stats.items():
        if isinstance(info, dict):
            total += info.get("count", 0)
    return {
        "collections": stats,
        "total_documents": total,
        "available_collections": DEFAULT_COLLECTIONS,
    }


@router.get("/memory/config")
async def memory_config():
    """Get memory system configuration."""
    stats = await get_memory_stats()
    total = sum(info.get("count", 0) for info in stats.values() if isinstance(info, dict))
    return MemoryConfigResponse(
        status="online",
        collections=DEFAULT_COLLECTIONS,
        total_documents=total,
    )


@router.post("/memory/feedback")
async def memory_feedback(req: MemoryFeedbackRequest):
    """Record manual thumbs up/down for a retrieved memory document."""
    if req.rating not in (-1, 1):
        return {"status": "error", "detail": "rating must be +1 or -1"}
    MemoryFeedbackDB.record_feedback(
        conversation_id=req.conversation_id,
        query=req.query,
        doc_id=req.doc_id,
        collection=req.collection,
        rating=req.rating,
        note=req.note or "",
    )
    return {"status": "ok", "rating": req.rating}


@router.get("/memory/feedback/stats")
async def memory_feedback_stats():
    """Get aggregate memory feedback statistics."""
    return MemoryFeedbackDB.get_stats()
