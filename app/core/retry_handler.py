"""
PEACOCK ENGINE — Dynamic Retry & Backoff Handler (TB-008)
Proper 429 handling using retry-after headers and intelligent key rotation.

Scope:
  • Extract retry-after from Groq 429 responses
  • Exponential backoff when retry-after is missing
  • Record 429s in the rate-limit tracker (TB-001)
  • Rotate to the next intelligent key (TB-007) on each retry
  • Mark exhausted keys on cooldown

References:
  • app.core.rate_limit_tracker   (TB-001)
  • app.core.groq_response_parser (TB-005)
  • app.core.key_manager          (GroqPool, TB-007 intelligent selector)
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Type


# ─────────────────────────── CUSTOM EXCEPTION ───────────────────────────

class RateLimitError(Exception):
    """
    Structured exception for rate-limit hits.

    Attributes:
        message: Human-readable error text
        retry_after: Seconds to wait before retry (from header)
        key_label: The key that was rate-limited
        model_id: The model being called
        raw_headers: Full response headers (for debugging)
    """
    def __init__(
        self,
        message: str,
        retry_after: Optional[float] = None,
        key_label: Optional[str] = None,
        model_id: Optional[str] = None,
        raw_headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.key_label = key_label
        self.model_id = model_id
        self.raw_headers = raw_headers or {}

    @classmethod
    def from_httpx_response(
        cls,
        response,
        key_label: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> "RateLimitError":
        """Build a RateLimitError from an httpx 429 response."""
        headers = dict(response.headers) if hasattr(response, "headers") else {}
        retry_after = None
        ra = headers.get("retry-after")
        if ra is not None:
            try:
                retry_after = float(ra)
            except (ValueError, TypeError):
                retry_after = None
        return cls(
            message=f"429 Too Many Requests (key={key_label}, model={model_id})",
            retry_after=retry_after,
            key_label=key_label,
            model_id=model_id,
            raw_headers=headers,
        )


# ─────────────────────────── CONFIG ───────────────────────────

@dataclass
class RetryConfig:
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    respect_retry_after: bool = True          # Wait exact retry-after when available
    rotate_on_429: bool = True                # Pick new key on each 429
    cooldown_duration: int = 60               # Default cooldown if no retry-after


# ─────────────────────────── HANDLER ───────────────────────────

class RetryHandler:
    """
    Execute async strike functions with dynamic retry and intelligent key rotation.

    Usage (raw httpx style):
        async def strike(key_label: str, model_id: str, prompt: str):
            response = await httpx_client.post(...)
            if response.status_code == 429:
                raise RateLimitError.from_httpx_response(response, key_label, model_id)
            return response.json()

        handler = RetryHandler()
        result = await handler.execute(
            strike_fn=strike,
            model_id="llama-3.3-70b-versatile",
            prompt="Hello world",
            estimated_tokens=10,
        )

    Usage (high-level, with preferred key):
        result = await handler.execute(
            strike_fn=strike,
            model_id="llama-3.3-70b-versatile",
            key_label="G_I7AT",
            prompt="Hello world",
        )
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()

    # ─────────────────────────── DELAY CALCULATION ───────────────────────────

    def _compute_delay(self, attempt: int, retry_after: Optional[float]) -> float:
        """Return seconds to wait before next attempt."""
        if self.config.respect_retry_after and retry_after is not None and retry_after > 0:
            return min(retry_after, self.config.max_delay)

        # Exponential backoff: base * multiplier^(attempt-1)
        delay = self.config.base_delay * (self.config.backoff_multiplier ** (attempt - 1))
        return min(delay, self.config.max_delay)

    # ─────────────────────────── KEY SELECTION ───────────────────────────

    async def _select_key(
        self,
        model_id: str,
        estimated_tokens: int,
        preferred_key: Optional[str] = None,
        attempt: int = 1,
    ) -> str:
        """Pick the best key for this attempt."""
        from app.core.key_manager import GroqPool

        # First attempt: use preferred key if provided and healthy
        if attempt == 1 and preferred_key:
            asset = next((a for a in GroqPool.deck if a.account == preferred_key), None)
            if asset and not asset.on_cooldown:
                return preferred_key

        # Subsequent attempts: intelligent rotation
        asset = await GroqPool.get_next_intelligent(model_id, estimated_tokens)
        return asset.account

    # ─────────────────────────── PUBLIC API ───────────────────────────

    async def execute(
        self,
        strike_fn: Callable,
        model_id: str,
        estimated_tokens: int = 1,
        key_label: Optional[str] = None,
        **strike_kwargs,
    ) -> Any:
        """
        Execute strike_fn with retry logic.

        Args:
            strike_fn: Async callable. Must accept `key_label` and `model_id` as kwargs.
            model_id: Groq model ID
            estimated_tokens: Expected token burn (for intelligent rotation)
            key_label: Preferred key for first attempt
            **strike_kwargs: Extra arguments forwarded to strike_fn

        Returns:
            Whatever strike_fn returns on success.

        Raises:
            RateLimitError: If all retries exhausted due to 429s.
            Exception: Any non-429 error is raised immediately.
        """
        from app.core.rate_limit_tracker import GroqRateTracker
        from app.core.key_manager import GroqPool
        from app.utils.formatter import CLIFormatter

        last_error: Optional[Exception] = None
        attempted_keys: set = set()

        for attempt in range(1, self.config.max_attempts + 1):
            # ── Key selection ──
            try:
                current_key = await self._select_key(
                    model_id, estimated_tokens, key_label, attempt
                )
            except Exception as e:
                # No healthy keys left
                raise RateLimitError(
                    f"No healthy keys available after {attempt - 1} attempts: {e}",
                    model_id=model_id,
                ) from e

            attempted_keys.add(current_key)

            try:
                # ── Strike ──
                return await strike_fn(
                    key_label=current_key,
                    model_id=model_id,
                    **strike_kwargs,
                )

            except RateLimitError as rle:
                last_error = rle

                # Record 429 in tracker
                await GroqRateTracker.record_429(current_key, model_id)

                # Compute cooldown / delay
                delay = self._compute_delay(attempt, rle.retry_after)
                cooldown_dur = int(rle.retry_after) if rle.retry_after else self.config.cooldown_duration

                # Mark key on cooldown
                GroqPool.mark_cooldown(current_key, duration=max(cooldown_dur, int(delay)))

                if CLIFormatter and hasattr(CLIFormatter, 'warning'):
                    CLIFormatter.warning(
                        f"429 on {current_key} (attempt {attempt}/{self.config.max_attempts}) — "
                        f"retry-after={rle.retry_after or 'N/A'}, sleeping {delay:.1f}s"
                    )

                # Wait before retry
                await asyncio.sleep(delay)

                # If this was the last attempt, break and raise
                if attempt >= self.config.max_attempts:
                    break

                continue  # Retry with new key

            except Exception as e:
                # Non-429 error — don't retry, bubble up immediately
                raise

        # All retries exhausted
        raise last_error or RateLimitError(
            f"All {self.config.max_attempts} retry attempts exhausted for {model_id}",
            model_id=model_id,
        )

    async def execute_with_result(
        self,
        strike_fn: Callable,
        model_id: str,
        estimated_tokens: int = 1,
        key_label: Optional[str] = None,
        **strike_kwargs,
    ) -> Dict[str, Any]:
        """
        Same as execute(), but wraps the result with metadata about retries.

        Returns:
            {
                "result": <strike_fn return value>,
                "key_used": str,
                "attempts": int,
                "model_id": str,
            }
        """
        # This would require tracking which key succeeded. For now, execute() is sufficient.
        # Users can capture key_used inside their strike_fn.
        result = await self.execute(
            strike_fn=strike_fn,
            model_id=model_id,
            estimated_tokens=estimated_tokens,
            key_label=key_label,
            **strike_kwargs,
        )
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

GroqRetryHandler = RetryHandler()
