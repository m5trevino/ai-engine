"""
CODEBASE API — Deep-dive directory analysis & ingestion
"""

import os
import uuid
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.db.database import CodebaseScanDB
from app.core.codebase_analyzer import run_codebase_scan, query_codebase_vault

router = APIRouter()


class ScanRequest(BaseModel):
    source_path: str = Field(..., description="Absolute path to the codebase directory")
    project_name: Optional[str] = Field(default=None, description="Override project name")


class ScanStatusResponse(BaseModel):
    scan_id: str
    status: str
    progress_pct: float
    project_name: str
    total_files: int
    total_lines: int
    docs_ingested: int
    error: Optional[str]
    created_at: str
    updated_at: str


class ScanListResponse(BaseModel):
    scans: List[Dict[str, Any]]
    total: int


class CodebaseQueryRequest(BaseModel):
    query: str
    n: int = 5


# ── Active scan jobs (in-memory state for progress tracking) ─────────

_ACTIVE_SCANS: Dict[str, Any] = {}


def _persist_scan(scan):
    """Callback passed to the analyzer to persist state."""
    try:
        CodebaseScanDB.update(scan)
    except Exception:
        pass


async def _run_scan_task(scan_id: str, source_path: str, project_name: str):
    """Background task wrapper for a scan."""
    scan = await run_codebase_scan(
        source_path=source_path,
        scan_id=scan_id,
        db_callback=_persist_scan,
    )
    _ACTIVE_SCANS[scan_id] = scan


# ── Routes ───────────────────────────────────────────────────────────

@router.post("/scan")
async def start_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    """Start a new codebase analysis scan. Returns immediately; poll /scan/{id} for status."""
    path = os.path.abspath(os.path.expanduser(req.source_path))
    if not os.path.exists(path):
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")
    
    scan_id = f"scan_{uuid.uuid4().hex[:12]}"
    project_name = req.project_name or os.path.basename(path)
    
    CodebaseScanDB.create(scan_id, path, project_name)
    
    background_tasks.add_task(_run_scan_task, scan_id, path, project_name)
    
    return {
        "status": "started",
        "scan_id": scan_id,
        "source_path": path,
        "project_name": project_name,
    }


@router.get("/scan/{scan_id}")
async def get_scan_status(scan_id: str):
    """Get the current status of a scan job."""
    scan = CodebaseScanDB.get(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/scans")
async def list_scans(limit: int = 50):
    """List all codebase scans, most recent first."""
    scans = CodebaseScanDB.list_scans(limit=limit)
    return {"scans": scans, "total": len(scans)}


@router.post("/query")
async def query_codebase(req: CodebaseQueryRequest):
    """Semantic search across all analyzed codebases."""
    result = await query_codebase_vault(req.query, n=req.n)
    return result


@router.get("/stats")
async def codebase_stats():
    """Quick stats on codebase vault contents."""
    from app.core.memory_engine import get_memory_stats
    stats = await get_memory_stats()
    cb_stats = stats.get("codebase_vault", {})
    return {
        "collection": "codebase_vault",
        "total_documents": cb_stats.get("count", 0),
        "status": cb_stats.get("error", "online"),
    }
