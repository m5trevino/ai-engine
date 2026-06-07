"""
PEACOCK ENGINE — Stress Test Harness (TB-022 / TB-025)
Controlled concurrency execution of multiple plans with live telemetry
and post-run bottleneck analysis.

Scope:
  • Create plans for a batch of files
  • Execute with configurable concurrency (asyncio semaphore)
  • Capture per-key burn, wait distribution, proxy split, retry patterns
  • Generate post-run report with bottleneck detection + tuning suggestions
  • SQLite-indexed listing — no JSON fallback

Storage:
  • Reports saved to stress/{run_id}.json

References:
  • app.core.plan_generator (TB-011)
  • app.core.plan_executor (TB-016)
  • app.core.plan_manager (TB-014)
  • app.core.config_store (TB-021)
  • app.monitoring.metrics (TB-018)
  • app.core.index_store (TB-025)
"""

import json
import time
import uuid
import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from app.core.plan_generator import generate_plan
from app.core.plan_manager import PlanManager
from app.core.plan_executor import PlanExecutor, PlanExecutionResult
from app.core.config_store import config_store
from app.monitoring.metrics import global_metrics
from app.core.index_store import index_store


STRESS_DIR = Path(__file__).resolve().parent.parent.parent / "stress"


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StressConfig:
    file_paths: List[str]
    model_id: str = "llama-3.3-70b-versatile"
    concurrency: int = 3
    system_prompt: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 1024
    abort_on_fail: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# LIVE STATUS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StressLiveStatus:
    run_id: str
    state: str  # "running" | "completed" | "aborted"
    total_plans: int
    completed_plans: int = 0
    failed_plans: int = 0
    total_chunks: int = 0
    completed_chunks: int = 0
    failed_chunks: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    elapsed_ms: int = 0
    current_file: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# REPORT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StressReport:
    run_id: str
    config: Dict[str, Any]
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
    per_key_stats: Dict[str, Any]
    wait_distribution: Dict[str, Any]
    proxy_effectiveness: Dict[str, Any]
    bottlenecks: List[str]
    suggestions: List[str]
    created_at: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "config": self.config,
            "status": self.status,
            "total_plans": self.total_plans,
            "completed_plans": self.completed_plans,
            "failed_plans": self.failed_plans,
            "total_chunks": self.total_chunks,
            "completed_chunks": self.completed_chunks,
            "failed_chunks": self.failed_chunks,
            "skipped_chunks": self.skipped_chunks,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "duration_ms": self.duration_ms,
            "per_key_stats": self.per_key_stats,
            "wait_distribution": self.wait_distribution,
            "proxy_effectiveness": self.proxy_effectiveness,
            "bottlenecks": self.bottlenecks,
            "suggestions": self.suggestions,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StressReport":
        return cls(
            run_id=data["run_id"],
            config=data.get("config", {}),
            status=data.get("status", "unknown"),
            total_plans=data.get("total_plans", 0),
            completed_plans=data.get("completed_plans", 0),
            failed_plans=data.get("failed_plans", 0),
            total_chunks=data.get("total_chunks", 0),
            completed_chunks=data.get("completed_chunks", 0),
            failed_chunks=data.get("failed_chunks", 0),
            skipped_chunks=data.get("skipped_chunks", 0),
            total_tokens=data.get("total_tokens", 0),
            total_cost=data.get("total_cost", 0.0),
            duration_ms=data.get("duration_ms", 0),
            per_key_stats=data.get("per_key_stats", {}),
            wait_distribution=data.get("wait_distribution", {}),
            proxy_effectiveness=data.get("proxy_effectiveness", {}),
            bottlenecks=data.get("bottlenecks", []),
            suggestions=data.get("suggestions", []),
            created_at=data.get("created_at", 0.0),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# RUNNER
# ═══════════════════════════════════════════════════════════════════════════════

class StressRunner:
    """
    Execute a batch of plans with controlled concurrency and generate
    a detailed post-run report.

    Usage:
        runner = StressRunner()
        report = await runner.run(StressConfig(file_paths=[...], concurrency=4))
    """

    def __init__(self):
        self._abort = False
        self._live: Optional[StressLiveStatus] = None
        self._lock = asyncio.Lock()

    @property
    def live_status(self) -> Optional[StressLiveStatus]:
        return self._live

    def abort(self) -> None:
        self._abort = True

    # ─────────────────────────── CORE RUN ───────────────────────────

    async def run(self, config: StressConfig) -> StressReport:
        run_id = f"stress_{int(time.time())}_{uuid.uuid4().hex[:6]}"
        trace_id = f"stress_{uuid.uuid4().hex[:8]}"
        logger = logging.getLogger("peacock.stress")
        logger.info(f"[trace={trace_id}] Starting stress run: {run_id} with {len(config.file_paths)} files")
        start_time = time.time()

        # Create plans
        plans: List[Any] = []
        plan_ids: List[str] = []
        for fp in config.file_paths:
            if self._abort:
                break
            try:
                plan = await generate_plan(
                    file_path=fp,
                    model_id=config.model_id,
                    system_prompt=config.system_prompt,
                )
                pid = PlanManager.save(plan)
                plans.append(plan)
                plan_ids.append(pid)
            except Exception as e:
                # Skip files that fail plan generation
                continue

        total_chunks = sum(p.total_chunks for p in plans)

        self._live = StressLiveStatus(
            run_id=run_id,
            state="running",
            total_plans=len(plan_ids),
            total_chunks=total_chunks,
        )

        # Execute with controlled concurrency
        sem = asyncio.Semaphore(config.concurrency)
        results: List[PlanExecutionResult] = []

        async def execute_one(plan_id: str, file_path: str):
            async with sem:
                if self._abort:
                    return None
                async with self._lock:
                    if self._live:
                        self._live.current_file = file_path
                executor = PlanExecutor(abort_on_fail=config.abort_on_fail)
                try:
                    return await executor.execute_plan(
                        plan_id,
                        system_prompt=config.system_prompt,
                        temperature=config.temperature,
                        max_tokens=config.max_tokens,
                    )
                except Exception:
                    return None

        tasks = [
            asyncio.create_task(execute_one(pid, fp))
            for pid, fp in zip(plan_ids, config.file_paths[: len(plan_ids)])
        ]

        for task in asyncio.as_completed(tasks):
            result = await task
            if result is not None:
                results.append(result)
            async with self._lock:
                if self._live and result:
                    self._live.completed_plans += 1 if result.status == "completed" else 0
                    self._live.failed_plans += 1 if result.status != "completed" else 0
                    self._live.completed_chunks += sum(1 for c in result.chunks if c.status == "completed")
                    self._live.failed_chunks += sum(1 for c in result.chunks if c.status == "failed")
                    self._live.total_tokens += result.total_tokens
                    self._live.total_cost += result.total_cost
                    self._live.elapsed_ms = int((time.time() - start_time) * 1000)

        duration_ms = int((time.time() - start_time) * 1000)

        # Build report
        report = self._analyze(run_id, config, results, duration_ms)
        logger.info(
            f"[trace={trace_id}] Stress run {run_id} complete: "
            f"status={report.status}, plans={report.total_plans}, "
            f"tokens={report.total_tokens}, duration={duration_ms}ms"
        )
        self._save_report(report)

        async with self._lock:
            if self._live:
                self._live.state = "aborted" if self._abort else "completed"

        return report

    # ─────────────────────────── ANALYSIS ───────────────────────────

    @staticmethod
    def _analyze(
        run_id: str,
        config: StressConfig,
        results: List[PlanExecutionResult],
        duration_ms: int,
    ) -> StressReport:
        total_plans = len(results)
        completed_plans = sum(1 for r in results if r.status == "completed")
        failed_plans = total_plans - completed_plans

        all_chunks = []
        for r in results:
            all_chunks.extend(r.chunks)

        total_chunks = len(all_chunks)
        completed_chunks = sum(1 for c in all_chunks if c.status == "completed")
        failed_chunks = sum(1 for c in all_chunks if c.status == "failed")
        skipped_chunks = sum(1 for c in all_chunks if c.status == "skipped")
        total_tokens = sum(c.usage.get("total_tokens", 0) for c in all_chunks if c.status == "completed")
        total_cost = round(sum(c.cost for c in all_chunks if c.status == "completed"), 6)

        # Per-key stats
        key_stats: Dict[str, Dict[str, Any]] = {}
        for c in all_chunks:
            if c.status != "completed" or not c.key_used:
                continue
            ks = key_stats.setdefault(c.key_used, {"tokens": 0, "chunks": 0, "cost": 0.0, "duration_ms": 0})
            ks["tokens"] += c.usage.get("total_tokens", 0)
            ks["chunks"] += 1
            ks["cost"] += c.cost
            ks["duration_ms"] += c.duration_ms

        for ks in key_stats.values():
            ks["avg_duration_ms"] = round(ks["duration_ms"] / max(ks["chunks"], 1), 1)
            ks["cost"] = round(ks["cost"], 6)

        # Wait time distribution
        durations = [c.duration_ms for c in all_chunks if c.status == "completed" and c.duration_ms > 0]
        durations_sorted = sorted(durations)
        wait_distribution = {
            "count": len(durations),
            "min_ms": durations_sorted[0] if durations else 0,
            "max_ms": durations_sorted[-1] if durations else 0,
            "median_ms": durations_sorted[len(durations) // 2] if durations else 0,
            "p95_ms": durations_sorted[int(len(durations) * 0.95)] if durations else 0,
            "p99_ms": durations_sorted[int(len(durations) * 0.99)] if durations else 0,
        }

        # Proxy effectiveness
        proxy_chunks = sum(1 for c in all_chunks if c.status == "completed" and c.route == "proxy")
        direct_chunks = sum(1 for c in all_chunks if c.status == "completed" and c.route == "direct")
        total_routed = proxy_chunks + direct_chunks
        proxy_effectiveness = {
            "proxy_chunks": proxy_chunks,
            "direct_chunks": direct_chunks,
            "proxy_pct": round((proxy_chunks / total_routed) * 100, 1) if total_routed > 0 else 0.0,
            "direct_pct": round((direct_chunks / total_routed) * 100, 1) if total_routed > 0 else 0.0,
        }

        # Bottlenecks
        bottlenecks: List[str] = []
        if failed_plans > 0:
            bottlenecks.append(f"{failed_plans}/{total_plans} plans failed")
        if wait_distribution["p95_ms"] > 30000:
            bottlenecks.append(f"P95 chunk latency is {wait_distribution['p95_ms']}ms — consider raising concurrency")
        if wait_distribution["median_ms"] > 15000:
            bottlenecks.append(f"Median chunk latency is {wait_distribution['median_ms']}ms — possible key throttling")

        # Find hottest key
        if key_stats:
            hottest = max(key_stats.items(), key=lambda x: x[1]["chunks"])
            if hottest[1]["chunks"] > total_routed * 0.5:
                bottlenecks.append(f"Key {hottest[0]} handled {hottest[1]['chunks']} chunks — uneven distribution")

        # Suggestions
        suggestions: List[str] = []
        current_burn = config_store.burn_mode
        if proxy_effectiveness["proxy_pct"] < 10 and proxy_effectiveness["proxy_chunks"] > 0:
            suggestions.append("Proxy usage is low — verify proxy is reachable or lower thresholds")
        elif proxy_effectiveness["proxy_pct"] > 80:
            suggestions.append("Most chunks routed through proxy — consider raising TPM/RPM thresholds")

        if failed_plans > total_plans * 0.2:
            suggestions.append("High failure rate — try CONSERVATIVE burn mode or lower concurrency")
        elif current_burn == "CONSERVATIVE" and wait_distribution["median_ms"] < 5000 and failed_plans == 0:
            suggestions.append("System is stable and fast — try BALANCED or ULTRA burn mode for more throughput")

        if wait_distribution["p95_ms"] > wait_distribution["median_ms"] * 3:
            suggestions.append("High latency variance — some keys may be slower than others; check key health")

        cfg = config_store.proxy_rules
        if proxy_effectiveness["proxy_chunks"] == 0 and cfg.get("tpm_threshold_pct", 85) < 95:
            suggestions.append("No proxy usage detected — proxy thresholds may be too conservative")

        return StressReport(
            run_id=run_id,
            config={
                "file_paths": config.file_paths,
                "model_id": config.model_id,
                "concurrency": config.concurrency,
                "burn_mode": current_burn,
            },
            status="aborted" if failed_plans == total_plans and total_plans > 0 else "completed" if failed_plans == 0 else "partial",
            total_plans=total_plans,
            completed_plans=completed_plans,
            failed_plans=failed_plans,
            total_chunks=total_chunks,
            completed_chunks=completed_chunks,
            failed_chunks=failed_chunks,
            skipped_chunks=skipped_chunks,
            total_tokens=total_tokens,
            total_cost=total_cost,
            duration_ms=duration_ms,
            per_key_stats=key_stats,
            wait_distribution=wait_distribution,
            proxy_effectiveness=proxy_effectiveness,
            bottlenecks=bottlenecks,
            suggestions=suggestions,
            created_at=time.time(),
        )

    # ─────────────────────────── PERSISTENCE ───────────────────────────

    @staticmethod
    def _save_report(report: StressReport) -> None:
        STRESS_DIR.mkdir(parents=True, exist_ok=True)
        path = STRESS_DIR / f"{report.run_id}.json"
        path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
        index_store.index_stress_report(report.to_dict())

    @staticmethod
    def load_report(run_id: str) -> Optional[StressReport]:
        path = STRESS_DIR / f"{run_id}.json"
        if not path.exists():
            return None
        try:
            return StressReport.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def list_reports(
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        start_date: Optional[float] = None,
        end_date: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        List past stress test reports.
        Uses SQLite index exclusively (TB-025). No JSON fallback.
        """
        return index_store.list_stress_reports(
            limit=limit, offset=offset, status=status, start_date=start_date, end_date=end_date
        )

    @staticmethod
    def count_reports(
        status: Optional[str] = None,
        start_date: Optional[float] = None,
        end_date: Optional[float] = None,
    ) -> int:
        """Return total count of stress reports matching filters."""
        return index_store.count_stress_reports(status=status, start_date=start_date, end_date=end_date)
