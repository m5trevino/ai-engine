"""
OpenAI-compatible API surface for Peacock Engine.
Allows OpenClaw and other standard clients to consume the engine.
"""

import time
import json
import uuid
import os
from typing import List, Optional, Literal, Union, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from app.core.striker import execute_strike, execute_streaming_strike
from app.config import MODEL_REGISTRY
from app.utils.formatter import CLIFormatter
from app.core.concurrency import openrouter_rate_limiter
from app.core.pea_trace import (
    TraceRecorder,
    current_trace,
    finalize,
    finalize_error,
    make_traced_client,
    valid_session_name,
)

router = APIRouter()


class OpenAIMessage(BaseModel):
    role: Literal["system", "user", "assistant", "tool", "function"]
    content: Union[str, List[dict], None] = None
    name: Optional[str] = None
    tool_calls: Optional[List[dict]] = None
    tool_call_id: Optional[str] = None


class OpenAIChatRequest(BaseModel):
    model: str
    messages: List[OpenAIMessage]
    stream: bool = False
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    stop: Optional[List[str]] = Field(default=None)
    tools: Optional[List[dict]] = Field(default=None)
    tool_choice: Optional[Union[str, dict]] = Field(default=None)
    response_format: Optional[dict] = Field(default=None)
    extra_body: Optional[dict] = Field(default=None)
    trace: bool = False
    pea_session: Optional[str] = Field(default=None, max_length=128)


class OpenAIUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


def _extract_content_text(content: Union[str, List[dict], None]) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for part in content:
            if isinstance(part, dict):
                texts.append(part.get("text", ""))
        return "".join(texts)
    return ""


def _messages_to_prompt(messages: List[OpenAIMessage]) -> str:
    """Flatten OpenAI message list into a single prompt string."""
    parts = []
    for m in messages:
        content = _extract_content_text(m.content)
        if m.role == "system":
            parts.append(f"[SYSTEM]\n{content}")
        elif m.role == "user":
            parts.append(f"[USER]\n{content}")
        elif m.role == "assistant":
            parts.append(f"[ASSISTANT]\n{content}")
        elif m.role == "tool":
            parts.append(f"[TOOL RESULT ({m.tool_call_id or m.name or 'unknown'})]\n{content}")
        elif m.role == "function":
            parts.append(f"[FUNCTION RESULT ({m.name or 'unknown'})]\n{content}")
    return "\n\n".join(parts)


def _generate_id() -> str:
    return f"chatcmpl-{uuid.uuid4().hex[:12]}"


