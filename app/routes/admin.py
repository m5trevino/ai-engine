"""
PEACOCK ENGINE — Admin Cleanup API (TB-024)
Manual cleanup trigger and storage statistics.

Endpoints:
  • POST /v1/admin/cleanup — Run cleanup immediately
  • GET  /v1/admin/storage  — Storage statistics
  • GET  /v1/admin/system   — System health summary
"""

import os
import asyncio
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.cleanup import CleanupManager
from app.core.rate_limit_tracker import GroqRateTracker, KeyModelTelemetry
from app.core.global_pacer import GroqPacer
from app.core.key_manager import GroqPool

LOG_PATH = "/tmp/peacock-engine.log"

router = APIRouter()


class CleanupSummaryResponse(BaseModel):
    status: str
    plans_deleted: int
    stress_deleted: int
    history_deleted: int
    bytes_freed: int


class StorageStatsResponse(BaseModel):
    plans: Dict[str, Any]
    stress: Dict[str, Any]
    history: Dict[str, Any]
    total_bytes: int


class QueueState(BaseModel):
    state: str
    depth: int
    current_plan_id: Optional[str]
    completed_today: int
    failed_today: int


class SystemStatusResponse(BaseModel):
    status: str
    queue: QueueState
    failure_rate_24h: float
    storage: Dict[str, Any]
    storage_status: str
    keys: Dict[str, int]


@router.post("/cleanup", response_model=CleanupSummaryResponse)
async def run_cleanup():
    """
    Trigger an immediate cleanup run using current TTL settings.
    Returns counts of what was deleted and bytes freed.
    """
    mgr = CleanupManager()
    result = mgr.run_now()
    return {
        "status": "cleaned",
        "plans_deleted": result["plans"],
        "stress_deleted": result["stress"],
        "history_deleted": result["history"],
        "bytes_freed": result["bytes_freed"],
    }


@router.get("/storage", response_model=StorageStatsResponse)
async def get_storage_stats():
    """
    Return current storage statistics for plans, stress reports, and history.
    Includes file counts, total bytes, and oldest mtime per category.
    """
    stats = CleanupManager.storage_stats()
    return {
        "plans": stats["plans"],
        "stress": stats["stress"],
        "history": stats["history"],
        "total_bytes": stats["total_bytes"],
    }


@router.get("/system", response_model=SystemStatusResponse)
async def get_system_status():
    """
    Return a high-level system health summary:
    queue state, failure rate, storage counts, key counts.
    Includes storage threshold status (ok / warning / critical).
    """
    from app.core.plan_queue import PlanRunnerSingleton
    from app.core.history import HistoryStore
    from app.core.key_manager import GroqPool, OpencodeGoPool, OpencodeZenPool, OpenrouterPool, OllamaPool, HetznerPool
    from app.core.config_store import config_store

    snap = await PlanRunnerSingleton.snapshot()
    hist = HistoryStore.get_stats(days=1)
    storage = CleanupManager.storage_stats()

    total_mb = round(storage.get("total_bytes", 0) / (1024 * 1024), 1)
    warning_mb = config_store.get("cleanup.storage_warning_mb", 50)
    critical_mb = config_store.get("cleanup.storage_critical_mb", 200)

    if total_mb >= critical_mb:
        storage_status = "critical"
    elif total_mb >= warning_mb:
        storage_status = "warning"
    else:
        storage_status = "ok"

    overall = "healthy"
    if hist["failure_rate"] >= 20 or storage_status == "critical":
        overall = "degraded"
    if storage_status == "critical":
        overall = "critical"

    return {
        "status": overall,
        "queue": {
            "state": snap.state,
            "depth": snap.length,
            "current_plan_id": snap.current_plan_id,
            "completed_today": hist["completed_runs"],
            "failed_today": hist["failed_runs"],
        },
        "failure_rate_24h": hist["failure_rate"],
        "storage": {
            "plans": storage["plans"]["count"],
            "history": storage["history"]["count"],
            "stress": storage["stress"]["count"],
            "total_mb": total_mb,
        },
        "storage_status": storage_status,
        "keys": {
            "groq": len(GroqPool.deck),
            "opencode-go": len(OpencodeGoPool.deck),
            "opencode-zen": len(OpencodeZenPool.deck),
            "openrouter": len(OpenrouterPool.deck),
            "ollama": len(OllamaPool.deck),
            "hetzner": len(HetznerPool.deck),
        },
        "providers": config_store.providers,
    }


@router.get("/rate-limits")
async def get_rate_limits():
    """
    Detailed Groq rate limit status.
    Returns per-key-model telemetry and pacer state.
    """
    key_labels = [a.account for a in GroqPool.deck]
    governor = GroqRateTracker.get_snapshot(key_labels=key_labels)
    pacer = GroqPacer.get_pacer_snapshot()
    return {
        "governor": governor.model_dump(),
        "pacer": pacer,
    }


@router.get("/logs")
async def get_engine_logs(lines: int = Query(50, ge=1, le=500)):
    """Return the last N lines of the engine log."""
    if not os.path.exists(LOG_PATH):
        return {"lines": [], "total_lines": 0}
    with open(LOG_PATH, "r") as f:
        all_lines = f.readlines()
    tail = all_lines[-lines:]
    return {"lines": tail, "total_lines": len(all_lines)}


@router.get("/logs/stream")
async def stream_engine_logs():
    """SSE stream of new engine log lines."""
    async def event_stream():
        last_pos = 0
        if os.path.exists(LOG_PATH):
            last_pos = os.path.getsize(LOG_PATH)
        while True:
            try:
                if os.path.exists(LOG_PATH):
                    cur_size = os.path.getsize(LOG_PATH)
                    if cur_size > last_pos:
                        with open(LOG_PATH, "r") as f:
                            f.seek(last_pos)
                            new_data = f.read()
                            last_pos = f.tell()
                        for line in new_data.split("\n"):
                            if line.strip():
                                yield f"data: {line}\n\n"
            except Exception:
                pass
            await asyncio.sleep(0.5)
    return StreamingResponse(event_stream(), media_type="text/event-stream")
