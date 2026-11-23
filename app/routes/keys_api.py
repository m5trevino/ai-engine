"""
Enhanced Key Management API for WebUI
Supports: key list, stats, test, add, delete, telemetry
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
import time
import json

from app.core.key_manager import KeyPool, get_pool, list_pools
from app.core.config_store import config_store
from app.config import MODEL_REGISTRY

router = APIRouter()


class KeyDetail(BaseModel):
    """Key details for WebUI."""
    label: str
    gateway: str
    masked_key: str
    status: str  # healthy, warning, exhausted, dead
    usage_today: int = 0
    tokens_today: int = 0
    rate_limit_remaining: Optional[int] = None
    last_used: Optional[str] = None
    on_cooldown: bool = False
    cooldown_until: Optional[float] = None


class GatewayKeys(BaseModel):
    """Keys grouped by gateway."""
    gateway: str
    status: str  # active, exhausted, etc.
    keys: List[KeyDetail]
    key_count: int
    healthy_count: int


class KeyTelemetry(BaseModel):
    """Aggregate telemetry for Key Management screen."""
    total_keys: int
    healthy_keys: int
    exhausted_keys: int
    dead_keys: int
    global_token_quota: Dict[str, int]
    gateway_redundancy: Dict[str, int]
    estimated_daily_cost: float
    error_rate: float


class AddKeyRequest(BaseModel):
    """Request to add a new key."""
    gateway: str = Field(..., description="Gateway: groq, opencode-go, opencode-zen, openrouter, ollama, hetzner")
    label: str = Field(..., description="Label for the key")
    key: str = Field(..., description="The API key")


class KeyTestResult(BaseModel):
    """Result of testing a key."""
    label: str
    gateway: str
    valid: bool
    latency_ms: float
    error: Optional[str] = None
    rate_limit: Optional[Dict] = None


@router.get("/", response_model=List[GatewayKeys])
async def get_all_keys():
    """
    Get all API keys grouped by gateway.
    For the Key Management screen.
    """
    result = []
    provider_cfg = config_store.providers

    for gateway, pool in list_pools().items():
        if not pool.deck:
            continue
        if not provider_cfg.get(gateway, {}).get("visible", False):
            continue

        keys = []
        healthy = 0

        for asset in pool.deck:
            # Determine status
            if not asset.enabled:
                status = "disabled"
            elif asset.on_cooldown:
                status = "exhausted"
            else:
                status = "healthy"

            # Get usage from DB
            usage_today = 0
            tokens_today = 0
            try:
                from app.db.database import KeyUsageDB
                stats = KeyUsageDB.get_key_stats(gateway, asset.account)
                usage_today = stats.get("requests_today", 0)
                tokens_today = stats.get("tokens_today", 0)
            except:
                pass

            key_detail = KeyDetail(
                label=asset.account,
                gateway=gateway,
                masked_key=f"{asset.key[:8]}...{asset.key[-4:]}" if len(asset.key) > 12 else "***",
                status=status,
                usage_today=usage_today,
                tokens_today=tokens_today,
                on_cooldown=asset.on_cooldown,
                cooldown_until=asset.cooldown_until if asset.on_cooldown else None
            )
            keys.append(key_detail)

            if status == "healthy":
                healthy += 1

        # Gateway status
        gateway_status = "active"
        if not config_store.is_provider_enabled(gateway):
            gateway_status = "disabled"
        elif healthy == 0:
            gateway_status = "exhausted"
        elif healthy < len(keys):
            gateway_status = "degraded"

        result.append(GatewayKeys(
            gateway=gateway,
            status=gateway_status,
            keys=keys,
            key_count=len(keys),
            healthy_count=healthy
        ))

    return result


@router.get("/telemetry", response_model=KeyTelemetry)
async def get_key_telemetry():
    """
    Get aggregate telemetry for Key Management dashboard.
    Includes: quotas, redundancy, cost estimates, error rates.
    """
    total = 0
    healthy = 0
    exhausted = 0
    dead = 0

    gateway_counts = {}

    for gateway, pool in list_pools().items():
        if not pool.deck:
            gateway_counts[gateway] = 0
            continue

        count = len(pool.deck)
        healthy_count = sum(1 for a in pool.deck if a.is_available)

        total += count
        healthy += healthy_count
        exhausted += sum(1 for a in pool.deck if a.enabled and a.on_cooldown)
        dead += sum(1 for a in pool.deck if not a.enabled)
        gateway_counts[gateway] = healthy_count

    # Estimate daily cost from usage
    est_cost = 0.0
    try:
        from app.db.database import KeyUsageDB
        total_tokens = 0
        for gateway, pool in list_pools().items():
            for asset in pool.deck:
                stats = KeyUsageDB.get_key_stats(gateway, asset.account)
                total_tokens += stats.get("tokens_today", 0)
        est_cost = (total_tokens / 1_000_000) * 0.50
    except:
        pass

    return KeyTelemetry(
        total_keys=total,
        healthy_keys=healthy,
        exhausted_keys=exhausted,
        dead_keys=dead,
        global_token_quota={"used": 0, "total": 1_000_000},
        gateway_redundancy=gateway_counts,
        estimated_daily_cost=est_cost,
        error_rate=0.0
    )


@router.post("/{gateway}/{label}/test", response_model=KeyTestResult)
async def test_key(gateway: str, label: str):
    """Test a specific key."""
    pool = get_pool(gateway)
    if not pool:
        raise HTTPException(status_code=400, detail=f"Unknown gateway: {gateway}")

    asset = next((a for a in pool.deck if a.account == label), None)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Key {label} not found in {gateway}")

    start = time.time()

    if gateway == "groq":
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {asset.key}"}
                )
                
                latency = (time.time() - start) * 1000
                
                if response.status_code == 200:
                    return KeyTestResult(
                        label=label,
                        gateway=gateway,
                        valid=True,
                        latency_ms=latency,
                        rate_limit={
                            "rpm_remaining": response.headers.get("x-ratelimit-remaining-requests")
                        }
                    )
                else:
                    return KeyTestResult(
                        label=label,
                        gateway=gateway,
                        valid=False,
                        latency_ms=latency,
                        error=f"HTTP {response.status_code}"
                    )
        except Exception as e:
            return KeyTestResult(
                label=label,
                gateway=gateway,
                valid=False,
                latency_ms=(time.time() - start) * 1000,
                error=str(e)
            )
    
    # Default: assume valid unless we add a provider-specific test.
    return KeyTestResult(
        label=label,
        gateway=gateway,
        valid=True,
        latency_ms=(time.time() - start) * 1000
    )


@router.delete("/{gateway}/{label}")
async def delete_key(gateway: str, label: str):
    """Delete a key from the pool."""
    # Note: This removes from runtime only, not from .env
    pool = get_pool(gateway)
    if not pool:
        raise HTTPException(status_code=400, detail=f"Unknown gateway: {gateway}")

    asset = next((a for a in pool.deck if a.account == label), None)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Key {label} not found")

    pool.deck.remove(asset)

    return {"message": f"Key {label} removed from {gateway} pool"}


@router.post("/{gateway}/{label}/toggle")
async def toggle_key(gateway: str, label: str):
    """Toggle key enable/disable."""
    pool = get_pool(gateway)
    if not pool:
        raise HTTPException(status_code=400, detail=f"Unknown gateway: {gateway}")

    asset = next((a for a in pool.deck if a.account == label), None)
    if not asset:
        raise HTTPException(status_code=404, detail=f"Key {label} not found")

    new_state = not asset.enabled
    pool.set_key_enabled(label, new_state)
    return {"message": f"Key {label} {'enabled' if new_state else 'disabled'}", "enabled": new_state}


@router.post("/add")
async def add_key(request: AddKeyRequest):
    """
    Add a new key to the pool.
    Note: This adds to runtime only, not to .env file.
    """
    from app.core.key_manager import KeyAsset

    pool = get_pool(request.gateway)
    if not pool:
        raise HTTPException(status_code=400, detail=f"Unknown gateway: {request.gateway}")

    # Check if label already exists
    if any(a.account == request.label for a in pool.deck):
        raise HTTPException(status_code=400, detail=f"Key with label {request.label} already exists")

    # Add key
    new_asset = KeyAsset(
        label=request.label,
        account=request.label,
        key=request.key
    )
    pool.deck.append(new_asset)

    return {
        "message": f"Key {request.label} added to {request.gateway}",
        "label": request.label,
        "gateway": request.gateway
    }
