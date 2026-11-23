"""
PEACOCK ENGINE — Groq Response Parser (TB-005)
Parses real usage and rate-limit headers from Groq API responses.

Scope:
  • Extract usage object (prompt / completion / total tokens)
  • Extract all x-ratelimit-* headers
  • Parse retry-after and reset time strings
  • Return typed, clean data structures

Reference:
  • Groq Rate Limit Headers: https://console.groq.com/docs/rate-limits
  • Header names are case-insensitive; this parser normalizes to lowercase.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Union


# ─────────────────────────── DATA MODELS ───────────────────────────

@dataclass
class GroqUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class GroqRateLimitHeaders:
    """
    Parsed rate-limit headers from Groq.

    Note per Groq docs:
      • limit-requests / remaining-requests / reset-requests  → ALWAYS RPD
      • limit-tokens / remaining-tokens / reset-tokens        → ALWAYS TPM
    """
    retry_after: Optional[float] = None              # seconds (only on 429)
    limit_requests: Optional[int] = None             # RPD limit
    limit_tokens: Optional[int] = None               # TPM limit
    remaining_requests: Optional[int] = None         # RPD remaining
    remaining_tokens: Optional[int] = None           # TPM remaining
    reset_requests_seconds: Optional[float] = None   # RPD reset window
    reset_tokens_seconds: Optional[float] = None     # TPM reset window

    def to_dict(self) -> Dict[str, Any]:
        return {
            "retry_after": self.retry_after,
            "limit_requests": self.limit_requests,
            "limit_tokens": self.limit_tokens,
            "remaining_requests": self.remaining_requests,
            "remaining_tokens": self.remaining_tokens,
            "reset_requests_seconds": self.reset_requests_seconds,
            "reset_tokens_seconds": self.reset_tokens_seconds,
        }


@dataclass
class GroqResponseMeta:
    """Complete parsed metadata from a Groq response."""
    usage: GroqUsage
    rate_limits: GroqRateLimitHeaders
    model_id: Optional[str] = None
    raw_headers: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "usage": self.usage.to_dict(),
            "rate_limits": self.rate_limits.to_dict(),
            "model_id": self.model_id,
        }


# ─────────────────────────── PARSER ───────────────────────────

class GroqResponseParser:
    """
    Static parser for Groq response bodies and headers.

    Supports:
      • Raw dict headers (from httpx/requests)
      • httpx.Response objects
      • JSON body dicts or raw JSON strings
    """

    # Regex for Groq reset-time strings:  "7.66s", "2m59.56s", "1h30m", "45s"
    _RESET_RE = re.compile(
        r"^(?:(?P<hours>\d+)h)?(?:(?P<minutes>\d+)m)?(?:(?P<seconds>\d+(?:\.\d+)?)s)?$"
    )

    @classmethod
    def parse_reset_time(cls, value: Optional[str]) -> Optional[float]:
        """
        Parse Groq reset time strings into seconds.

        Examples:
          "7.66s"      → 7.66
          "2m59.56s"   → 179.56
          "1h30m"      → 5400.0
          "45s"        → 45.0
        """
        if not value or not isinstance(value, str):
            return None

        value = value.strip().lower()
        match = cls._RESET_RE.match(value)
        if not match:
            # Fallback: try pure float
            try:
                return float(value)
            except ValueError:
                return None

        groups = match.groupdict()
        total = 0.0
        if groups.get("hours"):
            total += float(groups["hours"]) * 3600.0
        if groups.get("minutes"):
            total += float(groups["minutes"]) * 60.0
        if groups.get("seconds"):
            total += float(groups["seconds"])
        return total

    @classmethod
    def _normalize_headers(cls, headers: Union[Dict[str, str], Any]) -> Dict[str, str]:
        """Normalize headers to a plain lowercase dict."""
        # Handle httpx.Response.headers (which is a Headers object with .get() and case-insensitive access)
        if hasattr(headers, "items") and callable(headers.items):
            # Could be dict, httpx.Headers, requests.structures.CaseInsensitiveDict
            return {k.lower(): str(v) for k, v in headers.items()}
        # Fallback: assume dict-like
        return {str(k).lower(): str(v) for k, v in dict(headers).items()}

    @classmethod
    def parse_headers(cls, headers: Union[Dict[str, str], Any]) -> GroqRateLimitHeaders:
        """Extract and parse rate-limit headers."""
        h = cls._normalize_headers(headers)

        def _int(key: str) -> Optional[int]:
            v = h.get(key)
            if v is None:
                return None
            try:
                return int(v)
            except (ValueError, TypeError):
                return None

        def _float(key: str) -> Optional[float]:
            v = h.get(key)
            if v is None:
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        return GroqRateLimitHeaders(
            retry_after=_float("retry-after"),
            limit_requests=_int("x-ratelimit-limit-requests"),
            limit_tokens=_int("x-ratelimit-limit-tokens"),
            remaining_requests=_int("x-ratelimit-remaining-requests"),
            remaining_tokens=_int("x-ratelimit-remaining-tokens"),
            reset_requests_seconds=cls.parse_reset_time(h.get("x-ratelimit-reset-requests")),
            reset_tokens_seconds=cls.parse_reset_time(h.get("x-ratelimit-reset-tokens")),
        )

    @classmethod
    def parse_body(cls, body: Union[Dict[str, Any], str, bytes]) -> GroqUsage:
        """Extract usage from response body JSON."""
        data: Dict[str, Any] = {}

        if isinstance(body, str):
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                return GroqUsage()
        elif isinstance(body, bytes):
            try:
                data = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return GroqUsage()
        elif isinstance(body, dict):
            data = body
        else:
            return GroqUsage()

        usage = data.get("usage") or {}
        if not isinstance(usage, dict):
            return GroqUsage()

        return GroqUsage(
            prompt_tokens=usage.get("prompt_tokens", 0) or 0,
            completion_tokens=usage.get("completion_tokens", 0) or 0,
            total_tokens=usage.get("total_tokens", 0) or 0,
        )

    @classmethod
    def parse(
        cls,
        body: Union[Dict[str, Any], str, bytes],
        headers: Union[Dict[str, str], Any],
        model_id: Optional[str] = None,
    ) -> GroqResponseMeta:
        """
        Full parse of a Groq response.

        Args:
            body: Response body (dict, JSON string, or bytes)
            headers: Response headers (dict or httpx.Headers)
            model_id: Optional model ID for context

        Returns:
            GroqResponseMeta with usage + rate limits
        """
        raw_headers = cls._normalize_headers(headers)
        return GroqResponseMeta(
            usage=cls.parse_body(body),
            rate_limits=cls.parse_headers(headers),
            model_id=model_id,
            raw_headers=raw_headers,
        )

    @classmethod
    def parse_from_httpx(cls, response, model_id: Optional[str] = None) -> GroqResponseMeta:
        """Convenience wrapper for httpx.Response objects."""
        body = response.json() if hasattr(response, "json") else response.text
        return cls.parse(body=body, headers=response.headers, model_id=model_id)


# ─────────────────────────── MODULE SELF-TEST ───────────────────────────

if __name__ == "__main__":
    print("=== GROQ RESPONSE PARSER SELF-TEST ===\n")

    # 1. Reset time parser
    tests = [
        ("7.66s", 7.66),
        ("2m59.56s", 179.56),
        ("1h30m", 5400.0),
        ("45s", 45.0),
        ("3h20m15.5s", 12015.5),
        (None, None),
        ("", None),
    ]
    for inp, expected in tests:
        got = GroqResponseParser.parse_reset_time(inp)
        status = "✅" if got == expected else "❌"
        print(f"{status} parse_reset_time({inp!r}) = {got}  (expected {expected})")

    # 2. Header parsing
    sample_headers = {
        "retry-after": "2",
        "x-ratelimit-limit-requests": "14400",
        "x-ratelimit-limit-tokens": "18000",
        "x-ratelimit-remaining-requests": "14370",
        "x-ratelimit-remaining-tokens": "17997",
        "x-ratelimit-reset-requests": "2m59.56s",
        "x-ratelimit-reset-tokens": "7.66s",
    }
    rl = GroqResponseParser.parse_headers(sample_headers)
    print(f"\n📋 Parsed headers:")
    print(f"   retry_after            = {rl.retry_after} s")
    print(f"   limit_requests (RPD)   = {rl.limit_requests}")
    print(f"   limit_tokens   (TPM)   = {rl.limit_tokens}")
    print(f"   remaining_requests     = {rl.remaining_requests}")
    print(f"   remaining_tokens       = {rl.remaining_tokens}")
    print(f"   reset_requests_seconds = {rl.reset_requests_seconds} s")
    print(f"   reset_tokens_seconds   = {rl.reset_tokens_seconds} s")

    # 3. Body parsing
    sample_body = {
        "id": "chatcmpl-abc123",
        "object": "chat.completion",
        "usage": {
            "prompt_tokens": 123,
            "completion_tokens": 45,
            "total_tokens": 168,
        },
    }
    usage = GroqResponseParser.parse_body(sample_body)
    print(f"\n📋 Parsed usage:")
    print(f"   prompt_tokens     = {usage.prompt_tokens}")
    print(f"   completion_tokens = {usage.completion_tokens}")
    print(f"   total_tokens      = {usage.total_tokens}")

    # 4. Full parse
    meta = GroqResponseParser.parse(sample_body, sample_headers, model_id="llama-3.3-70b-versatile")
    print(f"\n📋 Full meta:")
    print(f"   model_id = {meta.model_id}")
    print(f"   dict     = {json.dumps(meta.to_dict(), indent=2)}")

    print("\n✅ TB-005 self-test complete.")
