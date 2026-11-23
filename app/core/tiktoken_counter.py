"""
PEACOCK ENGINE — Tiktoken Counter Core (TB-003)
Clean, reliable token counting for Groq models.

Scope:
  • Wrap tiktoken with Groq-aware model mappings
  • Count plain text, chat messages, tool calls, and full request payloads
  • Estimate completion tokens from max_tokens
  • Clean public API: count_request_tokens() + estimate_total_tokens()

Reference:
  • OpenAI token counting cookbook: https://github.com/openai/openai-cookbook
  • Groq uses OpenAI-compatible chat formatting internally
"""

import json
import tiktoken
from typing import Dict, Any, List, Optional, Union


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_ENCODING = "cl100k_base"

# Groq models are not in tiktoken's model registry, so we map them explicitly.
# cl100k_base (GPT-4 / GPT-3.5-Turbo) is the closest approximation for all
# current Groq models (Llama, Qwen, GPT-OSS, etc.).
MODEL_ENCODING_MAP: Dict[str, str] = {
    # Meta Llama
    "llama-3.3-70b-versatile": "cl100k_base",
    "llama-3.1-8b-instant": "cl100k_base",
    "meta-llama/llama-4-scout-17b-16e-instruct": "cl100k_base",
    "meta-llama/llama-prompt-guard-2-22m": "cl100k_base",
    "meta-llama/llama-prompt-guard-2-86m": "cl100k_base",
    # OpenAI OSS on Groq
    "openai/gpt-oss-120b": "cl100k_base",
    "openai/gpt-oss-20b": "cl100k_base",
    "openai/gpt-oss-safeguard-20b": "cl100k_base",
    # Qwen
    "qwen/qwen3-32b": "cl100k_base",
    # Groq native
    "groq/compound": "cl100k_base",
    "groq/compound-mini": "cl100k_base",
    # Allam
    "allam-2-7b": "cl100k_base",
    # Canopy Labs
    "canopylabs/orpheus-arabic-saudi": "cl100k_base",
    "canopylabs/orpheus-v1-english": "cl100k_base",
    # Whisper
    "whisper-large-v3": "cl100k_base",
    "whisper-large-v3-turbo": "cl100k_base",
}

# OpenAI-compatible chat format overhead (applied by Groq API internally)
# See: https://github.com/openai/openai-cookbook/blob/main/examples/How_to_count_tokens_with_tiktoken.ipynb
_PER_MESSAGE_OVERHEAD = 4   # <|im_start|>{role}\n{content}<|im_end|>\n  → 4 fmt tokens
_PER_REQUEST_OVERHEAD = 3   # <|im_start|>assistant\n  (priming)


# ═══════════════════════════════════════════════════════════════════════════════
# INTERNAL
# ═══════════════════════════════════════════════════════════════════════════════

def _get_encoding(model_id: str) -> tiktoken.Encoding:
    """Get tiktoken encoding for a model. Falls back to cl100k_base."""
    encoding_name = MODEL_ENCODING_MAP.get(model_id, DEFAULT_ENCODING)
    try:
        return tiktoken.get_encoding(encoding_name)
    except KeyError:
        return tiktoken.get_encoding(DEFAULT_ENCODING)


def _count_text(text: str, model_id: str) -> int:
    """Count tokens in a plain text string."""
    if not text:
        return 0
    enc = _get_encoding(model_id)
    return len(enc.encode(text))


def _count_message(message: Dict[str, Any], model_id: str) -> int:
    """Count tokens in a single chat message (internal)."""
    enc = _get_encoding(model_id)
    total = _PER_MESSAGE_OVERHEAD

    content = message.get("content")
    if content:
        total += len(enc.encode(str(content)))
    elif content == "":
        pass  # Empty content is common for tool-call messages

    # Tool / function calls
    tool_calls = message.get("tool_calls") or message.get("function_call")
    if tool_calls:
        if isinstance(tool_calls, dict):
            total += len(enc.encode(json.dumps(tool_calls)))
        elif isinstance(tool_calls, list):
            for tc in tool_calls:
                total += len(enc.encode(json.dumps(tc)))

    # Name field (function response naming)
    name = message.get("name")
    if name:
        total += len(enc.encode(str(name)))

    return total


