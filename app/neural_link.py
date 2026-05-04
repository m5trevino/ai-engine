"""
Neural Link session context endpoint.
Provides real-time session stats for the chat UI.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from app.config import MODEL_REGISTRY
from app.utils.token_counter import PeacockTokenCounter

router = APIRouter()

class SessionMessage(BaseModel):
    role: str
    content: str

class SessionContextRequest(BaseModel):
    model: str
    messages: List[SessionMessage]
    active_streams: Optional[int] = 0

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
