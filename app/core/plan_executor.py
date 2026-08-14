"""
PEACOCK ENGINE — Plan Execution Engine (TB-016)
Executes an ExecutionPlan chunk-by-chunk while honoring manual overrides.

Scope:
  • Load a persisted plan (TB-014)
  • For each chunk, determine effective route = manual_override or route
  • Acquire TB-009 GlobalPacer gate per attempt
  • Delegate retries/key rotation to TB-008 RetryHandler
  • Persist chunk/plan status via PlanManager

References:
  • app.core.plan_generator     (TB-011)
  • app.core.plan_scheduler     (TB-013)
  • app.core.plan_manager       (TB-014)
  • app.core.global_pacer       (TB-009)
  • app.core.retry_handler      (TB-008)
  • app.core.striker            (execute_strike fallback)
"""

import os
import time
import asyncio
import httpx
import uuid
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Literal, Optional, AsyncGenerator

from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.gemini import GeminiModel as GoogleModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.google_gla import GoogleGLAProvider as GoogleProvider

from app.config import MODEL_REGISTRY
from app.core.plan_generator import ExecutionPlan, ChunkPlan
from app.core.plan_manager import PlanManager
from app.monitoring.metrics import global_metrics
from app.core.key_manager import GroqPool, KeyAsset
from app.core.rate_limit_tracker import GroqRateTracker
from app.core.global_pacer import GroqPacer
from app.core.retry_handler import GroqRetryHandler, RateLimitError
from app.core.striker import execute_strike
from app.core.history import HistoryStore
from app.utils.logger import HighSignalLogger
from app.utils.formatter import CLIFormatter


