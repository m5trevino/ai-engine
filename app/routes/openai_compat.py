"""
OpenAI-compatible API surface for Peacock Engine.
Allows OpenClaw and other standard clients to consume the engine.
"""

import time
import json
import uuid
from typing import List, Optional, Literal, Union, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.striker import execute_strike, execute_streaming_strike
from app.config import MODEL_REGISTRY
from app.utils.formatter import CLIFormatter

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


@router.post("/chat/completions")
async def openai_chat_completions(request: OpenAIChatRequest):
    """OpenAI-compatible chat completions endpoint."""
    model_config = next((m for m in MODEL_REGISTRY if m.id == request.model), None)
    if not model_config:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown model '{request.model}'"
        )

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

        return {
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
    except Exception as e:
        CLIFormatter.error(f"OpenAI compat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
