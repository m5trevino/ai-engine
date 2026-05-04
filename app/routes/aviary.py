"""
AVIARY API — The Bird Pipeline
Real-time streaming project generation from chat logs.
"""

import uuid
import json
import httpx
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.core.aviary import (
    run_aviary_pipeline,
    run_aviary_pipeline_streamed,
    result_to_json,
    get_aviary_result,
    AviaryResult,
)

# Peacock Unified DB endpoint
UNIFIED_API = "http://localhost:8000"

router = APIRouter()

# In-memory store for aviary runs
_AVIARY_JOBS: Dict[str, AviaryResult] = {}


class AviaryRequest(BaseModel):
    chat_log_text: str = Field(..., description="Raw markdown chat log content")
    conversation_id: Optional[str] = Field(default=None, description="Optional conversation ID")
    source_path: Optional[str] = Field(default=None, description="Optional source file path")
    enable_memory: bool = Field(default=True, description="Query Peacock Unified for existing invariants")
    memory_collections: Optional[List[str]] = Field(default=None, description="Collections to query")
    model_id: Optional[str] = Field(default=None, description="Model ID for SPARK phase (e.g., 'models/gemini-2.5-pro' or 'llama-3.3-70b-versatile')")
    gateway: Optional[str] = Field(default=None, description="Gateway for SPARK phase ('google' or 'groq')")
    bucket_metadata: Optional[List[Dict[str, Any]]] = Field(default=None, description="Structured bucket metadata for SPARK (doc_id, collection, metadata)")


@router.post("/compile")
async def start_compile(req: AviaryRequest, background_tasks: BackgroundTasks):
    """Start an Aviary run from a chat log. Returns immediately; poll /compile/{id} for results."""
    run_id = f"aviary_{uuid.uuid4().hex[:12]}"
    
    async def _run():
        result = await run_aviary_pipeline(
            chat_log_text=req.chat_log_text,
            conversation_id=req.conversation_id or "",
            source_path=req.source_path or "",
            enable_memory=req.enable_memory,
            memory_collections=req.memory_collections,
            model_id=req.model_id,
            gateway=req.gateway,
            bucket_metadata=req.bucket_metadata,
        )
        _AVIARY_JOBS[run_id] = result
    
    background_tasks.add_task(_run)
    
    return {
        "status": "started",
        "run_id": run_id,
        "message": "PEACOCK launched the birds: SPARK → FALCON → EAGLE → CROW → OWL → RAVEN → HAWK",
    }


