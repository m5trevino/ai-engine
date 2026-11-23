"""
PEACOCK ENGINE — Execution History API (TB-020)
REST endpoints for querying execution audit history.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.core.history import HistoryStore

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ChunkRunItem(BaseModel):
    chunk_id: int
    status: str
    route: Optional[str]
    key_used: Optional[str]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost: float
    duration_ms: int
    error: Optional[str]


class RunListItem(BaseModel):
    run_id: str
    plan_id: str
    file_path: str
    model_id: str
    status: str
    total_tokens: int
    total_cost: float
    duration_ms: int
    proxy_chunks: int
    direct_chunks: int
    failed_chunks: int
    skipped_chunks: int
    executed_at: float
    error_summary: Optional[str]


class RunDetail(BaseModel):
    run_id: str
    plan_id: str
    file_path: str
    model_id: str
    status: str
    total_tokens: int
    total_cost: float
    duration_ms: int
    proxy_chunks: int
    direct_chunks: int
    failed_chunks: int
    skipped_chunks: int
    chunks: List[ChunkRunItem]
    executed_at: float
    error_summary: Optional[str]


class HistoryStats(BaseModel):
    period_days: int
    total_runs: int
    completed_runs: int
    failed_runs: int
    failure_rate: float
    total_tokens: int
    total_cost: float
    proxy_chunks: int
    direct_chunks: int
    proxy_pct: float
    failed_chunks: int


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("", response_model=List[RunListItem])
async def list_runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    plan_id: Optional[str] = None,
    status: Optional[str] = None,
    model_id: Optional[str] = None,
    start_date: Optional[float] = Query(None, description="Unix timestamp — inclusive start"),
    end_date: Optional[float] = Query(None, description="Unix timestamp — inclusive end"),
):
    """List execution runs with optional filtering and pagination."""
    return HistoryStore.list_runs(
        limit=limit,
        offset=offset,
        plan_id=plan_id,
        status=status,
        model_id=model_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/count")
async def count_runs(
    plan_id: Optional[str] = None,
    status: Optional[str] = None,
    model_id: Optional[str] = None,
    start_date: Optional[float] = Query(None, description="Unix timestamp — inclusive start"),
    end_date: Optional[float] = Query(None, description="Unix timestamp — inclusive end"),
):
    """Return total count of runs matching filters."""
    return {"total": HistoryStore.count_runs(
        plan_id=plan_id,
        status=status,
        model_id=model_id,
        start_date=start_date,
        end_date=end_date,
    )}


@router.get("/stats", response_model=HistoryStats)
async def get_stats(days: int = Query(7, ge=1, le=90)):
    """Aggregate statistics over the last N days."""
    return HistoryStore.get_stats(days=days)


class HistoryCompareRequest(BaseModel):
    run_ids: List[str] = Field(..., min_length=2, max_length=5)


class HistoryCompareItem(BaseModel):
    run_id: str
    plan_id: str
    file_path: str
    model_id: str
    status: str
    total_tokens: int
    total_cost: float
    duration_ms: int
    proxy_chunks: int
    direct_chunks: int
    failed_chunks: int
    skipped_chunks: int
    proxy_pct: float
    executed_at: float
    error_summary: Optional[str]


class HistoryCompareResponse(BaseModel):
    runs: List[HistoryCompareItem]


@router.get("/{run_id}", response_model=RunDetail)
async def get_run(run_id: str):
    """Retrieve full detail for a single execution run."""
    run = HistoryStore.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run


@router.post("/compare", response_model=HistoryCompareResponse)
async def compare_history_runs(request: HistoryCompareRequest):
    """Compare 2–5 history runs side-by-side."""
    runs: List[HistoryCompareItem] = []
    for run_id in request.run_ids:
        run = HistoryStore.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
        proxy = run.get("proxy_chunks", 0)
        direct = run.get("direct_chunks", 0)
        total = proxy + direct
        proxy_pct = round((proxy / total) * 100, 1) if total > 0 else 0.0
        runs.append(HistoryCompareItem(
            run_id=run.get("run_id", ""),
            plan_id=run.get("plan_id", ""),
            file_path=run.get("file_path", ""),
            model_id=run.get("model_id", ""),
            status=run.get("status", ""),
            total_tokens=run.get("total_tokens", 0),
            total_cost=run.get("total_cost", 0.0),
            duration_ms=run.get("duration_ms", 0),
            proxy_chunks=proxy,
            direct_chunks=direct,
            failed_chunks=run.get("failed_chunks", 0),
            skipped_chunks=run.get("skipped_chunks", 0),
            proxy_pct=proxy_pct,
            executed_at=run.get("executed_at", 0.0),
            error_summary=run.get("error_summary"),
        ))
    return {"runs": runs}
