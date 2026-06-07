"""
PEACOCK ENGINE — Execution History / Audit Layer (TB-020 / TB-025)
Persistent, queryable storage for every plan execution.

Scope:
  • Store full execution results (plan_id, timestamp, status, per-chunk results,
    total tokens, cost, proxy/direct split, errors)
  • Simple query interface (by date range, by plan, by status, by model_id)
  • Aggregate stats (total tokens, proxy usage %, failure rate)
  • SQLite-indexed listing — no JSON fallback

Storage:
  • Each run is saved as a JSON file under `history/{run_id}.json`
  • run_id = {plan_id}_{timestamp}_{nanoid} for uniqueness

References:
  • app.core.plan_executor (TB-016) — PlanExecutionResult, ChunkExecutionResult
  • app.core.plan_manager (TB-014) — plan metadata
  • app.core.index_store (TB-025) — fast listing via SQLite
"""

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Literal, Optional, Any

from app.core.index_store import index_store


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

HISTORY_DIR = Path(__file__).resolve().parent.parent.parent / "history"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ChunkRunRecord:
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

    @classmethod
    def from_chunk_result(cls, chunk) -> "ChunkRunRecord":
        usage = getattr(chunk, "usage", None) or {}
        return cls(
            chunk_id=getattr(chunk, "chunk_id", 0),
            status=getattr(chunk, "status", ""),
            route=getattr(chunk, "route", None),
            key_used=getattr(chunk, "key_used", None),
            prompt_tokens=usage.get("prompt_tokens", 0) if isinstance(usage, dict) else 0,
            completion_tokens=usage.get("completion_tokens", 0) if isinstance(usage, dict) else 0,
            total_tokens=usage.get("total_tokens", 0) if isinstance(usage, dict) else 0,
            cost=getattr(chunk, "cost", 0.0),
            duration_ms=getattr(chunk, "duration_ms", 0),
            error=getattr(chunk, "error", None),
        )


