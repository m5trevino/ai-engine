"""
PEACOCK ENGINE — Stress Test API (TB-022)
Trigger controlled stress runs and retrieve reports.
"""

import asyncio
import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

from app.core.stress_runner import StressRunner, StressConfig, StressReport

router = APIRouter()

# Active runners keyed by run_id
_active_runners: dict = {}


# ═══════════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class StressStartRequest(BaseModel):
    file_paths: List[str] = Field(..., min_length=1)
    model_id: str = "llama-3.3-70b-versatile"
    concurrency: int = Field(3, ge=1, le=20)
    system_prompt: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 1024


class StressStartResponse(BaseModel):
    run_id: str
    status: str
    total_plans: int


class StressLiveResponse(BaseModel):
    run_id: str
    state: str
    total_plans: int
    completed_plans: int
    failed_plans: int
    total_chunks: int
    completed_chunks: int
    failed_chunks: int
    total_tokens: int
    total_cost: float
    elapsed_ms: int
    current_file: str


class StressListItem(BaseModel):
    run_id: str
    status: str
    total_plans: int
    completed_plans: int
    failed_plans: int
    total_tokens: int
    duration_ms: int
    created_at: float


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/start", response_model=StressStartResponse)
async def start_stress(request: StressStartRequest, background_tasks: BackgroundTasks):
    """Start a new stress test run in the background."""
    runner = StressRunner()
    config = StressConfig(
        file_paths=request.file_paths,
        model_id=request.model_id,
        concurrency=request.concurrency,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    # Kick off the run in the background
    task = asyncio.create_task(_run_and_cleanup(runner, config))

    # Wait a moment for the runner to initialize and get a run_id
    for _ in range(50):
        if runner.live_status:
            break
        await asyncio.sleep(0.05)

    if not runner.live_status:
        raise HTTPException(status_code=500, detail="Stress runner failed to initialize")

    run_id = runner.live_status.run_id
    _active_runners[run_id] = runner

    return {
        "run_id": run_id,
        "status": "started",
        "total_plans": len(request.file_paths),
    }


async def _run_and_cleanup(runner: StressRunner, config: StressConfig):
    """Wrapper that runs the stress test and cleans up the active runner ref."""
    try:
        await runner.run(config)
    finally:
        if runner.live_status and runner.live_status.run_id in _active_runners:
            del _active_runners[runner.live_status.run_id]


@router.get("/status/{run_id}", response_model=StressLiveResponse)
async def get_stress_status(run_id: str):
    """Get live status of a running or recently completed stress test."""
    runner = _active_runners.get(run_id)
    if runner and runner.live_status:
        live = runner.live_status
        return {
            "run_id": live.run_id,
            "state": live.state,
            "total_plans": live.total_plans,
            "completed_plans": live.completed_plans,
            "failed_plans": live.failed_plans,
            "total_chunks": live.total_chunks,
            "completed_chunks": live.completed_chunks,
            "failed_chunks": live.failed_chunks,
            "total_tokens": live.total_tokens,
            "total_cost": live.total_cost,
            "elapsed_ms": live.elapsed_ms,
            "current_file": live.current_file,
        }

    # Fall back to loading the report if it's finished
    report = StressRunner.load_report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    return {
        "run_id": report.run_id,
        "state": report.status,
        "total_plans": report.total_plans,
        "completed_plans": report.completed_plans,
        "failed_plans": report.failed_plans,
        "total_chunks": report.total_chunks,
        "completed_chunks": report.completed_chunks,
        "failed_chunks": report.failed_chunks,
        "total_tokens": report.total_tokens,
        "total_cost": report.total_cost,
        "elapsed_ms": report.duration_ms,
        "current_file": "",
    }


@router.post("/abort/{run_id}")
async def abort_stress(run_id: str):
    """Signal a running stress test to abort."""
    runner = _active_runners.get(run_id)
    if runner is None:
        raise HTTPException(status_code=404, detail=f"No active run: {run_id}")
    runner.abort()
    return {"status": "abort_signaled", "run_id": run_id}


@router.get("/report/{run_id}")
async def get_stress_report(run_id: str):
    """Retrieve the full post-run report for a stress test."""
    report = StressRunner.load_report(run_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report not found: {run_id}")
    return report.to_dict()


class StressCompareRequest(BaseModel):
    run_ids: List[str] = Field(..., min_length=2, max_length=5)


class StressCompareItem(BaseModel):
    run_id: str
    status: str
    total_plans: int
    completed_plans: int
    failed_plans: int
    total_chunks: int
    completed_chunks: int
    failed_chunks: int
    skipped_chunks: int
    total_tokens: int
    total_cost: float
    duration_ms: int
    proxy_pct: float
    created_at: float


class StressCompareResponse(BaseModel):
    runs: List[StressCompareItem]


@router.get("/list", response_model=List[StressListItem])
async def list_stress_runs(
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None,
    start_date: Optional[float] = Query(None, description="Unix timestamp — inclusive start"),
    end_date: Optional[float] = Query(None, description="Unix timestamp — inclusive end"),
):
    """List past stress test runs with optional filtering and pagination."""
    return StressRunner.list_reports(limit=limit, offset=offset, status=status, start_date=start_date, end_date=end_date)


@router.get("/count")
async def count_stress_runs(
    status: Optional[str] = None,
    start_date: Optional[float] = Query(None, description="Unix timestamp — inclusive start"),
    end_date: Optional[float] = Query(None, description="Unix timestamp — inclusive end"),
):
    """Return total count of stress reports matching filters."""
    return {"total": StressRunner.count_reports(status=status, start_date=start_date, end_date=end_date)}


@router.post("/compare", response_model=StressCompareResponse)
async def compare_stress_runs(request: StressCompareRequest):
    """Compare 2–5 stress test runs side-by-side."""
    runs: List[StressCompareItem] = []
    for run_id in request.run_ids:
        report = StressRunner.load_report(run_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"Report not found: {run_id}")
        pe = report.proxy_effectiveness
        total_routed = pe.get("proxy_chunks", 0) + pe.get("direct_chunks", 0)
        proxy_pct = round((pe.get("proxy_chunks", 0) / total_routed) * 100, 1) if total_routed > 0 else 0.0
        runs.append(StressCompareItem(
            run_id=report.run_id,
            status=report.status,
            total_plans=report.total_plans,
            completed_plans=report.completed_plans,
            failed_plans=report.failed_plans,
            total_chunks=report.total_chunks,
            completed_chunks=report.completed_chunks,
            failed_chunks=report.failed_chunks,
            skipped_chunks=report.skipped_chunks,
            total_tokens=report.total_tokens,
            total_cost=report.total_cost,
            duration_ms=report.duration_ms,
            proxy_pct=proxy_pct,
            created_at=report.created_at,
        ))
    return {"runs": runs}
