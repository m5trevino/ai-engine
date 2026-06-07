"""
PEACOCK ENGINE — Global Pacing Coordinator (TB-009)
Lightweight global throttle that prevents org-level limit violations
across concurrent workers.

Scope:
  • Per-key-model semaphore (limits in-flight burst)
  • RPM pacing (minimum interval between requests)
  • TPM backpressure (delay when near ceiling)
  • Adaptive concurrency based on model RPM

References:
  • app.core.rate_limit_tracker (TB-001)
  • app.core.key_manager        (GroqPool)
"""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from app.core.rate_limit_tracker import GroqRateTracker
from app.core.config_store import config_store


class GlobalPacer:
    """
    Lightweight global throttle for concurrent workers.

    Usage (context manager — recommended):
        async with GroqPacer.gate("G_I7AT", "llama-3.3-70b-versatile", estimated_tokens=1500):
            result = await execute_strike(...)

    Usage (manual acquire/release):
        await GroqPacer.acquire("G_I7AT", "llama-3.3-70b-versatile", 1500)
        try:
            result = await execute_strike(...)
        finally:
            GroqPacer.release("G_I7AT", "llama-3.3-70b-versatile")
    """

    def __init__(self, default_concurrency: int = 2):
        self._default_concurrency_override = default_concurrency
        self.default_concurrency = config_store.pacer.get("default_concurrency", default_concurrency)
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._last_request_time: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    # ─────────────────────────── INTERNAL HELPERS ───────────────────────────

    @staticmethod
    def _key(key_label: str, model_id: str) -> str:
        return f"{key_label}:{model_id}"

    def _concurrency_for_model(self, model_id: str) -> int:
        """Adaptive concurrency: low-RPM models get serialized, high-RPM can parallelize.
        Burn mode overrides from runtime config (TB-021)."""
        mode = config_store.burn_mode
        limits = GroqRateTracker.get_model_limits(model_id)
        rpm = limits.get("rpm")
        if rpm is None:
            return self.default_concurrency

        # Burn-mode multipliers
        if mode == "CONSERVATIVE":
            if rpm <= 30:
                return 1
            if rpm <= 100:
                return 2
            return 3
        elif mode == "ULTRA":
            if rpm <= 10:
                return 2
            if rpm <= 30:
                return 4
            if rpm <= 100:
                return 6
            return 8
        # BALANCED (default)
        if rpm <= 10:
            return 1
        if rpm <= 30:
            return 2
        if rpm <= 100:
            return 3
        if rpm <= 1000:
            return 4
        return 5

    def _get_semaphore(self, key_label: str, model_id: str) -> asyncio.Semaphore:
        k = self._key(key_label, model_id)
        if k not in self._semaphores:
            concurrency = self._concurrency_for_model(model_id)
            self._semaphores[k] = asyncio.Semaphore(concurrency)
        return self._semaphores[k]

    async def _wait_for_rpm(self, key_label: str, model_id: str):
        """Enforce minimum inter-request interval to stay under RPM."""
        k = self._key(key_label, model_id)
        limits = GroqRateTracker.get_model_limits(model_id)
        rpm = limits.get("rpm")
        if not rpm or rpm <= 0:
            return

        async with self._lock:
            now = time.time()
            last = self._last_request_time.get(k, 0.0)
            min_interval = 60.0 / rpm
            elapsed = now - last

            if elapsed < min_interval:
                wait = min_interval - elapsed
                await asyncio.sleep(wait)

            self._last_request_time[k] = time.time()

    async def _wait_for_tpm(self, key_label: str, model_id: str, estimated_tokens: int):
        """TPM backpressure: if we're near the ceiling, wait for the minute window to roll."""
        limits = GroqRateTracker.get_model_limits(model_id)
        tpm = limits.get("tpm")
        if not tpm or tpm <= 0:
            return

        telemetry = GroqRateTracker.get_telemetry(key_label, model_id)

        # If adding this request would push us over the backpressure threshold,
        # pause until window resets. Threshold controlled by runtime config (TB-021).
        backpressure_pct = config_store.pacer.get("tpm_backpressure_pct", 90)
        if telemetry.tpm_pct >= backpressure_pct:
            # Peek at the tracker's internal window start to know exactly how long to wait
            state = GroqRateTracker._state.get(key_label, {}).get(model_id)
            if state and state.tpm_start > 0:
                remaining = max(0.0, 60.0 - (time.time() - state.tpm_start))
                await asyncio.sleep(remaining)
            else:
                await asyncio.sleep(60.0)

        # Double-check after sleep
        telemetry = GroqRateTracker.get_telemetry(key_label, model_id)
        if telemetry.tpm_pct >= 90:
            await asyncio.sleep(60.0)

    # ─────────────────────────── PUBLIC API ───────────────────────────

    async def acquire(self, key_label: str, model_id: str, estimated_tokens: int = 1):
        """
        Acquire permission to send a request.
        Blocks until RPM pacing, TPM backpressure, and concurrency limits allow it.
        """
        sem = self._get_semaphore(key_label, model_id)
        await sem.acquire()

        try:
            await self._wait_for_rpm(key_label, model_id)
            await self._wait_for_tpm(key_label, model_id, estimated_tokens)
        except Exception:
            sem.release()
            raise

    def release(self, key_label: str, model_id: str):
        """Release the semaphore slot after the request completes."""
        k = self._key(key_label, model_id)
        if k in self._semaphores:
            try:
                self._semaphores[k].release()
            except ValueError:
                # Semaphore was already at max value (release without acquire)
                pass

    @asynccontextmanager
    async def gate(self, key_label: str, model_id: str, estimated_tokens: int = 1):
        """
        Context manager wrapper for acquire/release.

        Example:
            async with GroqPacer.gate("G_I7AT", "llama-3.3-70b-versatile", 1500):
                result = await execute_strike(...)
        """
        await self.acquire(key_label, model_id, estimated_tokens)
        try:
            yield
        finally:
            self.release(key_label, model_id)

    # ─────────────────────────── TELEMETRY ───────────────────────────

    def get_active_count(self, key_label: str, model_id: str) -> int:
        """Return how many requests are currently in-flight for a key-model pair."""
        k = self._key(key_label, model_id)
        sem = self._semaphores.get(k)
        if not sem:
            return 0
        # Semaphore._value starts at N and decrements on acquire.
        # active = N - value
        concurrency = self._concurrency_for_model(model_id)
        return concurrency - sem._value

    def get_pacer_snapshot(self) -> Dict[str, Dict[str, Any]]:
        """Return a snapshot of all active semaphores and their states."""
        snap = {}
        for k, sem in self._semaphores.items():
            key_label, model_id = k.split(":", 1)
            concurrency = self._concurrency_for_model(model_id)
            snap[k] = {
                "key_label": key_label,
                "model_id": model_id,
                "concurrency_limit": concurrency,
                "active_requests": concurrency - sem._value,
                "waiting": sem._waiters is not None and len(sem._waiters) or 0,
            }
        return snap


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON INSTANCE
# ═══════════════════════════════════════════════════════════════════════════════

GroqPacer = GlobalPacer()