@dataclass
class RunRecord:
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
    chunks: List[ChunkRunRecord]
    executed_at: float
    error_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "plan_id": self.plan_id,
            "file_path": self.file_path,
            "model_id": self.model_id,
            "status": self.status,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "duration_ms": self.duration_ms,
            "proxy_chunks": self.proxy_chunks,
            "direct_chunks": self.direct_chunks,
            "failed_chunks": self.failed_chunks,
            "skipped_chunks": self.skipped_chunks,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "status": c.status,
                    "route": c.route,
                    "key_used": c.key_used,
                    "prompt_tokens": c.prompt_tokens,
                    "completion_tokens": c.completion_tokens,
                    "total_tokens": c.total_tokens,
                    "cost": c.cost,
                    "duration_ms": c.duration_ms,
                    "error": c.error,
                }
                for c in self.chunks
            ],
            "executed_at": self.executed_at,
            "error_summary": self.error_summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunRecord":
        return cls(
            run_id=data["run_id"],
            plan_id=data["plan_id"],
            file_path=data.get("file_path", ""),
            model_id=data.get("model_id", ""),
            status=data["status"],
            total_tokens=data.get("total_tokens", 0),
            total_cost=data.get("total_cost", 0.0),
            duration_ms=data.get("duration_ms", 0),
            proxy_chunks=data.get("proxy_chunks", 0),
            direct_chunks=data.get("direct_chunks", 0),
            failed_chunks=data.get("failed_chunks", 0),
            skipped_chunks=data.get("skipped_chunks", 0),
            chunks=[ChunkRunRecord(**c) for c in data.get("chunks", [])],
            executed_at=data["executed_at"],
            error_summary=data.get("error_summary"),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# STORE
# ═══════════════════════════════════════════════════════════════════════════════

class HistoryStore:
    """
    File-backed append-only store for execution runs.

    Usage:
        run_id = HistoryStore.record_execution("plan_abc", "/path/file.py", result)
        runs = HistoryStore.list_runs(limit=20, offset=0)
        detail = HistoryStore.get_run(run_id)
        stats = HistoryStore.get_stats(days=7)
    """

    @staticmethod
    def _ensure_dir() -> None:
        HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _run_path(run_id: str) -> Path:
        return HISTORY_DIR / f"{run_id}.json"

    @classmethod
    def record_execution(
        cls,
        plan_id: str,
        file_path: str,
        model_id: str,
        result: Any,
    ) -> str:
        """
        Persist a full execution result. Returns the generated run_id.
        """
        cls._ensure_dir()
        run_id = f"{plan_id}_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        proxy_chunks = sum(
            1 for c in result.chunks if c.status == "completed" and c.route == "proxy"
        )
        direct_chunks = sum(
            1 for c in result.chunks if c.status == "completed" and c.route == "direct"
        )
        failed_chunks = sum(1 for c in result.chunks if c.status == "failed")
        skipped_chunks = sum(1 for c in result.chunks if c.status == "skipped")

        error_summary = None
        errors = [c.error for c in result.chunks if c.error]
        if errors:
            error_summary = errors[0] if len(errors) == 1 else f"{len(errors)} chunks failed"

        record = RunRecord(
            run_id=run_id,
            plan_id=plan_id,
            file_path=file_path,
            model_id=model_id,
            status=result.status,
            total_tokens=result.total_tokens,
            total_cost=result.total_cost,
            duration_ms=result.duration_ms,
            proxy_chunks=proxy_chunks,
            direct_chunks=direct_chunks,
            failed_chunks=failed_chunks,
            skipped_chunks=skipped_chunks,
            chunks=[ChunkRunRecord.from_chunk_result(c) for c in result.chunks],
            executed_at=time.time(),
            error_summary=error_summary,
        )

        path = cls._run_path(run_id)
        path.write_text(json.dumps(record.to_dict(), indent=2), encoding="utf-8")
        index_store.index_history_run(record.to_dict())
        return run_id

    @classmethod
    def list_runs(
        cls,
        limit: int = 50,
        offset: int = 0,
        plan_id: Optional[str] = None,
        status: Optional[str] = None,
        model_id: Optional[str] = None,
        start_date: Optional[float] = None,
        end_date: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return a list of run summaries, newest first.
        Uses SQLite index exclusively (TB-025). No JSON fallback.

        Args:
            limit: Max results per page
            offset: Pagination offset
            plan_id: Filter to a specific plan
            status: Filter by run status
            model_id: Filter by model ID
            start_date: Unix timestamp — include runs after this time
            end_date: Unix timestamp — include runs before this time
        """
        return index_store.list_history_runs(
            limit=limit,
            offset=offset,
            plan_id=plan_id,
            status=status,
            model_id=model_id,
            start_date=start_date,
            end_date=end_date,
        )

    @classmethod
    def count_runs(
        cls,
        plan_id: Optional[str] = None,
        status: Optional[str] = None,
        model_id: Optional[str] = None,
        start_date: Optional[float] = None,
        end_date: Optional[float] = None,
    ) -> int:
        """Return total count of runs matching filters."""
        return index_store.count_history_runs(
            plan_id=plan_id,
            status=status,
            model_id=model_id,
            start_date=start_date,
            end_date=end_date,
        )

    @classmethod
    def get_run(cls, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single run by ID."""
        path = cls._run_path(run_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    @classmethod
    def get_stats(cls, days: int = 7) -> Dict[str, Any]:
        """
        Aggregate statistics over the last N days.
        Uses SQLite index exclusively (TB-030). No JSON scan.
        """
        from app.core.index_store import index_store
        cutoff = time.time() - (days * 86400)

        row = index_store._conn.execute(
            """SELECT
                COUNT(*) AS total_runs,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_runs,
                SUM(CASE WHEN status IN ('failed','partial') THEN 1 ELSE 0 END) AS failed_runs,
                SUM(total_tokens) AS total_tokens,
                SUM(total_cost) AS total_cost,
                SUM(proxy_chunks) AS proxy_chunks,
                SUM(direct_chunks) AS direct_chunks,
                SUM(failed_chunks) AS failed_chunks
            FROM history_runs
            WHERE executed_at >= ?""",
            (cutoff,),
        ).fetchone()

        total_runs = row["total_runs"] or 0
        completed_runs = row["completed_runs"] or 0
        failed_runs = row["failed_runs"] or 0
        total_tokens = row["total_tokens"] or 0
        total_cost = row["total_cost"] or 0.0
        proxy_chunks = row["proxy_chunks"] or 0
        direct_chunks = row["direct_chunks"] or 0
        failed_chunks = row["failed_chunks"] or 0

        total_completed_chunks = proxy_chunks + direct_chunks
        proxy_pct = (
            round((proxy_chunks / total_completed_chunks) * 100, 1)
            if total_completed_chunks > 0
            else 0.0
        )
        failure_rate = round((failed_runs / total_runs) * 100, 1) if total_runs > 0 else 0.0

        return {
            "period_days": days,
            "total_runs": total_runs,
            "completed_runs": completed_runs,
            "failed_runs": failed_runs,
            "failure_rate": failure_rate,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 6),
            "proxy_chunks": proxy_chunks,
            "direct_chunks": direct_chunks,
            "proxy_pct": proxy_pct,
            "failed_chunks": failed_chunks,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE
# ═══════════════════════════════════════════════════════════════════════════════

def record_execution(plan_id: str, file_path: str, model_id: str, result: Any) -> str:
    return HistoryStore.record_execution(plan_id, file_path, model_id, result)
