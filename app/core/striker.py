"""
PEACOCK ENGINE - Striker Module
Handles AI model execution with high-signal logging and usage tracking.
"""

import os
import re
import json
import time
import httpx
import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, create_model
from pydantic_ai import Agent
from pydantic_ai.models.groq import GroqModel
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.gemini import GeminiModel as GoogleModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.google_gla import GoogleGLAProvider as GoogleProvider
try:
    from pydantic_ai.providers.anthropic import AnthropicProvider
    from pydantic_ai.models.anthropic import AnthropicModel
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
from app.core.key_manager import KeyAsset, KeyPool, GroqPool, OllamaPool, OpencodeGoPool, OpencodeZenPool, OpenrouterPool, HetznerPool, get_pool, GooglePool, DeepSeekPool, MistralPool, ZaiPool, ZaiCodingPool
from app.core.rate_limit_tracker import GroqRateTracker
from app.core.provider_error_handler import handle_provider_exception
from app.utils.formatter import CLIFormatter, Colors
from app.utils.logger import HighSignalLogger
from app.config import MODEL_REGISTRY
from app.core.config_store import config_store

# Import unified token counter
from app.utils.token_counter import count_tokens

# Import global pacer for concurrency control
from app.core.global_pacer import GroqPacer

# Proxy / Tunnel Setup
tunnel_enabled = os.getenv("PEACOCK_TUNNEL", "false").lower() == "true"
proxy_url = os.getenv("PROXY_URL")
proxy_enabled = os.getenv("PROXY_ENABLED", "false").lower() == "true"

TUNNEL_SOCKS = "socks5://127.0.0.1:1081"
direct_client = httpx.AsyncClient(timeout=60.0, trust_env=False)
tunnel_client = httpx.AsyncClient(proxy=TUNNEL_SOCKS, timeout=100.0, trust_env=False) if tunnel_enabled else None
proxy_client = httpx.AsyncClient(proxy=proxy_url, timeout=60.0, trust_env=False) if proxy_enabled and proxy_url else None

if tunnel_enabled:
    http_client = tunnel_client
elif proxy_enabled and proxy_url:
    http_client = proxy_client
else:
    http_client = direct_client

# --- STRUCTURED OUTPUT MODELS ---
class EagleFile(BaseModel):
    path: str
    skeleton: str
    directives: str

class EagleScaffold(BaseModel):
    project: str
    files: List[EagleFile]

# --------------------------------

class ThrottleController:
    """Manages proactive throttling based on the active Performance Mode."""
    last_strike_time = {} # {gateway: timestamp}

    @staticmethod
    async def wait_if_needed(gateway: str, model_id: str):
        from app.config import PERFORMANCE_MODES
        
        mode_key = os.getenv("PEACOCK_PERF_MODE", "balanced").lower()
        mode_cfg = PERFORMANCE_MODES.get(mode_key, PERFORMANCE_MODES["balanced"])
        
        model_cfg = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
        if not model_cfg or not model_cfg.rpm:
            return False

        # Calculate pool size for collective RPM
        pool_size = 1
        if gateway == "groq": pool_size = len(GroqPool.deck)
        elif gateway == "google": pool_size = len(GooglePool.deck)

        # COLLECTIVE RPM limit
        collective_rpm = model_cfg.rpm * pool_size
        
        # Calculate minimum interval between strikes using the mode multiplier
        # Stealth (Black Key) = 3.0x safer/slower
        # Balanced (Blue Key) = 1.15x buffer
        # Apex (Red Key) = 1.02x (Absolute Limit)
        min_interval = (60.0 / collective_rpm) * mode_cfg["multiplier"]
        
        now = time.time()
        last_time = ThrottleController.last_strike_time.get(gateway, 0)
        elapsed = now - last_time
        
        if elapsed < min_interval:
            wait_time = min_interval - elapsed
            await asyncio.sleep(wait_time)
            return True
            
        ThrottleController.last_strike_time[gateway] = time.time()
        return False

def count_tokens_for_strike(gateway: str, model_id: str, prompt: str) -> int:
    """
    Count tokens for a strike using the unified counter.
    Returns estimated token count.
    """
    try:
        provider = "gemini" if gateway == "google" else "groq"
        return count_tokens(prompt, provider=provider, model=model_id)
    except Exception as e:
        # Fallback: rough approximation
        if os.getenv("PEACOCK_VERBOSE") == "true":
            print(f"[!] Token counting error: {e}")
        return len(prompt.split()) * 1.3


