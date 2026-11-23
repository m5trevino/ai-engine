"""
BUCKET API — Direct REST access to project buckets and bucket-based generation.

Buckets are working memory sets. You can:
  - Add unlimited documents from memory vault
  - Remove or edit any document
  - Compile into a payload for the Aviary pipeline
  - View token counts and chunk into any size
  - Feed directly to PEACOCK's 7-bird pipeline
"""

import uuid
import json
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.db.database import ProjectBucketDB
from app.core.groq_tool_engine import (
    _ensure_bucket,
    _save_bucket,
    _add_search_to_bucket,
    _add_doc_to_bucket,
    _bucket_summary,
    _get_bucket_item,
    _generate_from_bucket,
)
from app.core.project_engine import generate_project, ProjectConfig, project_result_to_json
from app.core.aviary import run_aviary_pipeline_streamed, result_to_json, AviaryResult
from app.config import MODEL_REGISTRY

router = APIRouter()

# In-memory stores
_GENERATION_JOBS: Dict[str, Any] = {}
_AVIARY_JOBS: Dict[str, AviaryResult] = {}


# ─── Helpers ──────────────────────────────────────────────────────────

def _count_tokens(text: str) -> int:
    """Approximate token count. ~4 chars per token."""
    return max(1, len(text) // 4)


def _compile_bucket_payload(bucket_name: str, separator: str = "\n\n=== DOC BREAK ===\n\n") -> Dict[str, Any]:
    """Compile all bucket items into a single payload string."""
    bucket = ProjectBucketDB.load_bucket(bucket_name)
    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found")
    
    items = bucket.get("items", {})
    if not items:
        return {"payload": "", "items": 0, "total_chars": 0, "total_tokens": 0, "chunks": []}
    
    parts = []
    item_meta = []
    for doc_id, item in items.items():
        content = item.get("content", "")
        note = item.get("note", "")
        meta = item.get("metadata", {})
        header = f"--- {doc_id} ---"
        if note:
            header += f" [note: {note}]"
        parts.append(f"{header}\n{content}")
        item_meta.append({
            "doc_id": doc_id,
            "collection": item.get("collection", ""),
            "chars": len(content),
            "tokens": _count_tokens(content),
            "note": note,
        })
    
    payload = separator.join(parts)
    total_tokens = _count_tokens(payload)
    
    return {
        "payload": payload,
        "items": len(items),
        "total_chars": len(payload),
        "total_tokens": total_tokens,
        "item_breakdown": item_meta,
    }


# ─── Request Models ───────────────────────────────────────────────────

class CreateBucketRequest(BaseModel):
    name: str
    description: Optional[str] = ""


class SearchFillRequest(BaseModel):
    bucket_name: str
    query: str
    collections: Optional[List[str]] = None
    n_results: int = 10


class AddDocRequest(BaseModel):
    bucket_name: str
    collection: str
    doc_id: str
    note: Optional[str] = ""


class AddRawRequest(BaseModel):
    doc_id: str
    content: str
    original_content: Optional[str] = None
    collection: Optional[str] = "raw"
    note: Optional[str] = ""


class UpdateDocRequest(BaseModel):
    content: Optional[str] = None
    note: Optional[str] = None


class RevertDocRequest(BaseModel):
    pass


class CompileRequest(BaseModel):
    separator: Optional[str] = "\n\n=== DOC BREAK ===\n\n"


class ChunkRequest(BaseModel):
    max_tokens_per_chunk: int = Field(default=4000, description="Max tokens per chunk")
    separator: Optional[str] = "\n\n=== CHUNK BREAK ===\n\n"


class GenerateFromBucketRequest(BaseModel):
    bucket_name: str
    description: str
    project_type_hint: Optional[str] = None
    model: Optional[str] = "llama-3.3-70b-versatile"


class AviaryFromBucketRequest(BaseModel):
    description: str = Field(default="", description="Optional override description")
    enable_memory: bool = Field(default=True)
    memory_collections: Optional[List[str]] = None


# ─── BUCKET CRUD ──────────────────────────────────────────────────────

@router.post("/create")
async def create_bucket(req: CreateBucketRequest):
    """Create a new project bucket."""
    bucket = _ensure_bucket(req.name)
    bucket["description"] = req.description or ""
    _save_bucket(req.name)
    return {"status": "ok", "bucket_name": req.name, "description": bucket["description"]}


@router.get("/list")
async def list_buckets():
    """List all project buckets with doc counts."""
    buckets = ProjectBucketDB.list_buckets()
    result = []
    for b in buckets:
        full = ProjectBucketDB.load_bucket(b["name"])
        item_count = len(full["items"]) if full else 0
        result.append({
            "name": b["name"],
            "description": b.get("description", ""),
            "item_count": item_count,
            "created_at": b.get("created_at", ""),
            "updated_at": b.get("updated_at", ""),
        })
    return {"buckets": result, "total": len(result)}


@router.get("/{bucket_name}")
async def get_bucket(bucket_name: str):
    """Get a single bucket with all items."""
    bucket = ProjectBucketDB.load_bucket(bucket_name)
    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found")
    return bucket


@router.delete("/{bucket_name}")
async def delete_bucket(bucket_name: str):
    """Delete a bucket."""
    ProjectBucketDB.delete_bucket(bucket_name)
    return {"status": "ok", "deleted": bucket_name}


# ─── BUCKET OPERATIONS ────────────────────────────────────────────────

@router.post("/{bucket_name}/search")
async def search_and_fill(bucket_name: str, req: SearchFillRequest):
    """Search memory and add results to a bucket."""
    result = await _add_search_to_bucket(
        name=bucket_name,
        query=req.query,
        collections=req.collections,
        n=req.n_results,
    )
    return {"status": "ok", "result": result}


@router.post("/{bucket_name}/add")
async def add_document(bucket_name: str, req: AddDocRequest):
    """Add a specific document to a bucket by ID."""
    result = await _add_doc_to_bucket(
        name=bucket_name,
        collection=req.collection,
        doc_id=req.doc_id,
        note=req.note,
    )
    return {"status": "ok", "result": result}


@router.post("/{bucket_name}/add-raw")
async def add_raw_document(bucket_name: str, req: AddRawRequest):
    """Add raw content to a bucket, preserving original for revert."""
    bucket = _ensure_bucket(bucket_name)
    bucket["items"][req.doc_id] = {
        "collection": req.collection or "raw",
        "content": req.content,
        "original_content": req.original_content or req.content,
        "metadata": {},
        "note": req.note or "",
        "edited": False,
    }
    _save_bucket(bucket_name)
    return {"status": "ok", "added": req.doc_id, "chars": len(req.content)}


@router.post("/{bucket_name}/remove/{doc_id}")
async def remove_document(bucket_name: str, doc_id: str):
    """Remove a document from a bucket."""
    bucket = ProjectBucketDB.load_bucket(bucket_name)
    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found")
    
    items = bucket.get("items", {})
    if doc_id not in items:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not in bucket")
    
    del items[doc_id]
    ProjectBucketDB.save_bucket(bucket_name, bucket.get("description", ""), items)
    return {"status": "ok", "removed": doc_id, "remaining": len(items)}


@router.post("/{bucket_name}/update/{doc_id}")
async def update_document(bucket_name: str, doc_id: str, req: UpdateDocRequest):
    """Update a document's content or note in a bucket."""
    bucket = ProjectBucketDB.load_bucket(bucket_name)
    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found")
    
    items = bucket.get("items", {})
    if doc_id not in items:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not in bucket")
    
    if req.content is not None:
        items[doc_id]["content"] = req.content
        items[doc_id]["edited"] = True
        # Ensure original_content exists (backfill for old buckets)
        if "original_content" not in items[doc_id]:
            items[doc_id]["original_content"] = req.content
    if req.note is not None:
        items[doc_id]["note"] = req.note
    
    ProjectBucketDB.save_bucket(bucket_name, bucket.get("description", ""), items)
    return {"status": "ok", "updated": doc_id}


@router.post("/{bucket_name}/revert/{doc_id}")
async def revert_document(bucket_name: str, doc_id: str):
    """Revert a bucket item to its original untouched content from the database."""
    bucket = ProjectBucketDB.load_bucket(bucket_name)
    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found")
    
    items = bucket.get("items", {})
    if doc_id not in items:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not in bucket")
    
    item = items[doc_id]
    if "original_content" not in item:
        raise HTTPException(status_code=400, detail=f"Document '{doc_id}' has no original content stored")
    
    item["content"] = item["original_content"]
    item["edited"] = False
    
    ProjectBucketDB.save_bucket(bucket_name, bucket.get("description", ""), items)
    return {"status": "ok", "reverted": doc_id}


@router.get("/{bucket_name}/summary")
async def bucket_summary(bucket_name: str):
    """Get text summary and item list for a bucket."""
    summary = _bucket_summary(bucket_name)
    return {"summary": summary}


@router.get("/{bucket_name}/item/{doc_id}")
async def get_bucket_item(bucket_name: str, doc_id: str):
    """Get full content of a document from a bucket."""
    result = await _get_bucket_item(name=bucket_name, doc_id=doc_id)
    return {"status": "ok", "content": result}


# ─── PAYLOAD BUILDER — Token counts, compile, chunk ───────────────────

@router.get("/{bucket_name}/tokens")
async def bucket_tokens(bucket_name: str):
    """Get structured token breakdown for every item in a bucket."""
    bucket = ProjectBucketDB.load_bucket(bucket_name)
    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found")
    
    items = bucket.get("items", {})
    breakdown = []
    total_tokens = 0
    total_chars = 0
    
    for doc_id, item in items.items():
        content = item.get("content", "")
        tokens = _count_tokens(content)
        chars = len(content)
        total_tokens += tokens
        total_chars += chars
        breakdown.append({
            "doc_id": doc_id,
            "collection": item.get("collection", ""),
            "chars": chars,
            "tokens": tokens,
            "note": item.get("note", ""),
        })
    
    return {
        "bucket": bucket_name,
        "items": len(items),
        "total_chars": total_chars,
        "total_tokens": total_tokens,
        "breakdown": breakdown,
    }


@router.post("/{bucket_name}/compile")
async def compile_bucket(bucket_name: str, req: CompileRequest):
    """Compile all bucket items into a single payload string."""
    result = _compile_bucket_payload(bucket_name, req.separator or "\n\n=== DOC BREAK ===\n\n")
    return {"status": "ok", **result}


@router.post("/{bucket_name}/chunk")
async def chunk_bucket(bucket_name: str, req: ChunkRequest):
    """Split bucket payload into token-sized chunks."""
    compiled = _compile_bucket_payload(bucket_name, "\n\n")
    payload = compiled["payload"]
    
    if not payload:
        return {"status": "ok", "chunks": [], "chunk_count": 0, "total_tokens": 0}
    
    max_tokens = req.max_tokens_per_chunk
    max_chars = max_tokens * 4  # approximate
    separator = req.separator or "\n\n=== CHUNK BREAK ===\n\n"
    
    # Simple greedy chunking at paragraph boundaries
    paragraphs = payload.split("\n\n")
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    for para in paragraphs:
        para_tokens = _count_tokens(para)
        if current_tokens + para_tokens > max_tokens and current_chunk:
            chunks.append(separator.join(current_chunk))
            current_chunk = [para]
            current_tokens = para_tokens
        else:
            current_chunk.append(para)
            current_tokens += para_tokens
    
    if current_chunk:
        chunks.append(separator.join(current_chunk))
    
    return {
        "status": "ok",
        "chunks": chunks,
        "chunk_count": len(chunks),
        "total_tokens": compiled["total_tokens"],
        "max_tokens_per_chunk": max_tokens,
    }


# ─── GENERATION FROM BUCKET (Legacy Project Engine) ───────────────────

@router.post("/{bucket_name}/generate")
async def generate_from_bucket(
    bucket_name: str,
    req: GenerateFromBucketRequest,
    background_tasks: BackgroundTasks,
):
    """Generate a project from bucket contents using legacy project engine."""
    job_id = f"gen_{uuid.uuid4().hex[:12]}"
    
    model_id = req.model or "llama-3.3-70b-versatile"
    model_cfg = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if not model_cfg:
        raise HTTPException(status_code=400, detail=f"Unknown model: {model_id}")
    
    async def _run():
        from app.core.project_engine import ProjectResult
        placeholder = ProjectResult(
            config=ProjectConfig(
                name=bucket_name,
                description=req.description,
                model=model_id,
                gateway=model_cfg.gateway,
            ),
            status="pending",
        )
        _GENERATION_JOBS[job_id] = placeholder
        
        bucket = ProjectBucketDB.load_bucket(bucket_name)
        research = ""
        if bucket and bucket.get("items"):
            lines = [f"=== BUCKET RESEARCH: {bucket_name} ===", ""]
            for did, item in bucket["items"].items():
                lines.append(f"--- {did} ({item.get('collection','')}) ---")
                lines.append(item.get("content", ""))
                lines.append("")
            research = "\n".join(lines)
        
        config = ProjectConfig(
            name=bucket_name,
            description=req.description,
            model=model_id,
            gateway=model_cfg.gateway,
            temperature=0.3,
            max_iterations=3,
            files_per_batch=3,
            enable_memory=False,
            project_type_hint=req.project_type_hint,
            research_context=research,
        )
        full_result = await generate_project(config)
        _GENERATION_JOBS[job_id] = full_result
    
    background_tasks.add_task(_run)
    
    return {
        "status": "started",
        "project_id": job_id,
        "bucket_name": bucket_name,
        "description": req.description,
    }


# ─── AVIARY PIPELINE FROM BUCKET ──────────────────────────────────────

@router.post("/{bucket_name}/aviary")
async def aviary_from_bucket(
    bucket_name: str,
    req: AviaryFromBucketRequest,
    background_tasks: BackgroundTasks,
):
    """Feed bucket contents to PEACOCK's 7-bird Aviary pipeline."""
    compiled = _compile_bucket_payload(bucket_name)
    if not compiled["payload"]:
        raise HTTPException(status_code=400, detail=f"Bucket '{bucket_name}' is empty. Add documents first.")
    
    run_id = f"aviary_{uuid.uuid4().hex[:12]}"
    
    # Extract metadata from bucket items for SPARK
    bucket = ProjectBucketDB.load_bucket(bucket_name)
    bucket_metadata = []
    for doc_id, item in bucket.get("items", {}).items():
        bucket_metadata.append({
            "doc_id": doc_id,
            "collection": item.get("collection", "raw"),
            "metadata": item.get("metadata", {}),
        })
    
    async def _run():
        result = await run_aviary_pipeline_streamed(
            chat_log_text=compiled["payload"],
            conversation_id=f"bucket:{bucket_name}",
            source_path=bucket_name,
            enable_memory=req.enable_memory,
            memory_collections=req.memory_collections,
            bucket_metadata=bucket_metadata,
        )
        # Drain the async generator to completion
        async for _ in result:
            pass
    
    background_tasks.add_task(_run)
    
    return {
        "status": "started",
        "run_id": run_id,
        "bucket_name": bucket_name,
        "payload_tokens": compiled["total_tokens"],
        "payload_items": compiled["items"],
        "message": "PEACOCK launched the birds from bucket contents",
    }


@router.post("/{bucket_name}/aviary/stream")
async def aviary_from_bucket_stream(bucket_name: str, req: AviaryFromBucketRequest):
    """Feed bucket contents to PEACOCK's 7-bird Aviary pipeline with real-time SSE streaming."""
    compiled = _compile_bucket_payload(bucket_name)
    if not compiled["payload"]:
        raise HTTPException(status_code=400, detail=f"Bucket '{bucket_name}' is empty. Add documents first.")
    
    # Extract metadata from bucket items for SPARK
    bucket = ProjectBucketDB.load_bucket(bucket_name)
    bucket_metadata = []
    for doc_id, item in bucket.get("items", {}).items():
        bucket_metadata.append({
            "doc_id": doc_id,
            "collection": item.get("collection", "raw"),
            "metadata": item.get("metadata", {}),
        })
    
    async def event_generator():
        async for event in run_aviary_pipeline_streamed(
            chat_log_text=compiled["payload"],
            conversation_id=f"bucket:{bucket_name}",
            source_path=bucket_name,
            enable_memory=req.enable_memory,
            memory_collections=req.memory_collections,
            bucket_metadata=bucket_metadata,
        ):
            yield event
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
