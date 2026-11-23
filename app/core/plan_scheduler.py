"""
PEACOCK ENGINE — Rate-Limit-Aware Scheduler (TB-013)
Calculates realistic timing between plan steps, factoring in direct vs proxy
routing latency and per-key rate-limit pacing.

Scope:
  • Convert an ExecutionPlan (TB-011) into a ScheduledPlan with per-chunk timing
  • Add proxy latency overhead to proxy-routed chunks
  • Enforce RPM pacing per key-model (no two requests closer than 60/RPM)
  • Respect concurrency limits from GlobalPacer (TB-009)
  • Warn when TPM backpressure would delay the plan

References:
  • app.core.plan_generator (TB-011)
  • app.core.global_pacer (TB-009)
  • app.core.rate_limit_tracker (TB-001)
"""

from dataclasses import dataclass, field
from heapq import heappush, heappop
from typing import Dict, List, Any, TYPE_CHECKING

from app.config import MODEL_REGISTRY
from app.core.rate_limit_tracker import GroqRateTracker
from app.core.global_pacer import GroqPacer

if TYPE_CHECKING:
    from app.core.plan_generator import ExecutionPlan, ChunkPlan


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ScheduledChunk:
    """A ChunkPlan augmented with scheduling metadata."""
    chunk_id: int
    text: str
    token_count: int
    model_id: str
    key_label: str
    route: str
    estimated_seconds: float      # Raw processing time
    wait_seconds: float           # Time spent waiting for pacing / concurrency
    scheduled_start: float        # Relative to plan start (t=0)
    estimated_end: float          # scheduled_start + estimated_seconds
    rationale: str


@dataclass
class ScheduledPlan:
    """A fully-timed execution plan."""
    file_path: str
    total_chunks: int
    total_tokens: int
    estimated_total_seconds: float   # Sum of raw processing times
    makespan_seconds: float          # Wall-clock time from first start to last end
    chunks: List[ScheduledChunk]
    model_id: str
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "total_chunks": self.total_chunks,
            "total_tokens": self.total_tokens,
            "estimated_total_seconds": self.estimated_total_seconds,
            "makespan_seconds": self.makespan_seconds,
            "model_id": self.model_id,
            "warnings": self.warnings,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "key_label": c.key_label,
                    "route": c.route,
                    "token_count": c.token_count,
                    "estimated_seconds": c.estimated_seconds,
                    "wait_seconds": c.wait_seconds,
                    "scheduled_start": round(c.scheduled_start, 2),
                    "estimated_end": round(c.estimated_end, 2),
                }
                for c in self.chunks
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SCHEDULER
# ═══════════════════════════════════════════════════════════════════════════════