class RateLimitMeter:
    """Real-time tracking of RPM and TPM to prevent redlining."""
    # Class-level storage for simplicity
    stats = {} # {gateway: {rpm: 0, tpm: 0, last_reset: timestamp}}

    @staticmethod
    def update(gateway: str, tokens: int):
        now = time.time()
        if gateway not in RateLimitMeter.stats:
            RateLimitMeter.stats[gateway] = {"count": 0, "tokens": 0, "start": now}
        
        # Reset every 60 seconds
        if now - RateLimitMeter.stats[gateway]["start"] > 60:
            RateLimitMeter.stats[gateway] = {"count": 1, "tokens": tokens, "start": now}
        else:
            RateLimitMeter.stats[gateway]["count"] += 1
            RateLimitMeter.stats[gateway]["tokens"] += tokens

    @staticmethod
    def get_meter(gateway: str, model_id: str) -> str:
        from app.config import PERFORMANCE_MODES
        model_cfg = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
        if not model_cfg or gateway not in RateLimitMeter.stats:
            return "Meter: [Initializing...]"
        
        # Performance Mode
        mode_key = os.getenv("PEACOCK_PERF_MODE", "balanced").lower()
        mode_cfg = PERFORMANCE_MODES.get(mode_key, PERFORMANCE_MODES["balanced"])
        mode_display = f"{mode_cfg['color']}Key: {mode_key.upper()}{Colors.RESET}"

        # Resolve pool size for total capacity
        pool_size = 1
        if gateway == "groq": pool_size = len(GroqPool.deck)
        elif gateway == "google": pool_size = len(GooglePool.deck)
        
        current = RateLimitMeter.stats[gateway]
        rpm_limit = (model_cfg.rpm or 1) * pool_size
        tpm_limit = (model_cfg.tpm or 1) * pool_size
        
        rpm_pct = min(int(current["count"] / rpm_limit * 100), 100)
        tpm_pct = min(int(current["tokens"] / tpm_limit * 100), 100)
        
        # Determine color
        color = Colors.GREEN
        if rpm_pct > 85 or tpm_pct > 85: color = Colors.RED
        elif rpm_pct > 60 or tpm_pct > 60: color = Colors.YELLOW
        
        return f"{mode_display} | {color}Meter: [RPM: {rpm_pct}% | TPM: {tpm_pct}% | Pool: {pool_size}]{Colors.RESET}"

def _build_dynamic_schema(schema_def: dict) -> type[BaseModel]:
    """Build a Pydantic model from a schema definition."""
    fields = {}
    type_map = {
        'str': str,
        'string': str,
        'int': int,
        'integer': int,
        'float': float,
        'bool': bool,
        'boolean': bool,
        'list': List,
        'List': List,
    }
    
    for field in schema_def.get('fields', []):
        field_name = field['name']
        field_type_str = field['type']
        
        if '[' in field_type_str:
            base_type = field_type_str.split('[')[0]
            inner_type = field_type_str[field_type_str.find('[')+1:field_type_str.find(']')]
            field_type = List[type_map.get(inner_type, str)]
        else:
            field_type = type_map.get(field_type_str, str)
        
        fields[field_name] = (field_type, ...)
    
    return create_model(schema_def.get('name', 'DynamicModel'), **fields)
def _calculate_cost(model_id: str, usage: dict) -> float:
    """Calculate the cost of a strike based on model rates."""
    from app.config import MODEL_REGISTRY
    model_cfg = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if not model_cfg:
        return 0.0
    
    in_tokens = usage.get("prompt_tokens", 0)
    out_tokens = usage.get("completion_tokens", 0)
    
    cost = (in_tokens / 1_000_000 * model_cfg.input_price_1m) + \
           (out_tokens / 1_000_000 * model_cfg.output_price_1m)
    return round(cost, 6)


def _inject_file_context(prompt: str, files: List[str]) -> str:
    """Inject local file contents into the prompt."""
    if not files:
        return prompt
    
    from pathlib import Path
    context = "\n\n=== FILE CONTEXT VAULT ===\n"
    for file_path in files:
        try:
            path = Path(file_path).expanduser()
            if path.exists() and path.is_file():
                # Read first 100KB to prevent massive memory spikes if accidental
                content = path.read_text(encoding="utf-8", errors="replace")
                context += f"\n--- FILE: {file_path} ---\n{content}\n"
            else:
                context += f"\n[!] Warning: File {file_path} not found or inaccessible.\n"
        except Exception as e:
            context += f"\n[!] Error reading {file_path}: {e}\n"
    
    context += "\n=== END OF FILE CONTEXT ===\n\n"
    return context + prompt



# === OPENCODE MODEL RESOLUTION HELPERS ===

_opencode_config_cache = None

def _load_opencode_config():
    import json
    global _opencode_config_cache
    if _opencode_config_cache is None:
        # app/core/striker.py -> repo root is two levels up (parents[2])
        config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "opencode_models.json")
        try:
            with open(config_path) as f:
                _opencode_config_cache = json.load(f)
        except Exception:
            _opencode_config_cache = {}
    return _opencode_config_cache

def _resolve_opencode_model(model_id, section):
    config = _load_opencode_config()
    for entry in config.get(section, []):
        if entry.get("model_id") == model_id:
            result = dict(entry)
            # Apply env var override for base_url if set
            env_var = "OPENCODE_" + section.upper() + "_BASE_URL"
            override = os.getenv(env_var)
            if override:
                result["base_url"] = override
                result["endpoint"] = override + "/chat/completions"
            return result
    return None