def _count_messages(messages: List[Dict[str, Any]], model_id: str) -> int:
    """Count tokens in a list of chat messages with request overhead."""
    if not messages:
        return 0
    total = sum(_count_message(m, model_id) for m in messages)
    total += _PER_REQUEST_OVERHEAD
    return total


def _count_tools(tools: List[Dict[str, Any]], model_id: str) -> int:
    """Count tokens consumed by tool definitions in the request."""
    if not tools:
        return 0
    enc = _get_encoding(model_id)
    return sum(len(enc.encode(json.dumps(t))) for t in tools)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def count_request_tokens(request_data: Dict[str, Any], model_id: str) -> int:
    """
    Clean public API: count tokens in a complete request dict.

    Handles:
      • { "messages": [...] }
      • { "prompt": "..." }
      • { "messages": [...], "tools": [...] }

    Args:
        request_data: Request payload dict
        model_id: Groq model ID

    Returns:
        Estimated prompt token count
    """
    total = 0
    has_explicit_field = False

    if "messages" in request_data:
        has_explicit_field = True
        total += _count_messages(request_data["messages"], model_id)

    if "prompt" in request_data:
        has_explicit_field = True
        total += _count_text(request_data["prompt"], model_id)

    if "tools" in request_data:
        has_explicit_field = True
        total += _count_tools(request_data["tools"], model_id)

    # Fallback: only if no recognizable fields were present
    if not has_explicit_field:
        total = _count_text(json.dumps(request_data), model_id)

    return total


def estimate_completion_tokens(request_data: Dict[str, Any], default_tokens: int = 100) -> int:
    """
    Estimate completion tokens from the max_tokens parameter.

    Args:
        request_data: Request payload dict
        default_tokens: Fallback if max_tokens is missing or invalid

    Returns:
        Estimated completion token count
    """
    max_tokens = request_data.get("max_tokens", default_tokens)
    if not isinstance(max_tokens, int) or max_tokens <= 0:
        return default_tokens
    return max_tokens


def estimate_total_tokens(
    request_data: Dict[str, Any],
    model_id: str,
    default_completion: int = 100,
) -> Dict[str, int]:
    """
    Clean public API: return prompt + completion + total token estimates.

    Args:
        request_data: Request payload dict
        model_id: Groq model ID
        default_completion: Fallback if max_tokens is missing

    Returns:
        {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
    """
    prompt_tokens = count_request_tokens(request_data, model_id)
    completion_tokens = estimate_completion_tokens(request_data, default_completion)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


# ─────────────────────────── BACKWARD COMPAT ALIASES ───────────────────────────

def count_text(text: str, model_id: str = "llama-3.3-70b-versatile") -> int:
    """Count tokens in plain text."""
    return _count_text(text, model_id)


def count_message(message: Dict[str, Any], model_id: str = "llama-3.3-70b-versatile") -> int:
    """Count tokens in a single chat message."""
    return _count_message(message, model_id)


def count_messages(messages: List[Dict[str, Any]], model_id: str = "llama-3.3-70b-versatile") -> int:
    """Count tokens in a list of chat messages."""
    return _count_messages(messages, model_id)


def count_tools(tools: List[Dict[str, Any]], model_id: str = "llama-3.3-70b-versatile") -> int:
    """Count tokens in tool definitions."""
    return _count_tools(tools, model_id)


def count_request(request_data: Dict[str, Any], model_id: str = "llama-3.3-70b-versatile") -> int:
    """Alias for count_request_tokens."""
    return count_request_tokens(request_data, model_id)


def count_prompt(prompt: str, model_id: str = "llama-3.3-70b-versatile") -> int:
    """Convenience wrapper: count a plain-text prompt as a user message."""
    return _count_messages([{"role": "user", "content": prompt}], model_id)
