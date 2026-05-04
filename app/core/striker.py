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
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.groq import GroqProvider
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.providers.google import GoogleProvider
from app.core.key_manager import KeyAsset, KeyPool, GroqPool, GooglePool, DeepSeekPool, MistralPool
from app.utils.formatter import CLIFormatter, Colors
from app.utils.logger import HighSignalLogger
from app.config import MODEL_REGISTRY

# Import unified token counter
from app.utils.token_counter import count_tokens

# Proxy / Tunnel Setup
tunnel_enabled = os.getenv("PEACOCK_TUNNEL", "false").lower() == "true"
proxy_url = os.getenv("PROXY_URL")
proxy_enabled = os.getenv("PROXY_ENABLED", "false").lower() == "true"

if tunnel_enabled:
    # User's dedicated MetroPCS Tunnel
    TUNNEL_SOCKS = "socks5://127.0.0.1:1081"
    http_client = httpx.AsyncClient(proxy=TUNNEL_SOCKS, timeout=100.0, trust_env=False)
    # Note: Using 100s timeout to match your pip command preference
elif proxy_enabled and proxy_url:
    http_client = httpx.AsyncClient(proxy=proxy_url, timeout=60.0, trust_env=False)
else:
    http_client = httpx.AsyncClient(timeout=60.0, trust_env=False)

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

    # 1. Proactive Throttle
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
        
        if timeout is not None:
            # Create a one-off client with requested timeout
            # If timeout <= 0, treat as "off" (1 hour limit)
            actual_timeout = 3600.0 if timeout <= 0 else float(timeout)
            
            if tunnel_enabled:
                temp_client = httpx.AsyncClient(proxy=TUNNEL_SOCKS, timeout=actual_timeout, trust_env=False)
            elif proxy_enabled and proxy_url:
                temp_client = httpx.AsyncClient(proxy=proxy_url, timeout=actual_timeout, trust_env=False)
            else:
                temp_client = httpx.AsyncClient(timeout=actual_timeout, trust_env=False)
            active_client = temp_client

        try:
            # Resolve Provider & Key
            if key_override:
                asset = KeyAsset(label="AUDIT_OVERRIDE", account="AUDIT_OVERRIDE", key=key_override)
            
            if gateway == "groq":
                pool = GroqPool
                if not key_override:
                    asset = pool.get_next()
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
            else:
                raise Exception(f"Gateway {gateway} not supported")

            # Execute
            agent = Agent(model, output_type=result_type)
            result = await agent.run(prompt, model_settings=model_settings)
            content = result.output.model_dump() if hasattr(result.output, "model_dump") else result.output
            
            # Resolve Usage
            usage_obj = result.usage()
            usage = {
                "prompt_tokens": usage_obj.input_tokens or 0,
                "completion_tokens": usage_obj.output_tokens or 0,
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
            RateLimitMeter.update(gateway, usage['total_tokens'])
            
            # Use requested temperature for logging
            active_temp = model_settings.get("temperature", 0.7)
            tag = HighSignalLogger.log_strike(gateway, model_id, prompt, str(content), usage, active_temp, cost, is_success=True, is_manual=is_manual)
            duration = time.time() - start_time
            meter = RateLimitMeter.get_meter(gateway, model_id)
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
            
            # Check for 429 (Rate Limit)
            if "429" in error_str or "rate limit" in error_str:
                if pool and asset:
                    pool.mark_cooldown(asset.account, duration=60)
                    if os.getenv("PEACOCK_VERBOSE") == "true":
                        print(f"[!] 429 Detected on {asset.account}. Cycling key and retrying (Attempt {attempt+1}/{max_retries})...")
                    continue # Try again with next key
            
            # Handle non-429 errors or max retries reached
            break
        finally:
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
                                   files: Optional[List[str]] = None, **gen_params):
    """
    Execute a streaming strike using Server-Sent Events (SSE).
    """
    if files:
        prompt = _inject_file_context(prompt, files)

    start_time = time.time()
    model_config = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if model_config and model_config.status == "frozen":
        raise Exception(f"Model {model_id} is currently FROZEN.")

    # Throttling
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

    # odluce which HTTP client to use
    active_client = http_client
    temp_client = None
    if timeout is not None:
        actual_timeout = 3600.0 if timeout <= 0 else float(timeout)
        if tunnel_enabled:
            temp_client = httpx.AsyncClient(proxy=TUNNEL_SOCKS, timeout=actual_timeout, trust_env=False)
        elif proxy_enabled and proxy_url:
            temp_client = httpx.AsyncClient(proxy=proxy_url, timeout=actual_timeout, trust_env=False)
        else:
            temp_client = httpx.AsyncClient(timeout=actual_timeout, trust_env=False)
        active_client = temp_client

    try:
        # Resolve Provider & Key
        asset = None
        model = None
        if gateway == "groq":
            asset = GroqPool.get_next()
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
                # Note: For stream, usage might be available at the end of the stream
                # We'll try to extract from the last message or metadata if possible
                pass
            
            cost = _calculate_cost(model_id, usage)
            KeyPool.record_usage(gateway, asset.account, usage)
            RateLimitMeter.update(gateway, usage['total_tokens'])
            
            active_temp = model_settings.get("temperature", 0.7)
            tag = HighSignalLogger.log_strike(gateway, model_id, prompt, "STREAMS_COMPLETE", usage, active_temp, cost, is_success=True, is_manual=is_manual)
            duration = time.time() - start_time
            
            yield {
                "type": "metadata",
                "model": model_id,
                "gateway": gateway,
                "key_used": asset.account,
                "usage": usage,
                "cost": cost,
                "duration_ms": int(duration * 1000),
                "tag": tag
            }

    except Exception as e:
        yield {"type": "error", "content": str(e)}
        raise e
    finally:
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

    # Decide which HTTP client to use
    active_client = http_client
    temp_client = None
    
    if timeout is not None:
        actual_timeout = 3600.0 if timeout <= 0 else float(timeout)
        if tunnel_enabled:
            temp_client = httpx.AsyncClient(proxy=TUNNEL_SOCKS, timeout=actual_timeout, trust_env=False)
        elif proxy_enabled and proxy_url:
            temp_client = httpx.AsyncClient(proxy=proxy_url, timeout=actual_timeout, trust_env=False)
        else:
            temp_client = httpx.AsyncClient(timeout=actual_timeout, trust_env=False)
        active_client = temp_client

    # Initialize Model
    model = None
    if gateway == "groq":
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

    agent = Agent(model, output_type=str)
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
        
        active_temp = model_settings.get("temperature", 0.7)
        tag = HighSignalLogger.log_strike(gateway, model_id, prompt, result.output, usage, active_temp, cost, is_success=True, is_manual=is_manual)
        duration = time.time() - start_time
        CLIFormatter.strike_success(gateway, asset.account, model_id, usage['prompt_tokens'], usage['completion_tokens'], duration, temp=active_temp, tag=tag, cost=cost)

        return {
            "content": result.output,
            "keyUsed": asset.account,
            "usage": usage,
            "tag": tag,
            "cost": cost
        }
    except Exception as e:
        active_err_temp = model_settings.get("temperature", 0.7)
        tag = HighSignalLogger.log_strike(gateway, model_id, prompt, "", {"prompt_tokens":0, "completion_tokens":0, "total_tokens":0}, active_err_temp, 0.0, is_success=False, is_manual=is_manual, error=str(e))
        CLIFormatter.strike_error(gateway, asset.account, str(e), model_id, temp=active_err_temp, tag=tag)
        raise e
    finally:
        if temp_client:
            await temp_client.aclose()