def _build_opencode_provider(base_url, api_key, package, model_id, http_client):
    if package == "@ai-sdk/anthropic":
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        # Anthropic models use custom proxy path
        anthropic_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        provider = AnthropicProvider(base_url=anthropic_url, api_key=api_key, http_client=http_client)
        model = AnthropicModel(model_id, provider=provider)
    elif package == "@ai-sdk/openai":
        provider = OpenAIProvider(base_url=base_url, api_key=api_key, http_client=http_client)
        model = OpenAIModel(model_id, provider=provider)
    else:  # @ai-sdk/openai-compatible (default)
        provider = OpenAIProvider(base_url=base_url, api_key=api_key, http_client=http_client)
        model = OpenAIModel(model_id, provider=provider)
    return provider, model

# === END OPENCODE HELPERS ===
async def execute_strike(gateway: str, model_id: str, prompt: str, 
                         format_mode: Optional[str] = None, response_format: Optional[dict] = None,
                         dynamic_schema: Optional[dict] = None, is_manual: bool = False,
                         timeout: Optional[int] = None, files: Optional[List[str]] = None,
                         key_override: Optional[str] = None, **gen_params):
    """
    Execute a strike against an AI model with built-in Rev Limiter.
    """
    if files:
        prompt = _inject_file_context(prompt, files)
        
    start_time = time.time()
    
    # Pre-count tokens for validation and logging
    estimated_tokens = count_tokens_for_strike(gateway, model_id, prompt)
    if os.getenv("PEACOCK_VERBOSE") == "true":
        print(f"[Tokens] Pre-count estimate: {estimated_tokens}")
    
    # Construct ModelSettings
    # Map gen_params to pydantic-ai ModelSettings keys
    model_settings = {
        "temperature": gen_params.get("temperature", 0.7),
        "top_p": gen_params.get("top_p"),
        "top_k": gen_params.get("top_k"),
        "max_tokens": gen_params.get("max_tokens"),
        "seed": gen_params.get("seed"),
        "presence_penalty": gen_params.get("presence_penalty"),
        "frequency_penalty": gen_params.get("frequency_penalty"),
        "stop_sequences": gen_params.get("stop_sequences"),
    }
    # Remove None values to avoid overriding provider defaults if not requested
    model_settings = {k: v for k, v in model_settings.items() if v is not None}

    result_type = str
    if format_mode == "eagle_scaffold":
        result_type = EagleScaffold
    elif format_mode == "pydantic" and dynamic_schema:
        result_type = _build_dynamic_schema(dynamic_schema)

    model_config = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if model_config and model_config.status == "frozen":
        raise Exception(f"Model {model_id} is currently FROZEN.")

    # Provider enable gate
    if not config_store.is_provider_enabled(gateway):
        raise Exception(f"Provider {gateway} is currently disabled.")

    # 1. Proactive Throttle (Groq uses TB-001 tracker per-key instead)
    if gateway != "groq":
        was_throttled = await ThrottleController.wait_if_needed(gateway, model_id)

    # 2. Execution Loop (Retry on 429)
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        model = None
        asset = None
        pool = None
        
        # Decide which HTTP client to use
        active_client = http_client
        temp_client = None
        
        try:
            # Resolve Provider & Key
            if key_override:
                asset = KeyAsset(label="AUDIT_OVERRIDE", account="AUDIT_OVERRIDE", key=key_override)
            
            if gateway == "groq":
                pool = GroqPool
                if not key_override:
                    asset = await pool.get_next_intelligent(model_id, estimated_tokens)
                # --- TB-004 PRE-FLIGHT GUARD ---
                from app.core.pre_flight_guard import check_request_safety
                candidate_keys = [a.account for a in pool.deck]
                preflight = await check_request_safety(
                    request_data={"messages": [{"role": "user", "content": prompt}], "max_tokens": gen_params.get("max_tokens")},
                    model_id=model_id,
                    key_label=asset.account,
                    candidate_keys=candidate_keys,
                )
                if not preflight.allowed:
                    pool.mark_cooldown(asset.account, duration=60)
                    if os.getenv("PEACOCK_VERBOSE") == "true":
                        print(f"[!] Pre-flight blocked for {asset.account}: {preflight.reason} → {preflight.suggested_action}")
                    continue
                # --- TB-012 PROXY RULES ---
                from app.core.proxy_rules import evaluate_rules
                proxy_decision = evaluate_rules(asset.account, model_id, estimated_tokens)
                if proxy_decision["route"] == "proxy" and (tunnel_client or proxy_client):
                    active_client = tunnel_client or proxy_client
                    if os.getenv("PEACOCK_VERBOSE") == "true":
                        print(f"[!] Proxy routing triggered for {asset.account}: {proxy_decision['rationale']}")
                # --------------------------
                # --- TB-009 PACER ---
                await GroqPacer.acquire(asset.account, model_id, estimated_tokens)
                # --------------------
                await GroqRateTracker.begin_request(asset.account, model_id)
                # --------------------------------
                if timeout is not None:
                    actual_timeout = 3600.0 if timeout <= 0 else float(timeout)
                    if active_client is tunnel_client:
                        temp_client = httpx.AsyncClient(proxy=TUNNEL_SOCKS, timeout=actual_timeout, trust_env=False)
                    elif active_client is proxy_client:
                        temp_client = httpx.AsyncClient(proxy=proxy_url, timeout=actual_timeout, trust_env=False)
                    else:
                        temp_client = httpx.AsyncClient(timeout=actual_timeout, trust_env=False)
                    active_client = temp_client
                provider = GroqProvider(api_key=asset.key, http_client=active_client)
                model = GroqModel(model_id, provider=provider)
            elif gateway == "deepseek":
                pool = DeepSeekPool
                if not key_override:
                    asset = pool.get_next()
                provider = OpenAIProvider(base_url="https://api.deepseek.com", api_key=asset.key, http_client=active_client)
                model = OpenAIModel(model_id, provider=provider)
            elif gateway == "mistral":
                pool = MistralPool
                if not key_override:
                    asset = pool.get_next()
                provider = OpenAIProvider(base_url="https://api.mistral.ai/v1", api_key=asset.key, http_client=active_client)
                model = OpenAIModel(model_id, provider=provider)
            elif gateway == "google":
                pool = GooglePool
                if not key_override:
                    asset = pool.get_next()
                clean_model_id = model_id.replace("models/", "")
                provider = GoogleProvider(api_key=asset.key, http_client=active_client)
                model = GoogleModel(clean_model_id, provider=provider)
            elif gateway == "zai":
                pool = ZaiPool
                if not key_override:
                    asset = pool.get_next()
                provider = OpenAIProvider(base_url="https://api.z.ai/api/paas/v4", api_key=asset.key, http_client=active_client)
                model = OpenAIModel(model_id, provider=provider)
            elif gateway == "zai-coding":
                pool = ZaiCodingPool
                if not key_override:
                    asset = pool.get_next()
                provider = OpenAIProvider(base_url="https://api.z.ai/api/coding/paas/v4", api_key=asset.key, http_client=active_client)
                model = OpenAIModel(model_id, provider=provider)
            elif gateway == "ollama":
                pool = OllamaPool
                if not key_override:
                    asset = pool.get_next()
                provider = OpenAIProvider(base_url="https://ollama.com/v1", api_key=asset.key, http_client=active_client)
                model = OpenAIModel(model_id, provider=provider)
            elif gateway == "opencode-go":
                pool = OpencodeGoPool
                if not key_override:
                    asset = pool.get_next()
                # Registry exposes -go suffixed ids (e.g. glm-5.2-go) but the upstream
                # OpenCode Go gateway and config/opencode_models.json use bare ids
                # (e.g. glm-5.2). Strip the -go suffix once here so every downstream
                # use (config lookup, provider build, fallback model construct) sends
                # the unsuffixed id upstream. Registry-facing model_id is unchanged.
                upstream_id = model_id[:-3] if model_id.endswith("-go") else model_id
                # Resolve per-model endpoint and SDK package from opencode config
                opencode_cfg = _resolve_opencode_model(upstream_id, "go")
                if opencode_cfg:
                    base_url = opencode_cfg.get("base_url")
                    if not base_url:
                        # Use proxy URL with provider in path
                        base_url = "https://opencode.ai/zen/go/v1"
                    package = opencode_cfg.get("ai_sdk_package", "@ai-sdk/openai-compatible")
                    provider, model = _build_opencode_provider(base_url, asset.key, package, upstream_id, active_client)
                else:
                    # Fallback to proxy URL
                    base_url = "https://opencode.ai/zen/go/v1"
                    provider = OpenAIProvider(base_url=base_url, api_key=asset.key, http_client=active_client)
                    model = OpenAIModel(upstream_id, provider=provider)
            elif gateway == "opencode-zen":
                pool = OpencodeZenPool
                if not key_override:
                    asset = pool.get_next()
                # Resolve per-model endpoint and SDK package from opencode config
                opencode_cfg = _resolve_opencode_model(model_id, "zen")
                if opencode_cfg:
                    base_url = opencode_cfg.get("base_url")
                    if not base_url:
                        # Use proxy URL with provider in path
                        base_url = "https://opencode.ai/zen/v1"
                    package = opencode_cfg.get("ai_sdk_package", "@ai-sdk/openai-compatible")
                    provider, model = _build_opencode_provider(base_url, asset.key, package, model_id, active_client)
                else:
                    # Fallback to proxy URL
                    base_url = "https://opencode.ai/zen/v1"
                    provider = OpenAIProvider(base_url=base_url, api_key=asset.key, http_client=active_client)
                    model = OpenAIModel(model_id, provider=provider)
            elif gateway == "openrouter":
                pool = OpenrouterPool
                if not key_override:
                    asset = pool.get_next()
                provider = OpenAIProvider(base_url="https://openrouter.ai/api/v1", api_key=asset.key, http_client=active_client)
                model = OpenAIModel(model_id, provider=provider)
            else:
                raise Exception(f"Gateway {gateway} not supported")
            
            # Non-groq timeout client (groq handles this inside its pacer block)
            if gateway != "groq" and timeout is not None:
                actual_timeout = 3600.0 if timeout <= 0 else float(timeout)
                if tunnel_enabled:
                    temp_client = httpx.AsyncClient(proxy=TUNNEL_SOCKS, timeout=actual_timeout, trust_env=False)
                elif proxy_enabled and proxy_url:
                    temp_client = httpx.AsyncClient(proxy=proxy_url, timeout=actual_timeout, trust_env=False)
                else:
                    temp_client = httpx.AsyncClient(timeout=actual_timeout, trust_env=False)
                active_client = temp_client

            # Execute
            agent = Agent(model, result_type=result_type)
            result = await agent.run(prompt, model_settings=model_settings)
            content = result.data.model_dump() if hasattr(result.data, "model_dump") else result.data
            
            # Resolve Usage
            usage_obj = result.usage()
            usage = {
                "prompt_tokens": usage_obj.request_tokens or 0,
                "completion_tokens": usage_obj.response_tokens or 0,
                "total_tokens": usage_obj.total_tokens or 0
            }
            
            # Gemini usage recovery
            if gateway == "google" and usage["total_tokens"] == 0:
                if hasattr(result, 'metadata') and result.metadata:
                    usage["prompt_tokens"] = result.metadata.get('promptTokenCount', 0)
                    usage["completion_tokens"] = result.metadata.get('candidatesTokenCount', 0)
                    usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
            
            # Token count validation (compare estimate vs actual)
            if usage["prompt_tokens"] > 0:
                diff = abs(estimated_tokens - usage["prompt_tokens"])
                accuracy = 100 - (diff / usage["prompt_tokens"] * 100) if usage["prompt_tokens"] > 0 else 0
                if os.getenv("PEACOCK_VERBOSE") == "true":
                    print(f"[Tokens] Estimated: {estimated_tokens}, Actual: {usage['prompt_tokens']}, Accuracy: {accuracy:.1f}%")
            
            # Store estimated tokens for reference
            usage["estimated_tokens"] = estimated_tokens
            
            cost = _calculate_cost(model_id, usage)
            KeyPool.record_usage(gateway, asset.account, usage)
            
            # --- TB-001 TELEMETRY ---
            if gateway == "groq":
                await GroqRateTracker.consume(asset.account, model_id, usage['total_tokens'])
                t = GroqRateTracker.get_telemetry(asset.account, model_id)
                meter = f"Tracker: [RPM:{t.rpm_pct}% | TPM:{t.tpm_pct}% | Status:{t.status} | Active:{t.active_requests}]"
            else:
                RateLimitMeter.update(gateway, usage['total_tokens'])
                meter = RateLimitMeter.get_meter(gateway, model_id)
            # ------------------------
            
            # Use requested temperature for logging
            active_temp = model_settings.get("temperature", 0.7)
            tag = HighSignalLogger.log_strike(gateway, model_id, prompt, str(content), usage, active_temp, cost, is_success=True, is_manual=is_manual)
            duration = time.time() - start_time
            CLIFormatter.strike_success(gateway, asset.account, model_id, usage['prompt_tokens'], usage['completion_tokens'], duration, format_mode, temp=active_temp, tag=tag, cost=cost, meter=meter)
            
            return {
                "content": content, 
                "keyUsed": asset.account,
                "usage": usage,
                "tag": tag,
                "cost": cost
            }

        except Exception as e:
            last_error = e
            error_str = str(e).lower()

            # --- TB-004: Non-Groq failure policy (classify → log → cooldown) ---
            # Route non-Groq failures through the shared handler so they are
            # classified and logged to the JSONL sink. The handler applies a
            # cooldown ONLY for rate_limit / auth classes (via apply_failure_policy).
            # Groq keeps its own error handling (separate slice).
            if gateway != "groq" and pool and asset:
                _ng_result = handle_provider_exception(
                    pool, asset,
                    gateway=gateway, model=model_id, error=e,
                )
                # Retry only when a cooldown class was applied (rate_limit/auth).
                if _ng_result.get("cooldown_applied"):
                    if os.getenv("PEACOCK_VERBOSE") == "true":
                        print(f"[!] {gateway} failure ({_ng_result['classification']}) on "
                              f"{asset.account}. Cycling key (Attempt {attempt+1}/{max_retries})...")
                    continue
                # Non-cooldown failure: log already written; stop retrying.
                break

            # --- Groq 429 handling (unchanged — separate slice owns Groq) ---
            if "429" in error_str or "rate limit" in error_str:
                if gateway == "groq" and asset:
                    await GroqRateTracker.record_429(asset.account, model_id)
                if pool and asset:
                    pool.mark_cooldown(asset.account, duration=60)
                    if os.getenv("PEACOCK_VERBOSE") == "true":
                        print(f"[!] 429 Detected on {asset.account}. Cycling key and retrying (Attempt {attempt+1}/{max_retries})...")
                    continue # Try again with next key

            # Handle non-429 errors or max retries reached
            break
        finally:
            if gateway == "groq" and asset:
                await GroqRateTracker.end_request(asset.account, model_id)
                GroqPacer.release(asset.account, model_id)
            if temp_client:
                await temp_client.aclose()

    # If we got here, all attempts failed
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    active_err_temp = model_settings.get("temperature", 0.7)
    tag = HighSignalLogger.log_strike(gateway, model_id, prompt, "", usage, active_err_temp, 0.0, is_success=False, is_manual=is_manual, error=str(last_error))
    CLIFormatter.strike_error(gateway, "RETRY_EXHAUSTED", str(last_error), model_id, temp=active_err_temp, tag=tag)
    raise last_error


