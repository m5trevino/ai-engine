"""
PEACOCK ENGINE — Usage Sync Layer (TB-006)
Reconciles estimated token counts with real Groq response data.

Scope:
  • After every Groq call, parse response headers + usage (TB-005)
  • Sync tracker counters to ground-truth values from headers (TB-001)
  • Log estimate-vs-actual discrepancies for debugging

References:
  • app.core.groq_response_parser (TB-005)
  • app.core.rate_limit_tracker   (TB-001)
"""

import os
from typing import Optional

from app.core.groq_response_parser import GroqResponseMeta, GroqResponseParser
from app.core.rate_limit_tracker import GroqRateTracker


class UsageSync:
    """
    Sync layer that keeps the rate-limit tracker aligned with reality.

    Usage (after a raw httpx/groq call):
        meta = GroqResponseParser.parse_from_httpx(response, model_id="llama-3.3-70b-versatile")
        await UsageSync.sync_from_meta("G_I7AT", "llama-3.3-70b-versatile", meta, estimated_tokens=1500)

    Usage (from raw body + headers):
        await UsageSync.sync_from_raw("G_I7AT", "llama-3.3-70b-versatile", body, headers, estimated_tokens=1500)
    """

    @staticmethod
    async def sync_from_meta(
        key_label: str,
        model_id: str,
        meta: GroqResponseMeta,
        estimated_tokens: Optional[int] = None,
    ):
        """
        Reconcile tracker state with parsed Groq response metadata.

        Args:
            key_label: The API key that was used for the request
            model_id: The model ID that was called
            meta: Parsed GroqResponseMeta from TB-005
            estimated_tokens: Optional pre-flight estimate for discrepancy logging
        """
        rl = meta.rate_limits
        limits = GroqRateTracker.get_model_limits(model_id)
        rpd_lim = limits.get("rpd")
        tpm_lim = limits.get("tpm")

        # ── Ground truth from headers ──
        # Groq headers tell us exact remaining budget. We back-calculate used.
        actual_rpd_used: Optional[int] = None
        actual_tpm_used: Optional[int] = None

        if rpd_lim is not None and rl.remaining_requests is not None:
            actual_rpd_used = rpd_lim - rl.remaining_requests
            actual_rpd_used = max(0, min(actual_rpd_used, rpd_lim))

        if tpm_lim is not None and rl.remaining_tokens is not None:
            actual_tpm_used = tpm_lim - rl.remaining_tokens
            actual_tpm_used = max(0, min(actual_tpm_used, tpm_lim))

        # ── Sync tracker to reality ──
        await GroqRateTracker.sync_counters(
            key_label,
            model_id,
            rpd_used=actual_rpd_used,
            tpm_used=actual_tpm_used,
        )

        # ── Discrepancy logging ──
        if estimated_tokens is not None and os.getenv("PEACOCK_VERBOSE") == "true":
            actual = meta.usage.total_tokens
            diff = abs(estimated_tokens - actual)
            accuracy = 100 - (diff / actual * 100) if actual > 0 else 0.0
            print(
                f"[UsageSync] {key_label} | {model_id} | "
                f"Est:{estimated_tokens} | Act:{actual} | Diff:{diff} | Acc:{accuracy:.1f}% | "
                f"RPD:{actual_rpd_used}/{rpd_lim} | TPM:{actual_tpm_used}/{tpm_lim}"
            )

    @staticmethod
    async def sync_from_raw(
        key_label: str,
        model_id: str,
        body,
        headers,
        estimated_tokens: Optional[int] = None,
    ):
        """
        Convenience wrapper: parse raw response body + headers, then sync.
        """
        meta = GroqResponseParser.parse(body=body, headers=headers, model_id=model_id)
        await UsageSync.sync_from_meta(key_label, model_id, meta, estimated_tokens)

    @staticmethod
    async def sync_usage_only(
        key_label: str,
        model_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_tokens: Optional[int] = None,
    ):
        """
        Fallback when only usage numbers are available (no headers).
        Calls consume() with actual tokens to keep counters accurate.
        Use this when integrating with pydantic-ai or other high-level clients
        that don't expose raw HTTP headers.
        """
        total = prompt_tokens + completion_tokens
        if total > 0:
            await GroqRateTracker.consume(key_label, model_id, total)

        if estimated_tokens is not None and os.getenv("PEACOCK_VERBOSE") == "true":
            diff = abs(estimated_tokens - total)
            accuracy = 100 - (diff / total * 100) if total > 0 else 0.0
            print(
                f"[UsageSync] {key_label} | {model_id} | "
                f"Est:{estimated_tokens} | Act:{total} | Diff:{diff} | Acc:{accuracy:.1f}% (usage-only)"
            )
