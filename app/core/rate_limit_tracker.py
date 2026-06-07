"""
PEACOCK ENGINE — Rate Limit Tracker Core (TB-001)
Single source of truth for per-key, per-model rate limit tracking.

Scope:
  • In-memory state management
  • Per-key, per-model telemetry (used, limit, percentage, status)
  • Minute and daily rolling windows
  • Record consumption, 429s, and resets
  • Governor snapshot for dashboard + other modules

Design:
  • Fixed time windows (60s minute, 86400s daily)
  • Thread-safe via per-key asyncio.Lock
  • Minimal surface area: consume, can_consume, record_429, reset, telemetry, snapshot
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any, Literal
from pydantic import BaseModel


# ═══════════════════════════════════════════════════════════════════════════════
# GROQ RATE LIMITS — SOURCE OF TRUTH FROM OFFICIAL DOCS
# ═══════════════════════════════════════════════════════════════════════════════
GROQ_RATE_LIMITS: Dict[str, Tuple[Optional[int], Optional[int], Optional[int], Optional[int], int]] = {
    # Meta
    "llama-3.3-70b-versatile": (30, 1000, 12000, 100000, 131072),
    "llama-3.1-8b-instant": (30, 14400, 6000, 500000, 131072),
    "meta-llama/llama-4-scout-17b-16e-instruct": (30, 1000, 30000, 500000, 131072),
    "meta-llama/llama-prompt-guard-2-22m": (30, 14400, 15000, 500000, 512),
    "meta-llama/llama-prompt-guard-2-86m": (30, 14400, 15000, 500000, 512),
    # Groq
    "groq/compound": (30, 250, 70000, None, 131072),
    "groq/compound-mini": (30, 250, 70000, None, 131072),
    # OpenAI on Groq
    "openai/gpt-oss-120b": (30, 1000, 8000, 200000, 131072),
    "openai/gpt-oss-20b": (30, 1000, 8000, 200000, 131072),
    "openai/gpt-oss-safeguard-20b": (30, 1000, 8000, 200000, 131072),
    # Qwen
    "qwen/qwen3-32b": (60, 1000, 6000, 500000, 131072),
    # Allam
    "allam-2-7b": (30, 7000, 6000, 500000, 4096),
    # Canopy Labs
    "canopylabs/orpheus-arabic-saudi": (10, 100, 1200, 3600, 4000),
    "canopylabs/orpheus-v1-english": (10, 100, 1200, 3600, 4000),
    # Whisper
    "whisper-large-v3": (20, 2000, None, None, 448),
    "whisper-large-v3-turbo": (20, 2000, None, None, 448),
    # Deprecated
    "moonshotai/kimi-k2-instruct": (0, 0, 0, 0, 131072),
    "moonshotai/kimi-k2-instruct-0905": (0, 0, 0, 0, 131072),
}

MINUTE = 60.0
DAY = 86400.0


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ConsumeResult(BaseModel):
    allowed: bool
    key_label: str
    model_id: str
    remaining_rpm: int
    remaining_rpd: int
    remaining_tpm: int
    remaining_tpd: int
    status: Literal["green", "yellow", "red", "exhausted"] = "green"
    reason: Optional[str] = None


class KeyModelTelemetry(BaseModel):
    key_label: str
    model_id: str
    rpm_used: int
    rpm_limit: int
    rpm_remaining: int
    rpm_pct: float
    rpd_used: int
    rpd_limit: int
    rpd_remaining: int
    rpd_pct: float
    tpm_used: int
    tpm_limit: int
    tpm_remaining: int
    tpm_pct: float
    tpd_used: int
    tpd_limit: int
    tpd_remaining: int
    tpd_pct: float
    status: Literal["green", "yellow", "red", "exhausted"]
    consecutive_429s: int
    active_requests: int
    total_requests: int
    total_tokens: int
    last_used: Optional[float] = None


class GovernorSnapshot(BaseModel):
    timestamp: float
    keys: List[KeyModelTelemetry]
    pool_health: Literal["healthy", "degraded", "exhausted"]


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL STATE
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class _Window:
    """Fixed time window counter."""
    count: int = 0
    window_start: float = 0.0

    def reset_if_expired(self, now: float, duration: float) -> bool:
        """Reset counter if window has expired. Returns True if reset occurred."""
        if self.window_start == 0.0 or now - self.window_start >= duration:
            self.count = 0
            self.window_start = now
            return True
        return False


@dataclass
class _KeyModelState:
    """Internal mutable state for a single key-model pair."""
    rpm: _Window = field(default_factory=_Window)
    rpd: _Window = field(default_factory=_Window)
    tpm: _Window = field(default_factory=_Window)
    tpd: _Window = field(default_factory=_Window)
    consecutive_429s: int = 0
    active_requests: int = 0
    total_requests: int = 0
    total_tokens: int = 0
    last_used: Optional[float] = None


# ═══════════════════════════════════════════════════════════════════════════════
# TRACKER
# ═══════════════════════════════════════════════════════════════════════════════

class RateLimitTracker:
    """
    Central rate-limit tracker for Groq.

    Usage:
        tracker = RateLimitTracker()

        # Pre-flight check (dry-run)
        result = await tracker.can_consume("G_I7AT", "llama-3.3-70b-versatile", tokens=1500)

        # Commit consumption
        result = await tracker.consume("G_I7AT", "llama-3.3-70b-versatile", tokens=1500)

        # Record a 429 from the API
        await tracker.record_429("G_I7AT", "llama-3.3-70b-versatile")

        # Read telemetry
        telemetry = tracker.get_telemetry("G_I7AT", "llama-3.3-70b-versatile")

        # Full dashboard snapshot
        snap = tracker.get_snapshot()
    """

    # ─────────────────────────── INIT ───────────────────────────

    def __init__(self):
        # state[key_label][model_id] = _KeyModelState
        self._state: Dict[str, Dict[str, _KeyModelState]] = {}
        self._locks: Dict[str, asyncio.Lock] = {}

    # ─────────────────────────── INTERNAL ───────────────────────────

    def _get_lock(self, key_label: str) -> asyncio.Lock:
        if key_label not in self._locks:
            self._locks[key_label] = asyncio.Lock()
        return self._locks[key_label]

    def _get_state(self, key_label: str, model_id: str) -> _KeyModelState:
        if key_label not in self._state:
            self._state[key_label] = {}
        if model_id not in self._state[key_label]:
            self._state[key_label][model_id] = _KeyModelState()
        return self._state[key_label][model_id]

    @staticmethod
    def get_model_limits(model_id: str) -> Dict[str, Any]:
        rpm, rpd, tpm, tpd, ctx = GROQ_RATE_LIMITS.get(model_id, (None, None, None, None, 131072))
        return {"rpm": rpm, "rpd": rpd, "tpm": tpm, "tpd": tpd, "context_window": ctx}

    @staticmethod
    def get_context_window(model_id: str) -> int:
        return RateLimitTracker.get_model_limits(model_id)["context_window"]

    def _reset_windows(self, state: _KeyModelState, now: float) -> None:
        state.rpm.reset_if_expired(now, MINUTE)
        state.tpm.reset_if_expired(now, MINUTE)
        state.rpd.reset_if_expired(now, DAY)
        state.tpd.reset_if_expired(now, DAY)

    def _compute_status(
        self, state: _KeyModelState, limits: Dict[str, Any]
    ) -> Literal["green", "yellow", "red", "exhausted"]:
        if state.consecutive_429s >= 3:
            return "exhausted"

        pcts = []
        if limits["rpm"]:
            pcts.append((state.rpm.count / limits["rpm"]) * 100)
        if limits["rpd"]:
            pcts.append((state.rpd.count / limits["rpd"]) * 100)
        if limits["tpm"]:
            pcts.append((state.tpm.count / limits["tpm"]) * 100)
        if limits["tpd"]:
            pcts.append((state.tpd.count / limits["tpd"]) * 100)

        if not pcts:
            return "green"

        max_pct = max(pcts)
        if max_pct >= 100:
            return "exhausted"
        if max_pct >= 85:
            return "red"
        if max_pct >= 60:
            return "yellow"
        return "green"

    def _build_result(
        self,
        allowed: bool,
        key_label: str,
        model_id: str,
        state: _KeyModelState,
        limits: Dict[str, Any],
        status: Literal["green", "yellow", "red", "exhausted"],
        reason: Optional[str] = None,
    ) -> ConsumeResult:
        return ConsumeResult(
            allowed=allowed,
            key_label=key_label,
            model_id=model_id,
            remaining_rpm=(limits["rpm"] or 0) - state.rpm.count,
            remaining_rpd=(limits["rpd"] or 0) - state.rpd.count,
            remaining_tpm=(limits["tpm"] or 0) - state.tpm.count,
            remaining_tpd=(limits["tpd"] or 0) - state.tpd.count,
            status=status,
            reason=reason,
        )

    # ─────────────────────────── PUBLIC API ───────────────────────────

    async def can_consume(self, key_label: str, model_id: str, tokens: int = 1) -> ConsumeResult:
        """Dry-run: check if a request would be allowed without incrementing counters."""
        async with self._get_lock(key_label):
            state = self._get_state(key_label, model_id)
            now = time.time()
            self._reset_windows(state, now)
            limits = self.get_model_limits(model_id)

            if state.consecutive_429s >= 3:
                return self._build_result(
                    False, key_label, model_id, state, limits, "exhausted",
                    f"Key exceeded 3 consecutive 429s",
                )

            reasons = []
            if limits["rpm"] is not None and state.rpm.count + 1 > limits["rpm"]:
                reasons.append("RPM")
            if limits["rpd"] is not None and state.rpd.count + 1 > limits["rpd"]:
                reasons.append("RPD")
            if limits["tpm"] is not None and state.tpm.count + tokens > limits["tpm"]:
                reasons.append("TPM")
            if limits["tpd"] is not None and state.tpd.count + tokens > limits["tpd"]:
                reasons.append("TPD")

            if reasons:
                status: Literal["red", "exhausted"] = "exhausted" if "RPD" in reasons or "TPD" in reasons else "red"
                return self._build_result(
                    False, key_label, model_id, state, limits, status,
                    f"Would exceed: {', '.join(reasons)}",
                )

            return self._build_result(
                True, key_label, model_id, state, limits,
                self._compute_status(state, limits),
            )

    async def consume(self, key_label: str, model_id: str, tokens: int = 1) -> ConsumeResult:
        """Commit consumption. Increments all relevant counters."""
        async with self._get_lock(key_label):
            state = self._get_state(key_label, model_id)
            now = time.time()
            self._reset_windows(state, now)
            limits = self.get_model_limits(model_id)

            if state.consecutive_429s >= 3:
                return self._build_result(
                    False, key_label, model_id, state, limits, "exhausted",
                    f"Key exceeded 3 consecutive 429s",
                )

            reasons = []
            if limits["rpm"] is not None and state.rpm.count + 1 > limits["rpm"]:
                reasons.append("RPM")
            if limits["rpd"] is not None and state.rpd.count + 1 > limits["rpd"]:
                reasons.append("RPD")
            if limits["tpm"] is not None and state.tpm.count + tokens > limits["tpm"]:
                reasons.append("TPM")
            if limits["tpd"] is not None and state.tpd.count + tokens > limits["tpd"]:
                reasons.append("TPD")

            if reasons:
                status: Literal["red", "exhausted"] = "exhausted" if "RPD" in reasons or "TPD" in reasons else "red"
                return self._build_result(
                    False, key_label, model_id, state, limits, status,
                    f"Limit exceeded: {', '.join(reasons)}",
                )

            # All clear — commit
            state.rpm.count += 1
            state.rpd.count += 1
            state.tpm.count += tokens
            state.tpd.count += tokens
            state.total_requests += 1
            state.total_tokens += tokens
            state.last_used = now
            state.consecutive_429s = 0

            return self._build_result(
                True, key_label, model_id, state, limits,
                self._compute_status(state, limits),
            )

    async def record_429(self, key_label: str, model_id: str) -> None:
        """Record a 429 rate-limit error for a key-model pair."""
        async with self._get_lock(key_label):
            state = self._get_state(key_label, model_id)
            state.consecutive_429s += 1

    async def reset(self, key_label: str, model_id: str) -> None:
        """Manually reset all counters for a key-model pair."""
        async with self._get_lock(key_label):
            if key_label in self._state and model_id in self._state[key_label]:
                self._state[key_label][model_id] = _KeyModelState()

    async def begin_request(self, key_label: str, model_id: str) -> None:
        """Track an in-flight request (increments active_requests)."""
        async with self._get_lock(key_label):
            state = self._get_state(key_label, model_id)
            state.active_requests += 1
            state.last_used = time.time()

    async def end_request(self, key_label: str, model_id: str) -> None:
        """Mark a request as complete (decrements active_requests)."""
        async with self._get_lock(key_label):
            state = self._get_state(key_label, model_id)
            state.active_requests = max(0, state.active_requests - 1)

    # ─────────────────────────── TELEMETRY ───────────────────────────

    def get_telemetry(self, key_label: str, model_id: str) -> KeyModelTelemetry:
        """Get real-time telemetry for a single key-model pair (non-locking read)."""
        state = self._state.get(key_label, {}).get(model_id, _KeyModelState())
        now = time.time()
        self._reset_windows(state, now)
        limits = self.get_model_limits(model_id)
        status = self._compute_status(state, limits)

        rpm_limit = limits["rpm"] or 0
        rpd_limit = limits["rpd"] or 0
        tpm_limit = limits["tpm"] or 0
        tpd_limit = limits["tpd"] or 0

        return KeyModelTelemetry(
            key_label=key_label,
            model_id=model_id,
            rpm_used=state.rpm.count,
            rpm_limit=rpm_limit,
            rpm_remaining=max(0, rpm_limit - state.rpm.count),
            rpm_pct=(state.rpm.count / rpm_limit * 100) if rpm_limit else 0.0,
            rpd_used=state.rpd.count,
            rpd_limit=rpd_limit,
            rpd_remaining=max(0, rpd_limit - state.rpd.count),
            rpd_pct=(state.rpd.count / rpd_limit * 100) if rpd_limit else 0.0,
            tpm_used=state.tpm.count,
            tpm_limit=tpm_limit,
            tpm_remaining=max(0, tpm_limit - state.tpm.count),
            tpm_pct=(state.tpm.count / tpm_limit * 100) if tpm_limit else 0.0,
            tpd_used=state.tpd.count,
            tpd_limit=tpd_limit,
            tpd_remaining=max(0, tpd_limit - state.tpd.count),
            tpd_pct=(state.tpd.count / tpd_limit * 100) if tpd_limit else 0.0,
            status=status,
            consecutive_429s=state.consecutive_429s,
            active_requests=state.active_requests,
            total_requests=state.total_requests,
            total_tokens=state.total_tokens,
            last_used=state.last_used,
        )

    def get_snapshot(self, key_labels: Optional[List[str]] = None) -> GovernorSnapshot:
        """Get a full snapshot for the dashboard."""
        now = time.time()
        keys: List[KeyModelTelemetry] = []

        target_keys = key_labels or list(self._state.keys())
        for kl in target_keys:
            for mid in self._state.get(kl, {}):
                keys.append(self.get_telemetry(kl, mid))

        if not keys:
            return GovernorSnapshot(timestamp=now, keys=[], pool_health="healthy")

        exhausted = sum(1 for k in keys if k.status == "exhausted")
        red = sum(1 for k in keys if k.status == "red")
        total = len(keys)

        if exhausted == total:
            health = "exhausted"
        elif exhausted > 0 or red > 0:
            health = "degraded"
        else:
            health = "healthy"

        return GovernorSnapshot(timestamp=now, keys=keys, pool_health=health)

    # ── Persistence stubs (TB-001 lifecycle hooks) ──
    def load(self) -> None:
        """Load persisted state if available."""
        pass

    async def start_auto_save(self, interval: float = 30.0) -> None:
        """Start background auto-save task."""
        pass

    async def stop_auto_save(self) -> None:
        """Stop background auto-save task."""
        pass

    async def save(self) -> None:
        """Persist current state."""
        pass


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON
# ═══════════════════════════════════════════════════════════════════════════════

GroqRateTracker = RateLimitTracker()