async def execute_streaming_strike(gateway: str, model_id: str, prompt: str,
                                   is_manual: bool = True, timeout: Optional[int] = None, 
                                   files: Optional[List[str]] = None,
                                   key_override: Optional[str] = None, **gen_params):
    """
    Execute a streaming strike using Server-Sent Events (SSE).
    """
    if files:
        prompt = _inject_file_context(prompt, files)

    start_time = time.time()
    model_config = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if model_config and model_config.status == "frozen":
        raise Exception(f"Model {model_id} is currently FROZEN.")

    # Pre-count tokens for validation, guard, and pacing
    estimated_tokens = count_tokens_for_strike(gateway, model_id, prompt)
    if os.getenv("PEACOCK_VERBOSE") == "true":
        print(f"[Tokens] Pre-count estimate: {estimated_tokens}")

    # Throttling (Groq uses TB-001 tracker)
    if gateway != "groq":
        await ThrottleController.wait_if_needed(gateway, model_id)

    model_settings = {
        "temperature": gen_params.get("temperature", 0.7),
        "top_p": gen_params.get("top_p"),
        "top_k": gen_params.get("top_k"),
        "max_tokens": gen_params.get("max_tokens"),
        "seed": gen_params.get("seed"),
        "presence_penalty": gen_params.get("presence_penalty"),
        "frequency_penalty": gen_params.get("frequency_penalty"),
        "stop_sequences": gen_params.get("stop_sequences"),
    }
    model_settings = {k: v for k, v in model_settings.items() if v is not None}

    try:
        # Resolve Provider & Key
        asset = None
        model = None
        active_client = http_client
        temp_client = None
        if gateway == "groq":
            if key_override:
                asset = KeyAsset(label="AUDIT_OVERRIDE", account="AUDIT_OVERRIDE", key=key_override)
            else:
                asset = await GroqPool.get_next_intelligent(model_id, estimated_tokens)
            # --- TB-004 PRE-FLIGHT GUARD (streaming) ---
            from app.core.pre_flight_guard import check_request_safety
            streaming_candidates = [a.account for a in GroqPool.deck]
            preflight = await check_request_safety(
                request_data={"messages": [{"role": "user", "content": prompt}]},
                model_id=model_id,
                key_label=asset.account,
                candidate_keys=streaming_candidates,
            )
            if not preflight.allowed:
                GroqPool.mark_cooldown(asset.account, duration=60)
                raise Exception(f"Pre-flight blocked for {asset.account}: {preflight.reason} → {preflight.suggested_action}")
            # --- TB-012 PROXY RULES ---
            from app.core.proxy_rules import evaluate_rules
            proxy_decision = evaluate_rules(asset.account, model_id, estimated_tokens)
            if proxy_decision["route"] == "proxy" and (tunnel_client or proxy_client):
                active_client = tunnel_client or proxy_client
                if os.getenv("PEACOCK_VERBOSE") == "true":
                    print(f"[!] Proxy routing triggered for {asset.account}: {proxy_decision['rationale']}")
            # --------------------------
            # --- TB-009 PACER ---
            await GroqPacer.acquire(asset.account, model_id, estimated_tokens)
            # --------------------
            await GroqRateTracker.begin_request(asset.account, model_id)
            # -------------------------------------------
            if timeout is not None:
                actual_timeout = 3600.0 if timeout <= 0 else float(timeout)
                if active_client is tunnel_client:
                    temp_client = httpx.AsyncClient(proxy=TUNNEL_SOCKS, timeout=actual_timeout, trust_env=False)
                elif active_client is proxy_client:
                    temp_client = httpx.AsyncClient(proxy=proxy_url, timeout=actual_timeout, trust_env=False)
                else:
                    temp_client = httpx.AsyncClient(timeout=actual_timeout, trust_env=False)
                active_client = temp_client
            provider = GroqProvider(api_key=asset.key, http_client=active_client)
            model = GroqModel(model_id, provider=provider)
        elif gateway == "google":
            asset = GooglePool.get_next()
            clean_model_id = model_id.replace("models/", "")
            provider = GoogleProvider(api_key=asset.key, http_client=active_client)
            model = GoogleModel(clean_model_id, provider=provider)
        elif gateway == "deepseek":
            asset = DeepSeekPool.get_next()
            provider = OpenAIProvider(base_url="https://api.deepseek.com", api_key=asset.key, http_client=active_client)
            model = OpenAIModel(model_id, provider=provider)
        elif gateway == "mistral":
            asset = MistralPool.get_next()
            provider = OpenAIProvider(base_url="https://api.mistral.ai/v1", api_key=asset.key, http_client=active_client)
            model = OpenAIModel(model_id, provider=provider)
        
        # Non-groq timeout client
        if gateway != "groq" and timeout is not None:
            actual_timeout = 3600.0 if timeout <= 0 else float(timeout)
            if tunnel_enabled:
                temp_client = httpx.AsyncClient(proxy=TUNNEL_SOCKS, timeout=actual_timeout, trust_env=False)
            elif proxy_enabled and proxy_url:
                temp_client = httpx.AsyncClient(proxy=proxy_url, timeout=actual_timeout, trust_env=False)
            else:
                temp_client = httpx.AsyncClient(timeout=actual_timeout, trust_env=False)
            active_client = temp_client
            # Re-create provider with new client if needed
            if gateway == "google":
                provider = GoogleProvider(api_key=asset.key, http_client=active_client)
                model = GoogleModel(clean_model_id, provider=provider)
            elif gateway == "deepseek":
                provider = OpenAIProvider(base_url="https://api.deepseek.com", api_key=asset.key, http_client=active_client)
                model = OpenAIModel(model_id, provider=provider)
            elif gateway == "mistral":
                provider = OpenAIProvider(base_url="https://api.mistral.ai/v1", api_key=asset.key, http_client=active_client)
                model = OpenAIModel(model_id, provider=provider)

        agent = Agent(model)
        async with agent.run_stream(prompt, model_settings=model_settings) as result:
            async for chunk in result.stream_text(delta=True):
                yield {"type": "content", "content": chunk}
            
            # Finalize
            usage_obj = result.usage()
            usage = {
                "prompt_tokens": usage_obj.request_tokens or 0,
                "completion_tokens": usage_obj.response_tokens or 0,
                "total_tokens": usage_obj.total_tokens or 0
            }
            # Gemini fix
            if gateway == "google" and usage["total_tokens"] == 0:
                pass
            
            cost = _calculate_cost(model_id, usage)
            KeyPool.record_usage(gateway, asset.account, usage)
            
            # --- TB-001 TELEMETRY (streaming) ---
            if gateway == "groq":
                await GroqRateTracker.consume(asset.account, model_id, usage['total_tokens'])
            else:
                RateLimitMeter.update(gateway, usage['total_tokens'])
            # ------------------------------------
            
            active_temp = model_settings.get("temperature", 0.7)
            tag = HighSignalLogger.log_strike(gateway, model_id, prompt, "STREAMS_COMPLETE", usage, active_temp, cost, is_success=True, is_manual=is_manual)
            duration = time.time() - start_time
            
            yield {
                "type": "metadata",
                "model": model_id,
                "gateway": gateway,
                "keyUsed": asset.account,
                "usage": usage,
                "cost": cost,
                "duration_ms": int(duration * 1000),
                "tag": tag
            }

    except Exception as e:
        if gateway == "groq" and asset:
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str:
                await GroqRateTracker.record_429(asset.account, model_id)
        yield {"type": "error", "content": str(e)}
        raise e
    finally:
        if gateway == "groq" and asset:
            await GroqRateTracker.end_request(asset.account, model_id)
            GroqPacer.release(asset.account, model_id)
        if temp_client:
            await temp_client.aclose()