@router.post("/compile/stream")
async def stream_compile(req: AviaryRequest):
    """Start an Aviary run with real-time SSE streaming. Watch every bird live."""
    async def event_generator():
        async for event in run_aviary_pipeline_streamed(
            chat_log_text=req.chat_log_text,
            conversation_id=req.conversation_id or "",
            source_path=req.source_path or "",
            enable_memory=req.enable_memory,
            memory_collections=req.memory_collections,
            model_id=req.model_id,
            gateway=req.gateway,
            bucket_metadata=req.bucket_metadata,
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


@router.get("/compile/{run_id}")
async def get_compile_status(run_id: str):
    """Get the status and results of an Aviary run."""
    result = _AVIARY_JOBS.get(run_id) or get_aviary_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Aviary run not found")
    
    return result_to_json(result)


@router.get("/compile/{run_id}/file/{file_path:path}")
async def get_compile_file(run_id: str, file_path: str):
    """Get a specific generated file from an Aviary run."""
    result = _AVIARY_JOBS.get(run_id) or get_aviary_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Aviary run not found")
    
    for f in result.files:
        if f["path"] == file_path:
            return {"path": f["path"], "content": f["content"]}
    
    raise HTTPException(status_code=404, detail=f"File '{file_path}' not found")


@router.get("/compile/{run_id}/deploy")
async def get_compile_deploy(run_id: str):
    """Get the deploy script from an Aviary run."""
    result = _AVIARY_JOBS.get(run_id) or get_aviary_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Aviary run not found")
    
    return {"deploy_script": result.deploy_script, "readme": result.readme}


@router.get("/compile/{run_id}/raven")
async def get_raven_audit(run_id: str):
    """Get the Raven audit log from an Aviary run."""
    result = _AVIARY_JOBS.get(run_id) or get_aviary_result(run_id)
    if not result:
        raise HTTPException(status_code=404, detail="Aviary run not found")
    
    return {
        "raven_approved": result.raven_approved,
        "audit_log": result.raven_audit_log,
        "issues_found": sum(a.get("issues", 0) for a in result.raven_audit_log),
        "critical_issues": sum(a.get("critical", 0) for a in result.raven_audit_log),
        "attempts": len(result.raven_audit_log),
    }


@router.get("/runs")
async def list_runs():
    """List all completed PEACOCK runs in memory."""
    runs = []
    for run_id, result in _AVIARY_JOBS.items():
        runs.append({
            "run_id": run_id,
            "status": result.status,
            "file_count": len(result.files),
            "raven_approved": result.raven_approved,
            "duration_ms": result.total_duration_ms,
        })
    return {"runs": runs}


@router.get("/search")
async def search_memory(
    q: str = Query(..., description="Search query"),
    collections: str = Query("chat_conversations,tech_vault,seed_vault,personal_vault,case_files_vault", description="Comma-separated collections"),
    n: int = Query(10, description="Number of results per collection"),
):
    """Search Peacock Unified memory vault. Returns results from all requested collections."""
    try:
        coll_list = [c.strip() for c in collections.split(",") if c.strip()]
        all_results = {}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for coll in coll_list:
                try:
                    resp = await client.get(
                        f"{UNIFIED_API}/api/search",
                        params={"q": q, "collections": coll, "n": n},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if coll in data:
                            all_results[coll] = data[coll]
                except Exception:
                    pass
        
        return {"query": q, "results": all_results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Memory search failed: {e}")


@router.get("/assembly")
async def assemble_document(
    collection: str = Query(..., description="Collection name"),
    doc_id: str = Query(..., description="Document ID"),
):
    """
    Assemble the FULL source document from all chunks.
    
    Vault collections chunk large files during ingestion. This endpoint
    finds all chunks from the same source file and concatenates them
    in order. ZERO truncation.
    """
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Step 1: Get the selected doc's metadata to find source file
            resp = await client.get(f"{UNIFIED_API}/api/document/{collection}/{doc_id}")
            if resp.status_code != 200:
                raise HTTPException(status_code=404, detail=f"Document {doc_id} not found in {collection}")
            
            doc = resp.json()
            meta = doc.get("metadata", {})
            source_file = meta.get("file", "")
            
            # Step 2: If no source file, return the raw doc with a warning
            if not source_file:
                return {
                    "doc_id": doc_id,
                    "collection": collection,
                    "source_file": None,
                    "is_fragment": True,
                    "warning": "This document has no source file metadata. It may be a mined fragment.",
                    "content": doc.get("document", ""),
                    "chars": len(doc.get("document", "")),
                    "tokens": max(1, len(doc.get("document", "")) // 4),
                    "chunks_found": 1,
                }
            
            # Step 3: Fetch ALL chunks from the same source file
            where_json = json.dumps({"file": source_file})
            resp = await client.get(
                f"{UNIFIED_API}/api/documents",
                params={"collection_name": collection, "where": where_json, "limit": 500},
            )
            if resp.status_code != 200:
                # Fallback: just return the single doc
                return {
                    "doc_id": doc_id,
                    "collection": collection,
                    "source_file": source_file,
                    "is_fragment": False,
                    "content": doc.get("document", ""),
                    "chars": len(doc.get("document", "")),
                    "tokens": max(1, len(doc.get("document", "")) // 4),
                    "chunks_found": 1,
                }
            
            data = resp.json()
            chunks = data.get("items", [])
            
            # Step 4: Sort by entry number and concatenate
            def sort_key(item):
                entry = item.get("metadata", {}).get("entry", "000")
                try:
                    return int(entry)
                except ValueError:
                    return entry
            
            chunks.sort(key=sort_key)
            
            full_text = "\n\n".join([c.get("document", "") for c in chunks])
            total_chars = len(full_text)
            total_tokens = max(1, total_chars // 4)
            
            return {
                "doc_id": doc_id,
                "collection": collection,
                "source_file": source_file,
                "is_fragment": False,
                "content": full_text,
                "chars": total_chars,
                "tokens": total_tokens,
                "chunks_found": len(chunks),
                "chunk_sizes": [len(c.get("document", "")) for c in chunks],
            }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assembly failed: {e}")


@router.get("/recent")
async def recent_memory(
    collection: str = Query("chat_conversations", description="Collection to browse"),
    n: int = Query(20, description="Number of recent items"),
):
    """Get recent documents from a collection by browsing with empty query."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{UNIFIED_API}/api/search",
                params={"q": "app", "collections": collection, "n": n},
            )
            if resp.status_code == 200:
                data = resp.json()
                return {"collection": collection, "results": data.get(collection, [])}
            return {"collection": collection, "results": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Recent fetch failed: {e}")


@router.get("/", response_class=HTMLResponse)
async def aviary_ui():
    """Serve the Aviary pipeline UI."""
    ui_path = os.path.join(os.path.dirname(__file__), "..", "static", "neural-link", "aviary.html")
    if os.path.exists(ui_path):
        with open(ui_path, "r", encoding="utf-8") as f:
            return f.read()
    raise HTTPException(status_code=404, detail="Aviary UI not found")