class PlanScheduler:
    """
    Rate-limit-aware scheduler for ExecutionPlans.

    Usage:
        plan = await generate_plan("file.py")
        scheduled = PlanScheduler().schedule(plan)
        for chunk in scheduled.chunks:
            print(f"Chunk {chunk.chunk_id}: start={chunk.scheduled_start:.1f}s, end={chunk.estimated_end:.1f}s")
    """

    _THROUGHPUT: Dict[str, float] = {
        "groq": 250.0,
        "google": 80.0,
        "deepseek": 60.0,
        "mistral": 100.0,
    }

    def __init__(
        self,
        proxy_overhead: float = 1.35,
        fixed_overhead: float = 0.5,
        proxy_fixed_overhead: float = 1.0,
        tpm_backpressure_pct: float = 90.0,
    ):
        """
        Args:
            proxy_overhead: Multiplier on processing time for proxy-routed chunks
            fixed_overhead: Base connection overhead (seconds) for direct chunks
            proxy_fixed_overhead: Additional fixed overhead for proxy setup
            tpm_backpressure_pct: If telemetry shows TPM >= this, warn/assume delay
        """
        self.proxy_overhead = proxy_overhead
        self.fixed_overhead = fixed_overhead
        self.proxy_fixed_overhead = proxy_fixed_overhead
        self.tpm_backpressure_pct = tpm_backpressure_pct

    @staticmethod
    def _key(key_label: str, model_id: str) -> str:
        return f"{key_label}:{model_id}"

    def _gateway_for_model(self, model_id: str) -> str:
        for cfg in MODEL_REGISTRY:
            if cfg.id == model_id:
                return cfg.gateway
        return "groq"

    def _processing_time(self, chunk: Any, gateway: str) -> float:
        """Raw wall time to process a chunk (request + response)."""
        throughput = self._THROUGHPUT.get(gateway, 100.0)
        base = chunk.token_count / throughput
        if chunk.route == "proxy":
            base *= self.proxy_overhead
            base += self.proxy_fixed_overhead
        return base + self.fixed_overhead

    @staticmethod
    def _rpm_interval(key_label: str, model_id: str) -> float:
        """Minimum seconds between requests on the same key-model pair."""
        limits = GroqRateTracker.get_model_limits(model_id)
        rpm = limits.get("rpm")
        if not rpm or rpm <= 0:
            return 0.0
        return 60.0 / rpm

    @staticmethod
    def _concurrency_limit(key_label: str, model_id: str) -> int:
        """Concurrency cap from the global pacer for this key-model pair."""
        return GroqPacer._concurrency_for_model(model_id)

    def _tpm_backpressure_delay(
        self,
        key_label: str,
        model_id: str,
        chunk_tokens: int,
        simulated_tpm_used: Dict[str, int],
    ) -> float:
        """
        Estimate TPM backpressure delay.

        We maintain a simple per-key-model token counter. If adding this chunk's
        tokens would push us over the backpressure threshold, we assume a 60s
        wait for the minute window to roll.
        """
        limits = GroqRateTracker.get_model_limits(model_id)
        tpm_limit = limits.get("tpm")
        if not tpm_limit or tpm_limit <= 0:
            return 0.0

        k = self._key(key_label, model_id)
        projected = simulated_tpm_used.get(k, 0) + chunk_tokens
        pct = (projected / tpm_limit) * 100
        if pct >= self.tpm_backpressure_pct:
            return 60.0
        return 0.0

    def schedule(self, plan: Any) -> ScheduledPlan:
        """
        Produce a ScheduledPlan with realistic timing for every chunk.

        Algorithm:
          1. Iterate chunks in chunk_id order
          2. For each chunk, determine earliest start considering:
             a. RPM pacing from previous request on same key-model
             b. Concurrency limit (max N in-flight per key-model)
             c. TPM backpressure simulation
          3. Compute wait = start - ideal_start
          4. Track in-flight completions in a min-heap per key-model
        """
        # Lazy import avoids circular dependency with plan_generator
        from app.core.plan_generator import ExecutionPlan, ChunkPlan

        if not plan.chunks:
            return ScheduledPlan(
                file_path=plan.file_path,
                total_chunks=0,
                total_tokens=0,
                estimated_total_seconds=0.0,
                makespan_seconds=0.0,
                chunks=[],
                model_id=plan.model_id,
            )

        # Per-key-model state
        last_send_time: Dict[str, float] = {}
        in_flight_heap: Dict[str, List[float]] = {}
        simulated_tpm_used: Dict[str, int] = {}

        scheduled_chunks: List[ScheduledChunk] = []
        total_processing = 0.0
        makespan = 0.0
        warnings: List[str] = []

        gateway = self._gateway_for_model(plan.model_id)

        for chunk in sorted(plan.chunks, key=lambda c: c.chunk_id):
            k = self._key(chunk.key_label, chunk.model_id)

            # ── 1. Base processing time ──
            proc_time = self._processing_time(chunk, gateway)
            total_processing += proc_time

            # ── 2. Ideal start (if no pacing) ──
            ideal_start = 0.0  # Chunks are independent; schedule as early as possible

            # ── 3. RPM pacing (only if this key-model has been used before) ──
            if k in last_send_time:
                rpm_interval = self._rpm_interval(chunk.key_label, chunk.model_id)
                last = last_send_time[k]
                rpm_available = last + rpm_interval
            else:
                rpm_available = ideal_start

            # ── 4. Concurrency wait ──
            concurrency = self._concurrency_limit(chunk.key_label, chunk.model_id)
            heap = in_flight_heap.setdefault(k, [])
            # Pop finished requests until we have a free slot
            while heap and heap[0] <= ideal_start:
                heappop(heap)
            if len(heap) >= concurrency and heap:
                # Wait for the earliest in-flight request to finish
                concurrency_available = heap[0]
            else:
                concurrency_available = ideal_start

            # ── 5. TPM backpressure ──
            tpm_delay = self._tpm_backpressure_delay(
                chunk.key_label, chunk.model_id, chunk.token_count, simulated_tpm_used
            )
            if tpm_delay > 0:
                warnings.append(
                    f"Chunk {chunk.chunk_id} on {chunk.key_label} may hit TPM backpressure "
                    f"(projected > {self.tpm_backpressure_pct:.0f}%)"
                )

            # ── 6. Final start time ──
            start = max(ideal_start, rpm_available, concurrency_available) + tpm_delay
            wait = start - ideal_start
            end = start + proc_time

            # ── 7. Update state ──
            last_send_time[k] = start
            simulated_tpm_used[k] = simulated_tpm_used.get(k, 0) + chunk.token_count
            heappush(heap, end)

            scheduled_chunks.append(
                ScheduledChunk(
                    chunk_id=chunk.chunk_id,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    model_id=chunk.model_id,
                    key_label=chunk.key_label,
                    route=chunk.route,
                    estimated_seconds=round(proc_time, 2),
                    wait_seconds=round(wait, 2),
                    scheduled_start=round(start, 2),
                    estimated_end=round(end, 2),
                    rationale=chunk.rationale,
                )
            )
            makespan = max(makespan, end)

        return ScheduledPlan(
            file_path=plan.file_path,
            total_chunks=len(plan.chunks),
            total_tokens=plan.total_tokens,
            estimated_total_seconds=round(total_processing, 2),
            makespan_seconds=round(makespan, 2),
            chunks=scheduled_chunks,
            model_id=plan.model_id,
            warnings=warnings,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE
# ═══════════════════════════════════════════════════════════════════════════════

def schedule_plan(plan: Any, **scheduler_kwargs) -> ScheduledPlan:
    """One-shot scheduler wrapper."""
    return PlanScheduler(**scheduler_kwargs).schedule(plan)