async def execute_precision_strike(gateway: str, model_id: str, prompt: str, target_account: str, is_manual: bool = True, timeout: Optional[int] = None, **gen_params):
    """
    PERFORM A PRECISION STRIKE.
    """
    start_time = time.time()
    pool = None
    if gateway == "groq": pool = GroqPool
    elif gateway == "google": pool = GooglePool
    elif gateway == "deepseek": pool = DeepSeekPool
    elif gateway == "mistral": pool = MistralPool
    else: raise Exception(f"Precision Strike Error: Gateway {gateway} not supported")

    asset = next((a for a in pool.deck if a.account == target_account), None)
    if not asset: raise Exception(f"Precision Strike Failed: account '{target_account}' not found.")

    model_config = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if model_config and model_config.status == "frozen":
        raise Exception(f"Model {model_id} is currently FROZEN.")

    model_settings = {
        "temperature": gen_params.get("temperature", 0.7),
        "top_p": gen_params.get("top_p"),
        "top_k": gen_params.get("top_k"),
        "max_tokens": gen_params.get("max_tokens"),
        "seed": gen_params.get("seed"),
        "presence_penalty": gen_params.get("presence_penalty"),
        "frequency_penalty": gen_params.get("frequency_penalty"),
        "stop_sequences": gen_params.get("stop_sequences"),
    }
    model_settings = {k: v for k, v in model_settings.items() if v is not None}

    # Decide which HTTP client to use
    active_client = http_client
    temp_client = None

    # Initialize Model
    model = None
    if gateway == "groq":
        # --- TB-004 PRECISION PRE-FLIGHT ---
        from app.core.pre_flight_guard import check_request_safety
        precision_candidates = [a.account for a in pool.deck]
        preflight = await check_request_safety(
            request_data={"messages": [{"role": "user", "content": prompt}]},
            model_id=model_id,
            key_label=asset.account,
            candidate_keys=precision_candidates,
        )
        if not preflight.allowed:
            raise Exception(f"Pre-flight blocked for {asset.account}: {preflight.reason} → {preflight.suggested_action}")
        # --- TB-012 PROXY RULES ---
        from app.core.proxy_rules import evaluate_rules
        estimated_tokens = count_tokens_for_strike(gateway, model_id, prompt)
        proxy_decision = evaluate_rules(asset.account, model_id, estimated_tokens)
        if proxy_decision["route"] == "proxy" and (tunnel_client or proxy_client):
            active_client = tunnel_client or proxy_client
            if os.getenv("PEACOCK_VERBOSE") == "true":
                print(f"[!] Proxy routing triggered for {asset.account}: {proxy_decision['rationale']}")
        # --------------------------
        # --- TB-009 PACER ---
        await GroqPacer.acquire(asset.account, model_id, estimated_tokens)
        # --------------------
        await GroqRateTracker.begin_request(asset.account, model_id)
        # -------------------------------------
        if timeout is not None:
            actual_timeout = 3600.0 if timeout <= 0 else float(timeout)
            if active_client is tunnel_client:
                temp_client = httpx.AsyncClient(proxy=TUNNEL_SOCKS, timeout=actual_timeout, trust_env=False)
            elif active_client is proxy_client:
                temp_client = httpx.AsyncClient(proxy=proxy_url, timeout=actual_timeout, trust_env=False)
            else:
                temp_client = httpx.AsyncClient(timeout=actual_timeout, trust_env=False)
            active_client = temp_client
        provider = GroqProvider(api_key=asset.key, http_client=active_client)
        model = GroqModel(model_id, provider=provider)
    elif gateway == "google":
        clean_model_id = model_id.replace("models/", "")
        provider = GoogleProvider(api_key=asset.key, http_client=active_client)
        model = GoogleModel(clean_model_id, provider=provider)
    elif gateway == "deepseek":
        provider = OpenAIProvider(base_url="https://api.deepseek.com", api_key=asset.key, http_client=active_client)
        model = OpenAIModel(model_id, provider=provider)
    elif gateway == "mistral":
        provider = OpenAIProvider(base_url="https://api.mistral.ai/v1", api_key=asset.key, http_client=active_client)
        model = OpenAIModel(model_id, provider=provider)
    
    # Non-groq timeout client
    if gateway != "groq" and timeout is not None:
        actual_timeout = 3600.0 if timeout <= 0 else float(timeout)
        if tunnel_enabled:
            temp_client = httpx.AsyncClient(proxy=TUNNEL_SOCKS, timeout=actual_timeout, trust_env=False)
        elif proxy_enabled and proxy_url:
            temp_client = httpx.AsyncClient(proxy=proxy_url, timeout=actual_timeout, trust_env=False)
        else:
            temp_client = httpx.AsyncClient(timeout=actual_timeout, trust_env=False)
        active_client = temp_client
        if gateway == "google":
            provider = GoogleProvider(api_key=asset.key, http_client=active_client)
            model = GoogleModel(clean_model_id, provider=provider)
        elif gateway == "deepseek":
            provider = OpenAIProvider(base_url="https://api.deepseek.com", api_key=asset.key, http_client=active_client)
            model = OpenAIModel(model_id, provider=provider)
        elif gateway == "mistral":
            provider = OpenAIProvider(base_url="https://api.mistral.ai/v1", api_key=asset.key, http_client=active_client)
            model = OpenAIModel(model_id, provider=provider)

    agent = Agent(model, result_type=str)
    try:
        result = await agent.run(prompt, model_settings=model_settings)
        usage_obj = result.usage()
        usage = {
            "prompt_tokens": usage_obj.request_tokens or 0,
            "completion_tokens": usage_obj.response_tokens or 0,
            "total_tokens": usage_obj.total_tokens or 0
        }
        
        # Gemini fix
        if gateway == "google" and usage["total_tokens"] == 0:
            if hasattr(result, 'metadata') and result.metadata:
                usage["prompt_tokens"] = result.metadata.get('promptTokenCount', 0)
                usage["completion_tokens"] = result.metadata.get('candidatesTokenCount', 0)
                usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]
        
        cost = _calculate_cost(model_id, usage)
        KeyPool.record_usage(gateway, asset.account, usage)
        
        # --- TB-001 TELEMETRY ---
        if gateway == "groq":
            await GroqRateTracker.consume(asset.account, model_id, usage['total_tokens'])
        # ------------------------
        
        active_temp = model_settings.get("temperature", 0.7)
        tag = HighSignalLogger.log_strike(gateway, model_id, prompt, result.data, usage, active_temp, cost, is_success=True, is_manual=is_manual)
        duration = time.time() - start_time
        CLIFormatter.strike_success(gateway, asset.account, model_id, usage['prompt_tokens'], usage['completion_tokens'], duration, temp=active_temp, tag=tag, cost=cost)

        return {
            "content": result.data,
            "keyUsed": asset.account,
            "usage": usage,
            "tag": tag,
            "cost": cost
        }
    except Exception as e:
        if gateway == "groq":
            error_str = str(e).lower()
            if "429" in error_str or "rate limit" in error_str:
                await GroqRateTracker.record_429(asset.account, model_id)
        active_err_temp = model_settings.get("temperature", 0.7)
        tag = HighSignalLogger.log_strike(gateway, model_id, prompt, "", {"prompt_tokens":0, "completion_tokens":0, "total_tokens":0}, active_err_temp, 0.0, is_success=False, is_manual=is_manual, error=str(e))
        CLIFormatter.strike_error(gateway, asset.account, str(e), model_id, temp=active_err_temp, tag=tag)
        raise e
    finally:
        if gateway == "groq" and asset:
            await GroqRateTracker.end_request(asset.account, model_id)
            GroqPacer.release(asset.account, model_id)
        if temp_client:
            await temp_client.aclose()