# ═══════════════════════════════════════════════════════════════════════════════
# RESULT TYPES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ChunkExecutionResult:
    chunk_id: int
    status: Literal["completed", "failed", "skipped"]
    route: Optional[str] = None
    key_used: Optional[str] = None
    content_preview: Optional[str] = None
    usage: Dict[str, int] = field(default_factory=lambda: {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    cost: float = 0.0
    duration_ms: int = 0
    error: Optional[str] = None


@dataclass
class PlanExecutionResult:
    plan_id: str
    status: Literal["completed", "failed", "partial"]
    chunks: List[ChunkExecutionResult] = field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    duration_ms: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# EXECUTOR
# ═══════════════════════════════════════════════════════════════════════════════

class PlanExecutor:
    """
    Execute an ExecutionPlan chunk-by-chunk with full respect for routing overrides.

    Usage:
        executor = PlanExecutor()
        result = await executor.execute_plan("plan_abc123")
    """

    def __init__(
        self,
        retry_handler: Any = GroqRetryHandler,
        pacer: Any = GroqPacer,
        abort_on_fail: bool = False,
        default_system_prompt: Optional[str] = None,
    ):
        """
        Args:
            retry_handler: TB-008 retry handler (default GroqRetryHandler)
            pacer: TB-009 pacer (default GroqPacer)
            abort_on_fail: If True, stop execution on first chunk failure
            default_system_prompt: Optional system prompt prepended to every chunk
        """
        self.retry_handler = retry_handler
        self.pacer = pacer
        self.abort_on_fail = abort_on_fail
        self.default_system_prompt = default_system_prompt

    @staticmethod
    def _effective_route(chunk: ChunkPlan) -> Literal["direct"]:
        return chunk.manual_override or chunk.route

    @staticmethod
    def _gateway_for_model(model_id: str) -> str:
        cfg = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
        return cfg.gateway if cfg else "groq"

    @staticmethod
    def _build_http_client(route: Literal["direct"], timeout: float = 60.0) -> httpx.AsyncClient:
        """Construct a per-chunk httpx client based on routing decision."""
        tunnel_enabled = os.getenv("PEACOCK_TUNNEL", "false").lower() == "true"
        proxy_enabled = os.getenv("PROXY_ENABLED", "false").lower() == "true"
        proxy_url = os.getenv("PROXY_URL")

        if tunnel_enabled:
            from app.core.striker import TUNNEL_SOCKS
            return httpx.AsyncClient(proxy=TUNNEL_SOCKS, timeout=timeout, trust_env=False)

        return httpx.AsyncClient(timeout=timeout, trust_env=False)

    @staticmethod
    def _calculate_cost(model_id: str, usage: Dict[str, int]) -> float:
        """Approximate cost based on MODEL_REGISTRY pricing."""
        cfg = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
        if not cfg:
            return 0.0
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        input_price = cfg.input_price_1m / 1_000_000
        output_price = cfg.output_price_1m / 1_000_000
        return (prompt_tokens * input_price) + (completion_tokens * output_price)

    # ─────────────────────────── PUBLIC API ───────────────────────────

    async def execute_plan(
        self,
        plan_id: str,
        system_prompt: Optional[str] = None,
        **gen_params,
    ) -> PlanExecutionResult:
        """
        Execute all pending/running chunks in a plan sequentially.

        Skips chunks already marked completed. Persists status after every chunk.
        """
        trace_id = f"exec_{uuid.uuid4().hex[:8]}"
        logger = logging.getLogger("peacock.executor")
        logger.info(f"[trace={trace_id}] Starting plan execution: {plan_id}")

        plan = PlanManager.load(plan_id)
        PlanManager.update_plan_status(plan_id, "running")

        start_time = time.time()
        results: List[ChunkExecutionResult] = []
        total_tokens = 0
        total_cost = 0.0
        any_failed = False

        sys_prompt = system_prompt or self.default_system_prompt

        for chunk in sorted(plan.chunks, key=lambda c: c.chunk_id):
            if chunk.status == "completed":
                results.append(
                    ChunkExecutionResult(
                        chunk_id=chunk.chunk_id,
                        status="skipped",
                        route=self._effective_route(chunk),
                        key_used=chunk.key_label,
                    )
                )
                continue

            PlanManager.update_chunk_status(plan_id, chunk.chunk_id, "running")

            chunk_result = await self._execute_chunk(chunk, sys_prompt, **gen_params)
            results.append(chunk_result)

            if chunk_result.status == "completed":
                PlanManager.update_chunk_status(plan_id, chunk.chunk_id, "completed")
                total_tokens += chunk_result.usage.get("total_tokens", 0)
                total_cost += chunk_result.cost
            else:
                PlanManager.update_chunk_status(
                    plan_id, chunk.chunk_id, "failed", error=chunk_result.error
                )
                any_failed = True
                if self.abort_on_fail:
                    # Mark remaining chunks as aborted in the result only;
                    # do not mutate their persisted status.
                    aborted_ids = {c.chunk_id for c in results}
                    for remaining in sorted(plan.chunks, key=lambda c: c.chunk_id):
                        if remaining.chunk_id not in aborted_ids:
                            results.append(
                                ChunkExecutionResult(
                                    chunk_id=remaining.chunk_id,
                                    status="skipped",
                                    route=self._effective_route(remaining),
                                    key_used=remaining.key_label,
                                    error="aborted due to earlier failure",
                                )
                            )
                    break

        final_status: Literal["completed", "failed", "partial"] = "completed"
        if any_failed:
            final_status = "failed" if self.abort_on_fail else "partial"

        # PlanManager only knows terminal states; "partial" maps to "failed".
        PlanManager.update_plan_status(plan_id, final_status if final_status != "partial" else "failed")
        duration_ms = int((time.time() - start_time) * 1000)

        result = PlanExecutionResult(
            plan_id=plan_id,
            status=final_status,
            chunks=results,
            total_tokens=total_tokens,
            total_cost=round(total_cost, 6),
            duration_ms=duration_ms,
        )
        logger.info(
            f"[trace={trace_id}] Plan {plan_id} complete: status={final_status}, "
            f"tokens={total_tokens}, cost=${total_cost:.4f}, duration={duration_ms}ms"
        )
        global_metrics.record_execution_result(result)

        # Persist execution log entry for Recent Executions view (TB-019)
        proxy_chunks = sum(1 for c in results if c.status == "completed" and c.route == "proxy")
        direct_chunks = sum(1 for c in results if c.status == "completed" and c.route == "direct")
        entry = {
            "executed_at": time.time(),
            "status": final_status,
            "total_tokens": total_tokens,
            "total_cost": round(total_cost, 6),
            "duration_ms": duration_ms,
            "proxy_chunks": proxy_chunks,
            "direct_chunks": direct_chunks,
        }
        plan = PlanManager.load(plan_id)
        plan.execution_log.append(entry)
        PlanManager.save(plan, plan_id=plan_id)

        # Persist to proper audit history (TB-020)
        HistoryStore.record_execution(
            plan_id=plan_id,
            file_path=plan.file_path,
            model_id=plan.model_id,
            result=result,
        )

        return result

    async def execute_plan_stream(
        self,
        plan_id: str,
        system_prompt: Optional[str] = None,
        **gen_params,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streaming variant that yields per-chunk progress events.

        Yields:
            {"type": "chunk_start", "chunk_id": int}
            {"type": "chunk_complete", "chunk_id": int, "result": ChunkExecutionResult}
            {"type": "error", "chunk_id": int, "error": str}
            {"type": "plan_complete", "result": PlanExecutionResult}
        """
        plan = PlanManager.load(plan_id)
        PlanManager.update_plan_status(plan_id, "running")

        start_time = time.time()
        results: List[ChunkExecutionResult] = []
        total_tokens = 0
        total_cost = 0.0
        any_failed = False

        sys_prompt = system_prompt or self.default_system_prompt

        for chunk in sorted(plan.chunks, key=lambda c: c.chunk_id):
            if chunk.status == "completed":
                continue

            yield {"type": "chunk_start", "chunk_id": chunk.chunk_id}
            PlanManager.update_chunk_status(plan_id, chunk.chunk_id, "running")

            chunk_result = await self._execute_chunk(chunk, sys_prompt, **gen_params)
            results.append(chunk_result)

            if chunk_result.status == "completed":
                PlanManager.update_chunk_status(plan_id, chunk.chunk_id, "completed")
                total_tokens += chunk_result.usage.get("total_tokens", 0)
                total_cost += chunk_result.cost
                yield {"type": "chunk_complete", "chunk_id": chunk.chunk_id, "result": chunk_result}
            else:
                PlanManager.update_chunk_status(
                    plan_id, chunk.chunk_id, "failed", error=chunk_result.error
                )
                any_failed = True
                yield {"type": "error", "chunk_id": chunk.chunk_id, "error": chunk_result.error}
                if self.abort_on_fail:
                    break

        final_status: Literal["completed", "failed", "partial"] = "completed"
        if any_failed:
            final_status = "failed" if self.abort_on_fail else "partial"

        PlanManager.update_plan_status(plan_id, final_status if final_status != "partial" else "failed")
        duration_ms = int((time.time() - start_time) * 1000)

        yield {
            "type": "plan_complete",
            "result": PlanExecutionResult(
                plan_id=plan_id,
                status=final_status,
                chunks=results,
                total_tokens=total_tokens,
                total_cost=round(total_cost, 6),
                duration_ms=duration_ms,
            ),
        }

    # ─────────────────────────── INTERNALS ───────────────────────────

    async def _execute_chunk(
        self,
        chunk: ChunkPlan,
        system_prompt: Optional[str],
        **gen_params,
    ) -> ChunkExecutionResult:
        """Execute a single chunk, applying guard → pacing → retry → request."""
        route = self._effective_route(chunk)
        gateway = self._gateway_for_model(chunk.model_id)
        chunk_start = time.time()

        # ── 1. Scheduler pacing (honor planned wait) ──
        if chunk.wait_seconds and chunk.wait_seconds > 0:
            await asyncio.sleep(chunk.wait_seconds)

        # ── 2. Build the prompt ──
        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": chunk.text})

        # ── 3. Non-Groq gateways fall back to existing striker ──
        if gateway != "groq":
            try:
                # striker handles its own proxy config globally; for non-groq we
                # still honor the plan key label by passing key_override if possible
                result = await execute_strike(
                    gateway=gateway,
                    model_id=chunk.model_id,
                    prompt=chunk.text,
                    key_override=None,  # striker will pick from pool
                    **gen_params,
                )
                duration_ms = int((time.time() - chunk_start) * 1000)
                content = str(result.get("content", ""))
                return ChunkExecutionResult(
                    chunk_id=chunk.chunk_id,
                    status="completed",
                    route=route,
                    key_used=result.get("keyUsed"),
                    content_preview=content[:200],
                    usage=result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
                    cost=result.get("cost", 0.0),
                    duration_ms=duration_ms,
                )
            except Exception as e:
                duration_ms = int((time.time() - chunk_start) * 1000)
                return ChunkExecutionResult(
                    chunk_id=chunk.chunk_id,
                    status="failed",
                    route=route,
                    error=str(e),
                    duration_ms=duration_ms,
                )

        # ── 4. Groq: Retry-wrapped strike with pacer gating ──
        try:
            result = await self.retry_handler.execute(
                self._groq_strike_once,
                model_id=chunk.model_id,
                estimated_tokens=chunk.token_count,
                key_label=key_label,
                route=route,
                messages=messages,
                **gen_params,
            )
            duration_ms = int((time.time() - chunk_start) * 1000)
            return ChunkExecutionResult(
                chunk_id=chunk.chunk_id,
                status="completed",
                route=route,
                key_used=result.get("key_used"),
                content_preview=str(result.get("content", ""))[:200],
                usage=result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
                cost=result.get("cost", 0.0),
                duration_ms=duration_ms,
            )
        except RateLimitError as rle:
            duration_ms = int((time.time() - chunk_start) * 1000)
            return ChunkExecutionResult(
                chunk_id=chunk.chunk_id,
                status="failed",
                route=route,
                key_used=rle.key_label,
                error=f"Rate limit exhausted after retries: {rle.message}",
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - chunk_start) * 1000)
            return ChunkExecutionResult(
                chunk_id=chunk.chunk_id,
                status="failed",
                route=route,
                error=str(e),
                duration_ms=duration_ms,
            )

    async def _groq_strike_once(
        self,
        *,
        key_label: str,
        model_id: str,
        route: Literal["direct", "proxy"],
        messages: List[Dict[str, str]],
        **gen_params,
    ) -> Dict[str, Any]:
        """
        Single-shot Groq strike.

        Must raise RateLimitError on 429 so the retry handler can rotate keys.
        Wrapped in GroqPacer.gate() so each attempt re-acquires pacing.
        """
        asset = next((a for a in GroqPool.deck if a.account == key_label), None)
        if not asset:
            raise Exception(f"Key {key_label} not found in GroqPool")

        client = self._build_http_client(route)
        try:
            async with self.pacer.gate(key_label, model_id, estimated_tokens=gen_params.get("max_tokens", 1024)):
                await GroqRateTracker.begin_request(key_label, model_id)

                provider = GroqProvider(api_key=asset.key, http_client=client)
                model = GroqModel(model_id, provider=provider)
                agent = Agent(model, output_type=str)

                model_settings = {
                    "temperature": gen_params.get("temperature", 0.3),
                    "max_tokens": gen_params.get("max_tokens", 1024),
                    "top_p": gen_params.get("top_p"),
                    "top_k": gen_params.get("top_k"),
                    "seed": gen_params.get("seed"),
                    "presence_penalty": gen_params.get("presence_penalty"),
                    "frequency_penalty": gen_params.get("frequency_penalty"),
                }
                model_settings = {k: v for k, v in model_settings.items() if v is not None}

                prompt = self._messages_to_prompt(messages)
                result = await agent.run(prompt, model_settings=model_settings)
                content = result.data

                usage_obj = result.usage()
                usage = {
                    "prompt_tokens": usage_obj.request_tokens or 0,
                    "completion_tokens": usage_obj.response_tokens or 0,
                    "total_tokens": usage_obj.total_tokens or 0,
                }

                await GroqRateTracker.consume(key_label, model_id, usage["total_tokens"])
                await GroqRateTracker.end_request(key_label, model_id)

                cost = self._calculate_cost(model_id, usage)
                tag = HighSignalLogger.log_strike(
                    "groq", model_id, prompt, str(content), usage,
                    model_settings.get("temperature", 0.3), cost, is_success=True
                )
                CLIFormatter.strike_success(
                    "groq", key_label, model_id, usage["prompt_tokens"],
                    usage["completion_tokens"], time.time() - 0, "", temp=model_settings.get("temperature", 0.3),
                    tag=tag, cost=cost,
                    meter=str(GroqRateTracker.get_telemetry(key_label, model_id)),
                )

                return {
                    "content": content,
                    "key_used": key_label,
                    "usage": usage,
                    "cost": cost,
                    "tag": tag,
                }

        except Exception as e:
            await GroqRateTracker.end_request(key_label, model_id)
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str or "too many requests" in error_str:
                raise RateLimitError(str(e), key_label=key_label, model_id=model_id) from e
            raise
        finally:
            await client.aclose()

    @staticmethod
    def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
        """Flatten messages into a single prompt string for pydantic-ai Agent(str)."""
        parts = []
        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                parts.append(f"[SYSTEM]: {content}")
            else:
                parts.append(content)
        return "\n\n".join(parts)


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE
# ═══════════════════════════════════════════════════════════════════════════════

async def execute_plan(
    plan_id: str,
    system_prompt: Optional[str] = None,
    abort_on_fail: bool = False,
    **gen_params,
) -> PlanExecutionResult:
    """One-shot plan execution."""
    return await PlanExecutor(abort_on_fail=abort_on_fail).execute_plan(
        plan_id, system_prompt=system_prompt, **gen_params
    )
