"""
PEACOCK ENGINE — Pre-Flight Token Guard (TB-004)
Hard gate: stop bad requests before they ever hit the wire.

Scope:
  • Estimate tokens via TB-003 (tiktoken_counter)
  • Check against TB-001 tracker state (hard limits + soft thresholds)
  • Return structured go/no-go decision with recommended action
  • Context-manager support for automatic enforcement

Design:
  • ZERO dependency on key_manager — candidates are passed explicitly
  • Configurable warn (80%) and block (95%) thresholds
  • Single source of truth: TB-001 tracker for all limit state

Usage:
    # Functional style
    result = await check_request_safety(
        request_data={"messages": [...]},
        model_id="llama-3.3-70b-versatile",
        key_label="G_I7AT",
        candidate_keys=["G_I7AT", "G_8BDJ"],
    )
    if not result.allowed:
        print(f"BLOCKED: {result.reason} → {result.suggested_action}")

    # Context-manager style
    async with guard_context(req, model_id, key_label="G_I7AT") as result:
        strike_result = await strike(key=result.key_label, ...)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Literal
from contextlib import asynccontextmanager

from app.core.tiktoken_counter import count_request_tokens, count_prompt, count_messages
from app.core.rate_limit_tracker import GroqRateTracker
from app.core.config_store import config_store


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG & RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class GuardConfig:
    """Soft-gate thresholds applied on top of TB-001 hard limits.
    Defaults read from runtime config store (TB-021)."""
    warn_threshold: float = field(default_factory=lambda: config_store.guard.get("warn_threshold", 0.80))
    block_threshold: float = field(default_factory=lambda: config_store.guard.get("block_threshold", 0.95))


@dataclass
class SafetyResult:
    """
    Structured decision from the pre-flight guard.

    Fields:
        allowed:         True if the request may proceed
        reason:          Human-readable explanation
        suggested_action: One of proceed / rotate_key / shrink_prompt / wait
        recommended_key:  Best alternative key if rotation is suggested
        key_label:        The key that was evaluated (or would be used)
        model_id:         Model being evaluated
        estimated_tokens: Tiktoken estimate for the request
        status:           green / yellow / red / exhausted
        remaining_*:      Budget telemetry from TB-001
    """
    allowed: bool
    reason: str
    suggested_action: Literal["proceed", "rotate_key", "shrink_prompt", "wait"]
    recommended_key: Optional[str] = None
    key_label: str = ""
    model_id: str = ""
    estimated_tokens: int = 0
    status: Literal["green", "yellow", "red", "exhausted"] = "green"
    remaining_rpm: int = 0
    remaining_tpm: int = 0
    remaining_rpd: int = 0
    remaining_tpd: int = 0


class GuardBlockedError(Exception):
    """Raised by guard_context when the pre-flight check fails."""
    def __init__(self, result: SafetyResult):
        self.result = result
        super().__init__(f"Pre-flight blocked: {result.reason} (action={result.suggested_action})")


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _estimate_tokens(request_data: Dict[str, Any], model_id: str) -> int:
    """Centralized token estimation via TB-003."""
    return count_request_tokens(request_data, model_id)


def _build_candidates(
    key_label: Optional[str],
    candidate_keys: Optional[List[str]],
) -> List[str]:
    """Build an ordered candidate list with preferred key first, deduped."""
    seen: set = set()
    ordered: List[str] = []
    for k in ([key_label] if key_label else []) + (candidate_keys or []):
        if k and k not in seen:
            seen.add(k)
            ordered.append(k)
    return ordered


def _compute_post_utilization(
    telemetry, estimated_tokens: int
) -> Optional[float]:
    """
    Return the highest utilization percentage AFTER the hypothetical request.
    None means no limits are configured.
    """
    pcts = []
    if telemetry.rpm_limit:
        pcts.append((telemetry.rpm_used + 1) / telemetry.rpm_limit)
    if telemetry.tpm_limit:
        pcts.append((telemetry.tpm_used + estimated_tokens) / telemetry.tpm_limit)
    if telemetry.rpd_limit:
        pcts.append((telemetry.rpd_used + 1) / telemetry.rpd_limit)
    if telemetry.tpd_limit:
        pcts.append((telemetry.tpd_used + estimated_tokens) / telemetry.tpd_limit)
    return max(pcts) if pcts else None


def _pick_best_from_telemetry(
    candidates: List[str],
    model_id: str,
    estimated_tokens: int,
) -> Optional[str]:
    """
    Non-async helper: scan candidates and return the one with highest TPM headroom.
    Used for recommended_key when the current key is yellow/red.
    """
    best_key: Optional[str] = None
    best_headroom = -1
    for ck in candidates:
        t = GroqRateTracker.get_telemetry(ck, model_id)
        if t.status == "exhausted":
            continue
        # Simple heuristic: remaining TPM is the bottleneck 99% of the time
        headroom = t.tpm_remaining
        if headroom > best_headroom:
            best_headroom = headroom
            best_key = ck
    return best_key


# ═══════════════════════════════════════════════════════════════════════════════
# CORE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

async def check_request_safety(
    request_data: Dict[str, Any],
    model_id: str,
    key_label: Optional[str] = None,
    config: Optional[GuardConfig] = None,
    candidate_keys: Optional[List[str]] = None,
) -> SafetyResult:
    """
    Clean top-level function: evaluate whether a request is safe to send.

    Hard gate (TB-001):  can_consume() → blocks if limit would be exceeded.
    Soft gate (this fn): threshold check → warns/blocks before redlining.

    Args:
        request_data:   Payload dict (messages / prompt / tools / max_tokens)
        model_id:       Groq model ID
        key_label:      Preferred key label. Evaluated first.
        config:         Guard thresholds. Defaults to warn=80%, block=95%.
        candidate_keys: Ordered list of fallback keys to evaluate.

    Returns:
        SafetyResult with allowed, reason, suggested_action, recommended_key.
    """
    config = config or GuardConfig()
    estimated = _estimate_tokens(request_data, model_id)
    candidates = _build_candidates(key_label, candidate_keys)

    if not candidates:
        return SafetyResult(
            allowed=False,
            reason="No key specified and no candidate list provided.",
            suggested_action="wait",
            model_id=model_id,
            estimated_tokens=estimated,
            status="exhausted",
        )

    preferred = candidates[0]
    any_hard_pass = False
    best_red: Optional[SafetyResult] = None

    for idx, candidate in enumerate(candidates):
        # ── HARD GATE (TB-001) ──
        hard = await GroqRateTracker.can_consume(candidate, model_id, estimated)
        if not hard.allowed:
            continue  # Try next candidate

        any_hard_pass = True

        # ── SOFT GATE (thresholds) ──
        telemetry = GroqRateTracker.get_telemetry(candidate, model_id)
        post_pct = _compute_post_utilization(telemetry, estimated)

        if post_pct is None:
            # No limits configured for this model — treat as green
            return SafetyResult(
                allowed=True,
                reason="No rate limits configured — proceeding.",
                suggested_action="proceed",
                key_label=candidate,
                model_id=model_id,
                estimated_tokens=estimated,
                status="green",
                remaining_rpm=hard.remaining_rpm,
                remaining_tpm=hard.remaining_tpm,
                remaining_rpd=hard.remaining_rpd,
                remaining_tpd=hard.remaining_tpd,
            )

        # Find next best candidate for rotation suggestions
        next_candidates = candidates[idx + 1:]
        fallback = _pick_best_from_telemetry(next_candidates, model_id, estimated) if next_candidates else None

        if post_pct >= config.block_threshold:
            # Too hot — record as best red fallback, then try next candidate
            red = SafetyResult(
                allowed=False,
                reason=(
                    f"Key {candidate} would hit {post_pct * 100:.1f}% utilization "
                    f"(block threshold {config.block_threshold * 100:.0f}%)."
                ),
                suggested_action="rotate_key" if fallback else "shrink_prompt",
                recommended_key=fallback,
                key_label=candidate,
                model_id=model_id,
                estimated_tokens=estimated,
                status="red",
                remaining_rpm=hard.remaining_rpm,
                remaining_tpm=hard.remaining_tpm,
                remaining_rpd=hard.remaining_rpd,
                remaining_tpd=hard.remaining_tpd,
            )
            if best_red is None or hard.remaining_tpm > best_red.remaining_tpm:
                best_red = red
            continue  # Try next candidate

        if post_pct >= config.warn_threshold:
            return SafetyResult(
                allowed=True,
                reason=(
                    f"Key {candidate} would hit {post_pct * 100:.1f}% utilization "
                    f"(warn threshold {config.warn_threshold * 100:.0f}%). "
                    f"Consider rotating to {fallback or 'N/A'}."
                ),
                suggested_action="rotate_key" if fallback else "proceed",
                recommended_key=fallback,
                key_label=candidate,
                model_id=model_id,
                estimated_tokens=estimated,
                status="yellow",
                remaining_rpm=hard.remaining_rpm,
                remaining_tpm=hard.remaining_tpm,
                remaining_rpd=hard.remaining_rpd,
                remaining_tpd=hard.remaining_tpd,
            )

        # All clear
        return SafetyResult(
            allowed=True,
            reason="All limits within safe margins.",
            suggested_action="proceed",
            key_label=candidate,
            model_id=model_id,
            estimated_tokens=estimated,
            status="green",
            remaining_rpm=hard.remaining_rpm,
            remaining_tpm=hard.remaining_tpm,
            remaining_rpd=hard.remaining_rpd,
            remaining_tpd=hard.remaining_tpd,
        )

    # ── NO CANDIDATE PASSED SOFT GATE ──
    if best_red is not None:
        return best_red

    # ── NO CANDIDATE PASSED HARD GATE ──
    return SafetyResult(
        allowed=False,
        reason="All candidate keys would breach hard limits.",
        suggested_action="wait",
        key_label=preferred,
        model_id=model_id,
        estimated_tokens=estimated,
        status="exhausted",
    )


@asynccontextmanager
async def guard_context(
    request_data: Dict[str, Any],
    model_id: str,
    key_label: Optional[str] = None,
    config: Optional[GuardConfig] = None,
    candidate_keys: Optional[List[str]] = None,
):
    """
    Async context manager that automatically enforces the pre-flight gate.

    Usage:
        async with guard_context(req, model_id, key_label="G_I7AT") as result:
            # result is SafetyResult with allowed=True
            strike = await execute_strike(key=result.key_label, ...)

    Raises:
        GuardBlockedError if the request would breach limits.
    """
    result = await check_request_safety(
        request_data, model_id, key_label, config, candidate_keys
    )
    if not result.allowed:
        raise GuardBlockedError(result)
    yield result


# ═══════════════════════════════════════════════════════════════════════════════
# CLASS API (backward-compatible wrapper around the functional core)
# ═══════════════════════════════════════════════════════════════════════════════

class PreFlightGuard:
    """
    Class-based API for callers that prefer OO style or need persistent config.

    Usage:
        guard = PreFlightGuard(GuardConfig(warn_threshold=0.75, block_threshold=0.90))
        result = await guard.check("llama-3.3-70b-versatile", "Hello world", candidate_keys=[...])
    """

    def __init__(self, config: Optional[GuardConfig] = None):
        self.config = config or GuardConfig()

    async def check(
        self,
        model_id: str,
        prompt: str,
        key_label: Optional[str] = None,
        candidate_keys: Optional[List[str]] = None,
    ) -> SafetyResult:
        """Pre-flight a plain-text prompt."""
        return await check_request_safety(
            request_data={"messages": [{"role": "user", "content": prompt}]},
            model_id=model_id,
            key_label=key_label,
            config=self.config,
            candidate_keys=candidate_keys,
        )

    async def check_messages(
        self,
        model_id: str,
        messages: List[Dict[str, Any]],
        key_label: Optional[str] = None,
        candidate_keys: Optional[List[str]] = None,
    ) -> SafetyResult:
        """Pre-flight a chat-message payload."""
        return await check_request_safety(
            request_data={"messages": messages},
            model_id=model_id,
            key_label=key_label,
            config=self.config,
            candidate_keys=candidate_keys,
        )

    async def check_request(
        self,
        model_id: str,
        request_data: Dict[str, Any],
        key_label: Optional[str] = None,
        candidate_keys: Optional[List[str]] = None,
    ) -> SafetyResult:
        """Pre-flight a full request dict (messages + tools + prompt + max_tokens)."""
        return await check_request_safety(
            request_data=request_data,
            model_id=model_id,
            key_label=key_label,
            config=self.config,
            candidate_keys=candidate_keys,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

GroqPreFlightGuard = PreFlightGuard()