def _sse_event(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.get("/models")
async def openai_models():
    """List models in OpenAI-compatible format."""
    now = int(time.time())
    data = []
    for m in MODEL_REGISTRY:
        if m.status != "frozen" and m.status != "deprecated":
            data.append({
                "id": m.id,
                "object": "model",
                "created": now,
                "owned_by": m.gateway
            })
    return {"object": "list", "data": data}


def _get_gateway_base_url(gateway: str, model_id: str) -> str:
    """Resolve the base URL for a gateway."""
    model_cfg = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if model_cfg and model_cfg.base_url:
        return model_cfg.base_url
    defaults = {
        "groq": "https://api.groq.com/openai/v1",
        "google": "https://generativelanguage.googleapis.com/v1beta/openai",
        "opencode-go": "https://opencode.ai/zen/go/v1",
        "deepseek": "https://api.deepseek.com/v1",
        "mistral": "https://api.mistral.ai/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "hetzner": "https://inference.hetzner.com/api/v1",
        "merge": "https://merge-api.xkiro.ai/v1",
        "novita": "https://api.novita.ai/openai",
        "xkiro": "https://api.xkiro.com/v1",
        "agnes": "https://apihub.agnes-ai.com/v1",
        "aion": "https://api.aionlabs.ai/v1",
        "bazaarlink": "https://api.bazaarlink.ai/v1",
        "cloudflare": "https://api.cloudflare.com/client/v4/accounts/8a695a9e9379bbbbc57a708e3e5a7194/ai/run",
        "explabs": "https://api.experientiallabs.ai/v1",
        # freshner-managed gateways
        "ollama": "https://ollama.com/v1",
        "merge": "https://api-gateway.merge.dev/v1",
        "clod": "https://api.clod.io/v1",
        "cerebras": "https://api.cerebras.ai/v1",
        "sailresearch": "https://api.sailresearch.com/v1",
        "router9": "https://api.router9.com/v1",
        "septorlabs": "https://api.septorlabs.com/v1",
        "airforce": "https://api.airforce/v1",
        "deepinfra": "https://api.deepinfra.com/v1/openai",
    }
    return defaults.get(gateway, "")


def _get_gateway_key(gateway: str) -> str:
    """Get the first available API key for a gateway from the key pools."""
    from app.core.key_manager import (
        GroqPool, GooglePool, DeepSeekPool, MistralPool,
        OllamaPool, OpencodeGoPool,  # removed: OllamaPool
        ArliPool,  # removed: ArliPool
        OpenrouterPool, HetznerPool, MergePool, AgnesPool, AionPool, BazaarlinkPool,
        CloudflarePool, NovitaPool, ExplabsPool, XkiroPool,
        ClodPool, CerebrasPool, SailResearchPool, Router9Pool,
        SeptorLabsPool, AirforcePool, DeepinfraPool,
    )
    pools = {
        "groq": GroqPool,
        "google": GooglePool,
        "deepseek": DeepSeekPool,
        "mistral": MistralPool,
        "opencode-go": OpencodeGoPool,
        "openrouter": OpenrouterPool,
        "ollama": OllamaPool,
        "hetzner": HetznerPool,
        "merge": MergePool,
        "novita": NovitaPool,
        "xkiro": XkiroPool,
        "agnes": AgnesPool,
        "aion": AionPool,
        "bazaarlink": BazaarlinkPool,
        "cloudflare": CloudflarePool,
        "explabs": ExplabsPool,
        "clod": ClodPool,
        "cerebras": CerebrasPool,
        "sailresearch": SailResearchPool,
        "router9": Router9Pool,
        "septorlabs": SeptorLabsPool,
        "airforce": AirforcePool,
        "deepinfra": DeepinfraPool,
    }
    pool = pools.get(gateway)
    if pool and pool.deck:
        # Find first non-cooldown key
        for asset in pool.deck:
            if not asset.on_cooldown:
                return asset.key
        # All on cooldown, return first anyway
        return pool.deck[0].key
    return ""


def _resolve_provider_model_id(gateway: str, model_id: str) -> str:
    """Map registry model ID to the actual provider model ID.

    OpenCode Go registry IDs now match provider model IDs directly.
    Ollama Cloud registry IDs carry a ``:cloud`` or ``-cloud`` suffix that
    the Ollama API does not recognise — strip it.
    """
    if gateway == "opencode-go":
        if model_id.endswith("-go"):
            return model_id[:-3]
    if gateway == "ollama":
        for suffix in (":cloud", "-cloud"):
            if model_id.endswith(suffix) and len(model_id) > len(suffix):
                return model_id[: -len(suffix)]
    return model_id


async def _execute_merge_request(
    model_id: str,
    messages: list,
    temperature: float,
    max_tokens: Optional[int],
    top_p: Optional[float],
) -> dict:
    """Make a raw HTTP request to the Merge.dev Responses API and convert to OpenAI format."""
    import httpx
    from app.core.key_manager import MergePool

    pool = MergePool
    if not pool or not pool.deck:
        raise HTTPException(status_code=429, detail="No Merge API keys available")
    asset = pool.get_next()
    api_key = asset.key

    # Merge.dev uses the OpenAI Responses API.
    # Input items are {role, content} objects (no "type" discriminator needed
    # for the simplest union variant).  max_output_tokens is the Responses
    # API parameter, not max_tokens.
    merge_input = []
    for m in messages:
        content = m.get("content") if isinstance(m.get("content"), str) else ""
        merge_input.append({
            "role": m.get("role", "user"),
            "content": content
        })

    body = {
        "model": model_id,
        "input": merge_input,
        "stream": False,
    }
    if temperature is not None:
        body["temperature"] = temperature
    if max_tokens:
        body["max_output_tokens"] = max_tokens
    if top_p is not None:
        body["top_p"] = top_p

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with make_traced_client(timeout=300) as client:
        resp = await client.post("https://api-gateway.merge.dev/v1/responses", headers=headers, json=body)
        if resp.status_code != 200:
            error_text = resp.text[:500]
            raise HTTPException(status_code=resp.status_code, detail=f"Merge API error ({resp.status_code}): {error_text}")
        data = resp.json()

    # Convert Merge response to OpenAI chat completion format
    output_text = ""
    for item in data.get("output", []):
        if item.get("type") == "message" and item.get("role") == "assistant":
            for part in item.get("content", []):
                if part.get("type") == "text":
                    output_text += part.get("text", "")

    usage = data.get("usage", {})
    return {
        "id": data.get("id", _generate_id()),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_id,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": output_text},
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    }


async def _execute_tool_request_raw(
    gateway: str,
    model_id: str,
    messages: list,
    tools: list,
    tool_choice: Any,
    temperature: float,
    max_tokens: Optional[int],
    top_p: Optional[float],
    stop: Optional[List[str]],
    response_format: Optional[dict] = None,
    extra_body: Optional[dict] = None,
) -> dict:
    """Make a raw HTTP request to the provider's chat completions endpoint with tools."""
    import httpx

    base_url = _get_gateway_base_url(gateway, model_id)
    api_key = _get_gateway_key(gateway)
    provider_model = _resolve_provider_model_id(gateway, model_id)

    if not base_url:
        raise HTTPException(status_code=400, detail=f"No base URL for gateway '{gateway}'")
    if not api_key:
        raise HTTPException(status_code=429, detail=f"No API keys available for gateway '{gateway}'")

    # Build the request body in OpenAI format
    body = {
        "model": provider_model,
        "messages": messages,
        "temperature": temperature,
        "stream": False,
    }
    if max_tokens:
        body["max_tokens"] = max_tokens
    else:
        # Use per-model max_completion_tokens from the registry
        from app.config import MODEL_REGISTRY
        model_cfg = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
        if model_cfg and model_cfg.max_completion_tokens:
            body["max_tokens"] = model_cfg.max_completion_tokens

    # Groq OTPM cap: if max_tokens exceeds the per-model OTPM limit, Groq
    # rejects with 429 "Request too large" before generating. Cap it.
    # NOTE: GPT-OSS models are reasoning models. A 1000-token cap causes
    # "exceeded before any response" failures due to internal reasoning tokens.
    # Use 4096 to give reasoning models room while still respecting Groq limits.
    if gateway == "groq" and "max_tokens" in body:
        _GROQ_OTPM_LIMITS = {
            "openai/gpt-oss-120b": 4096,
            "openai/gpt-oss-20b": 4096,
            "openai/gpt-oss-safeguard-20b": 4096,
            "meta-llama/llama-prompt-guard-2-86m": 512,
            "meta-llama/llama-prompt-guard-2-22m": 512,
        }
        _otpm_limit = _GROQ_OTPM_LIMITS.get(model_id)
        if _otpm_limit and body["max_tokens"] > _otpm_limit:
            body["max_tokens"] = _otpm_limit
    if top_p is not None:
        body["top_p"] = top_p
    if stop:
        body["stop"] = stop
    if tools:
        body["tools"] = tools
        body["tool_choice"] = tool_choice or "auto"
    # Pass through response_format for structured outputs (json_schema / json_object)
    if response_format:
        body["response_format"] = response_format
    # Pass through extra_body for provider-specific params (min_p, top_k, repetition_penalty)
    if extra_body:
        body.update(extra_body)

    # Cloudflare Workers AI uses a non-OpenAI endpoint path
    if gateway == "cloudflare":
        url = f"{base_url.rstrip('/')}/{provider_model}"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # Cloudflare expects messages directly under the 'messages' key,
        # not the full OpenAI chat completions body. Keep minimal params.
        cf_body = {
            "messages": messages,
        }
        if max_tokens:
            cf_body["max_tokens"] = max_tokens
        if temperature is not None:
            cf_body["temperature"] = temperature
        if top_p is not None:
            cf_body["top_p"] = top_p
        if tools:
            cf_body["tools"] = tools
            cf_body["tool_choice"] = tool_choice or "auto"
        async with make_traced_client(timeout=300) as client:
            resp = await client.post(url, headers=headers, json=cf_body)
            if resp.status_code != 200:
                error_text = resp.text[:500]
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"{gateway} API error ({resp.status_code}): {error_text}"
                )
            cf_data = resp.json()
            # Cloudflare returns { result: { response: "..." } }
            result_text = cf_data
            if isinstance(cf_data, dict) and "result" in cf_data:
                result_text = cf_data["result"]
            text_out = ""
            if isinstance(result_text, str):
                text_out = result_text
            elif isinstance(result_text, dict):
                text_out = result_text.get("response", "")
                if not text_out:
                    text_out = json.dumps(result_text)
            return {
                "id": _generate_id(),
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_id,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": text_out},
                        "finish_reason": "stop"
                    }
                ],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }

    # Ollama Cloud uses the OpenAI Responses API (/v1/responses),
    # not the Chat Completions API (/v1/chat/completions).
    # Body shape: { model, input: [{role, content}], stream }
    # Response shape: { id, object, output: [{role, content, type}], usage }
    if gateway == "ollama" and provider_model.endswith(
        (":cloud", "-cloud")
    ):
        resp_url = f"{base_url.rstrip('/')}/responses"
        resp_headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        # Build input array from messages
        resp_body = {
            "model": provider_model,
            "input": [
                {
                    "role": m.get("role", "user"),
                    "content": m.get("content", ""),
                }
                for m in messages
            ],
            "stream": False,
        }
        if temperature is not None:
            resp_body["temperature"] = temperature
        if max_tokens:
            resp_body["max_output_tokens"] = max_tokens

        async with make_traced_client(timeout=300) as client:
            resp = await client.post(resp_url, headers=resp_headers, json=resp_body)
            if resp.status_code != 200:
                error_text = resp.text[:500]
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"{gateway} API error ({resp.status_code}): {error_text}",
                )
            resp_data = resp.json()
            # Extract text from { output: [{ type: "message", role: "assistant", content: { type: "text", text: "..." } }] }
            output_text = ""
            for item in resp_data.get("output", []):
                if item.get("type") == "message" and item.get("role") == "assistant":
                    for part in item.get("content", []):
                        if part.get("type") == "text":
                            output_text += part.get("text", "")
            usage = resp_data.get("usage", {})
            return {
                "id": resp_data.get("id", _generate_id()),
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model_id,
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": output_text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            }

    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    async with make_traced_client(timeout=300) as client:
        resp = await client.post(url, headers=headers, json=body)

        if resp.status_code != 200:
            error_text = resp.text[:500]
            raise HTTPException(
                status_code=resp.status_code,
                detail=f"{gateway} API error ({resp.status_code}): {error_text}"
            )

        return resp.json()


@router.post("/chat/completions")
async def openai_chat_completions(request: OpenAIChatRequest):
    """OpenAI-compatible chat completions endpoint."""
    want_trace = bool(request.trace or request.pea_session)
    if request.pea_session and not valid_session_name(request.pea_session):
        raise HTTPException(status_code=400, detail="invalid pea_session")
    if request.stream and want_trace:
        raise HTTPException(
            status_code=400,
            detail="trace/pea_session is not supported with stream=true",
        )

    recorder = None
    token = None
    if want_trace:
        recorder = TraceRecorder(request.model_dump(exclude_none=True))
        recorder.engine_path = "/v1/chat/completions"
        token = current_trace.set(recorder)

    try:
        return await _openai_chat_completions_impl(request, recorder)
    except HTTPException as exc:
        if recorder is not None:
            meta = {"model": request.model}
            cfg = next((m for m in MODEL_REGISTRY if m.id == request.model), None)
            if cfg:
                meta["gateway"] = cfg.gateway
            meta["duration_ms"] = round((time.time() - recorder.started_at.timestamp()) * 1000)
            out = finalize_error(
                exc.status_code, exc.detail, recorder,
                trace_enabled=request.trace, session=request.pea_session, meta=meta,
            )
            if request.trace or request.pea_session:
                return JSONResponse(status_code=exc.status_code, content=out)
        raise
    except Exception as exc:
        if recorder is not None:
            meta = {"model": request.model}
            cfg = next((m for m in MODEL_REGISTRY if m.id == request.model), None)
            if cfg:
                meta["gateway"] = cfg.gateway
            meta["duration_ms"] = round((time.time() - recorder.started_at.timestamp()) * 1000)
            out = finalize_error(
                500, str(exc), recorder,
                trace_enabled=request.trace, session=request.pea_session, meta=meta,
            )
            if request.trace or request.pea_session:
                return JSONResponse(status_code=500, content=out)
        raise
    finally:
        if token is not None:
            current_trace.reset(token)


async def _openai_chat_completions_impl(request: OpenAIChatRequest, recorder):
    started = time.time()
    # --- OpenRouter rate limiting: 5 requests per 15 seconds ---
    model_config = next((m for m in MODEL_REGISTRY if m.id == request.model), None)
    if model_config and model_config.gateway == "openrouter":
        await openrouter_rate_limiter.acquire()
    # ----------------------------------------------------------
    if not model_config:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{request.model}'"
        )

    # If tools are provided, use raw HTTP passthrough to preserve tool calling
    if request.tools:
        # Convert messages to plain dicts for JSON serialization
        raw_messages = []
        for m in request.messages:
            msg = {"role": m.role}
            if m.content is not None:
                if isinstance(m.content, list):
                    msg["content"] = m.content
                else:
                    msg["content"] = m.content
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            if m.name:
                msg["name"] = m.name
            raw_messages.append(msg)

        result = await _execute_tool_request_raw(
            gateway=model_config.gateway,
            model_id=request.model,
            messages=raw_messages,
            tools=request.tools,
            tool_choice=request.tool_choice,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            stop=request.stop,
            response_format=request.response_format,
            extra_body=request.extra_body,
        )
        return finalize(
            result, recorder,
            trace_enabled=request.trace,
            session=request.pea_session,
            meta={"gateway": model_config.gateway, "model": request.model},
        )

    # Merge.dev uses the OpenAI Responses API, not chat completions.
    if model_config.gateway == "merge":
        raw_messages = []
        for m in request.messages:
            msg = {"role": m.role}
            if m.content is not None:
                if isinstance(m.content, list):
                    msg["content"] = m.content
                else:
                    msg["content"] = m.content
            raw_messages.append(msg)
        merge_result = await _execute_merge_request(
            model_id=request.model,
            messages=raw_messages,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
        )
        return finalize(
            merge_result, recorder,
            trace_enabled=request.trace,
            session=request.pea_session,
            meta={"gateway": model_config.gateway, "model": request.model},
        )

    # No tools — use the standard pydantic_ai path
    prompt = _messages_to_prompt(request.messages)
    gen_params = {
        "temperature": request.temperature,
        "max_tokens": request.max_tokens,
        "top_p": request.top_p,
        "stop_sequences": request.stop,
    }

    if request.stream:
        async def stream_generator():
            completion_id = _generate_id()
            created = int(time.time())

            # Emit role delta
            yield _sse_event({
                "id": completion_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request.model,
                "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}]
            })

            full_content = ""
            try:
                async for chunk in execute_streaming_strike(
                    gateway=model_config.gateway,
                    model_id=request.model,
                    prompt=prompt,
                    is_manual=False,
                    **gen_params
                ):
                    if "content" in chunk:
                        content = chunk["content"]
                        full_content += content
                        yield _sse_event({
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": request.model,
                            "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}]
                        })
                    elif "error" in chunk:
                        yield _sse_event({
                            "id": completion_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": request.model,
                            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                        })
                        yield "data: [DONE]\n\n"
                        return

                yield _sse_event({
                    "id": completion_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request.model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                })
                yield "data: [DONE]\n\n"
            except Exception as e:
                CLIFormatter.error(f"OpenAI stream error: {e}")
                yield _sse_event({"error": {"message": str(e), "type": "internal_error"}})

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    # Non-streaming
    try:
        result = await execute_strike(
            gateway=model_config.gateway,
            model_id=request.model,
            prompt=prompt,
            is_manual=False,
            **gen_params
        )

        content = result.get("content", "")
        usage = result.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})

        payload = {
            "id": _generate_id(),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop"
                }
            ],
            "usage": usage
        }
        return finalize(
            payload, recorder,
            trace_enabled=request.trace,
            session=request.pea_session,
            meta={
                "gateway": model_config.gateway,
                "model": request.model,
                "usage": usage,
                "tag": result.get("tag"),
                "duration_ms": round((time.time() - started) * 1000),
            },
        )
    except Exception as e:
        CLIFormatter.error(f"OpenAI compat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
