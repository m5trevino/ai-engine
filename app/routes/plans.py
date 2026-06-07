"""
PEACOCK ENGINE — Plan Review & Manual Override API (TB-015 / TB-016)
Backend endpoints for viewing, overriding, and executing execution plans.

References:
  • app.core.plan_generator     (TB-011)
  • app.core.plan_manager       (TB-014)
  • app.core.proxy_rules        (TB-012)
  • app.core.plan_executor      (TB-016)
"""

from typing import List, Literal, Optional
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.plan_generator import generate_plan
from app.core.plan_manager import PlanManager
from app.core.plan_executor import PlanExecutor, PlanExecutionResult
from app.core.plan_queue import PlanQueueSingleton, PlanRunnerSingleton


router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class PlanCreateRequest(BaseModel):
    file_path: str
    model_id: Optional[str] = None
    system_prompt: Optional[str] = None


class RouteOverrideRequest(BaseModel):
    route: Literal["direct", "proxy"]


class StatusUpdateRequest(BaseModel):
    status: str


class ChunkStatusUpdateRequest(BaseModel):
    status: str
    error: Optional[str] = None


class PlanExecuteRequest(BaseModel):
    system_prompt: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 1024
    top_p: Optional[float] = None
    abort_on_fail: bool = False


class PlanListItem(BaseModel):
    plan_id: str
    file_path: str
    model_id: str
    total_chunks: int
    completed_chunks: int
    overridden_chunks: int
    status: str
    estimated_total_seconds: float
    makespan_seconds: float
    created_at: Optional[float]
    completed_at: Optional[float]


class PlanDetailResponse(BaseModel):
    plan_id: str
    file_path: str
    total_chunks: int
    total_tokens: int
    estimated_total_seconds: float
    makespan_seconds: float
    status: str
    model_id: str
    config: dict
    rules: List[dict]
    created_at: Optional[float]
    completed_at: Optional[float]
    chunks: List[dict]


class ChunkSummaryResponse(BaseModel):
    plan_id: str
    plan_status: str
    total_chunks: int
    chunks: List[dict]


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

class RecentExecutionItem(BaseModel):
    plan_id: str
    file_path: str
    model_id: str
    total_chunks: int
    executed_at: float
    status: str
    total_tokens: int
    total_cost: float
    duration_ms: int
    proxy_chunks: int
    direct_chunks: int


@router.get("/recent", response_model=List[RecentExecutionItem])
async def get_recent_executions(limit: int = 20):
    """Get recent execution history across all plans."""
    return PlanManager.get_recent_executions(limit=limit)


