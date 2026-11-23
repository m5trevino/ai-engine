"""
PEACOCK ENGINE — Tiktoken Counter (Re-export wrapper)

DEPRECATED: Use app.core.tiktoken_counter directly.
This module re-exports the canonical implementation for backward compatibility.
"""

from app.core.tiktoken_counter import (
    count_request_tokens,
    estimate_total_tokens,
    estimate_completion_tokens,
    count_text,
    count_message,
    count_messages,
    count_tools,
    count_request,
    count_prompt,
)

__all__ = [
    "count_request_tokens",
    "estimate_total_tokens",
    "estimate_completion_tokens",
    "count_text",
    "count_message",
    "count_messages",
    "count_tools",
    "count_request",
    "count_prompt",
]