@router.get("", response_model=List[PlanListItem])
async def list_plans(
    status: Optional[str] = None,
    model_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List stored plans with optional status and model_id filter."""
    return PlanManager.list_plans(status=status, model_id=model_id, limit=limit, offset=offset)


@router.get("/count")
async def count_plans(
    status: Optional[str] = None,
    model_id: Optional[str] = None,
):
    """Return total count of plans matching filters."""
    return {"total": PlanManager.count_plans(status=status, model_id=model_id)}


@router.post("", response_model=PlanDetailResponse)
async def create_plan(request: PlanCreateRequest):
    """Generate a new plan from a file path and persist it."""
    if not Path(request.file_path).exists():
        raise HTTPException(status_code=404, detail=f"File not found: {request.file_path}")

    plan = await generate_plan(
        file_path=request.file_path,
        model_id=request.model_id,
        system_prompt=request.system_prompt,
    )
    plan_id = PlanManager.save(plan)
    return _plan_to_response(plan_id, plan)


@router.get("/{plan_id}", response_model=PlanDetailResponse)
async def get_plan(plan_id: str):
    """Retrieve a full plan by ID."""
    try:
        plan = PlanManager.load(plan_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    return _plan_to_response(plan_id, plan)


@router.get("/{plan_id}/chunks", response_model=ChunkSummaryResponse)
async def get_chunk_summary(plan_id: str):
    """Get a concise per-chunk summary including effective routes and overrides."""
    try:
        summary = PlanManager.get_chunk_summary(plan_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    return summary


@router.patch("/{plan_id}/status", response_model=PlanDetailResponse)
async def update_plan_status(plan_id: str, request: StatusUpdateRequest):
    """Update the top-level status of a plan."""
    try:
        plan = PlanManager.update_plan_status(plan_id, request.status)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _plan_to_response(plan_id, plan)


@router.patch("/{plan_id}/chunks/{chunk_id}/status", response_model=PlanDetailResponse)
async def update_chunk_status(plan_id: str, chunk_id: int, request: ChunkStatusUpdateRequest):
    """Update the status of a single chunk."""
    try:
        plan = PlanManager.update_chunk_status(plan_id, chunk_id, request.status, error=request.error)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _plan_to_response(plan_id, plan)


@router.patch("/{plan_id}/chunks/{chunk_id}/route", response_model=PlanDetailResponse)
async def set_chunk_route_override(plan_id: str, chunk_id: int, request: RouteOverrideRequest):
    """Apply a manual routing override to a chunk."""
    try:
        plan = PlanManager.set_chunk_override(plan_id, chunk_id, request.route)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _plan_to_response(plan_id, plan)


@router.delete("/{plan_id}/chunks/{chunk_id}/route", response_model=PlanDetailResponse)
async def clear_chunk_route_override(plan_id: str, chunk_id: int):
    """Remove a manual routing override from a chunk."""
    try:
        plan = PlanManager.clear_chunk_override(plan_id, chunk_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _plan_to_response(plan_id, plan)


@router.delete("/{plan_id}")
async def delete_plan(plan_id: str):
    """Delete a plan from storage."""
    if not PlanManager.delete(plan_id):
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")
    return {"status": "deleted", "plan_id": plan_id}


@router.post("/{plan_id}/execute")
async def execute_plan_endpoint(plan_id: str, request: PlanExecuteRequest):
    """Execute a plan, honoring per-chunk routing overrides."""
    try:
        PlanManager.load(plan_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")

    executor = PlanExecutor(abort_on_fail=request.abort_on_fail)
    result = await executor.execute_plan(
        plan_id,
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        top_p=request.top_p,
    )

    return {
        "plan_id": result.plan_id,
        "status": result.status,
        "total_tokens": result.total_tokens,
        "total_cost": result.total_cost,
        "duration_ms": result.duration_ms,
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "status": c.status,
                "route": c.route,
                "key_used": c.key_used,
                "usage": c.usage,
                "cost": c.cost,
                "duration_ms": c.duration_ms,
                "error": c.error,
            }
            for c in result.chunks
        ],
    }


# ═══════════════════════════════════════════════════════════════════════════════
# QUEUE
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/{plan_id}/queue")
async def queue_plan(plan_id: str):
    """Add a plan to the execution queue."""
    try:
        PlanManager.load(plan_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Plan not found: {plan_id}")

    position = await PlanQueueSingleton.enqueue(plan_id)
    PlanManager.update_plan_status(plan_id, "queued")
    return {"status": "queued", "plan_id": plan_id, "position": position}


@router.delete("/{plan_id}/queue")
async def unqueue_plan(plan_id: str):
    """Remove a plan from the execution queue."""
    removed = await PlanQueueSingleton.remove(plan_id)
    if removed:
        try:
            PlanManager.update_plan_status(plan_id, "pending")
        except Exception:
            pass
    return {"status": "removed" if removed else "not_in_queue", "plan_id": plan_id}


@router.get("/queue/snapshot")
async def queue_snapshot():
    """Get current queue state and runner status."""
    snap = await PlanRunnerSingleton.snapshot()
    return {
        "state": snap.state,
        "length": snap.length,
        "current_plan_id": snap.current_plan_id,
        "completed_count": snap.completed_count,
        "failed_count": snap.failed_count,
        "items": [{"plan_id": i.plan_id, "position": i.position} for i in snap.items],
    }


@router.post("/queue/start")
async def start_queue(request: PlanExecuteRequest):
    """Start processing the queue sequentially."""
    await PlanRunnerSingleton.start(
        system_prompt=request.system_prompt,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        top_p=request.top_p,
    )
    return {"status": "started"}


@router.post("/queue/stop")
async def stop_queue():
    """Signal the runner to stop after the current plan."""
    await PlanRunnerSingleton.stop()
    return {"status": "stopped"}


@router.delete("/queue/all")
async def clear_queue():
    """Clear all plans from the queue."""
    count = await PlanQueueSingleton.clear()
    return {"status": "cleared", "removed": count}


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _plan_to_response(plan_id: str, plan) -> dict:
    """Convert an ExecutionPlan into the API response shape."""
    return {
        "plan_id": plan_id,
        "file_path": plan.file_path,
        "total_chunks": plan.total_chunks,
        "total_tokens": plan.total_tokens,
        "estimated_total_seconds": plan.estimated_total_seconds,
        "makespan_seconds": plan.makespan_seconds,
        "status": plan.status,
        "model_id": plan.model_id,
        "config": plan.config,
        "rules": plan.rules,
        "created_at": plan.created_at,
        "completed_at": plan.completed_at,
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "token_count": c.token_count,
                "model_id": c.model_id,
                "key_label": c.key_label,
                "route": c.route,
                "estimated_seconds": c.estimated_seconds,
                "wait_seconds": c.wait_seconds,
                "status": c.status,
                "manual_override": c.manual_override,
                "rationale": c.rationale,
            }
            for c in plan.chunks
        ],
    }
