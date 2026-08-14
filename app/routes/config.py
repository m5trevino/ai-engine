"""
PEACOCK ENGINE — Runtime Config API (TB-021 / TB-024)
Read and update proxy rules, guard thresholds, burn mode, and cleanup TTL.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config_store import config_store

router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST / RESPONSE MODELS
# ═══════════════════════════════════════════════════════════════════════════════

class ProxyRulesConfig(BaseModel):
    tpm_threshold_pct: float = Field(85.0, ge=0.0, le=100.0)
    rpm_threshold_pct: float = Field(80.0, ge=0.0, le=100.0)
    chunk_size_threshold: int = Field(8000, ge=100, le=50000)
    recent_429_min_consecutive: int = Field(2, ge=1, le=10)
    status_rule_enabled: bool = True


class GuardConfig(BaseModel):
    warn_threshold: float = Field(0.80, ge=0.0, le=1.0)
    block_threshold: float = Field(0.95, ge=0.0, le=1.0)


class PacerConfig(BaseModel):
    burn_mode: str = Field("BALANCED")
    tpm_backpressure_pct: int = Field(90, ge=50, le=100)
    default_concurrency: int = Field(2, ge=1, le=16)


class CleanupConfig(BaseModel):
    plan_retention_days: int = Field(7, ge=1, le=365)
    stress_retention_days: int = Field(3, ge=1, le=90)
    history_retention_days: int = Field(30, ge=1, le=365)
    interval_hours: int = Field(6, ge=1, le=168)


class RuntimeConfigResponse(BaseModel):
    proxy_rules: ProxyRulesConfig
    guard: GuardConfig
    pacer: PacerConfig
    cleanup: CleanupConfig


class ProviderConfig(BaseModel):
    enabled: bool
    visible: bool
    label: str


class ProvidersConfig(BaseModel):
    providers: Dict[str, ProviderConfig]


class ConfigPatchRequest(BaseModel):
    proxy_rules: Optional[Dict[str, Any]] = None
    guard: Optional[Dict[str, Any]] = None
    pacer: Optional[Dict[str, Any]] = None
    cleanup: Optional[Dict[str, Any]] = None


class ConfigUpdateResponse(BaseModel):
    status: str
    applied: Dict[str, Any]


class PerformanceModeResponse(BaseModel):
    mode: str
    name: str
    multiplier: float
    description: str


class PerformanceModeRequest(BaseModel):
    mode: str = Field(..., pattern="^(stealth|balanced|apex)$")


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("", response_model=RuntimeConfigResponse)
async def get_config():
    """Get the current runtime configuration."""
    data = config_store.to_dict()
    return {
        "proxy_rules": data.get("proxy_rules", {}),
        "guard": data.get("guard", {}),
        "pacer": data.get("pacer", {}),
        "cleanup": data.get("cleanup", {}),
    }


@router.patch("", response_model=ConfigUpdateResponse)
async def patch_config(request: ConfigPatchRequest):
    """
    Partially update the runtime configuration.

    Only provided sections are modified; omitted sections keep current values.
    Changes are persisted immediately and take effect on the next decision.
    """
    patch: Dict[str, Any] = {}

    if request.proxy_rules is not None:
        pr = request.proxy_rules
        if "tpm_threshold_pct" in pr and not (0.0 <= pr["tpm_threshold_pct"] <= 100.0):
            raise HTTPException(status_code=422, detail="tpm_threshold_pct must be 0-100")
        if "rpm_threshold_pct" in pr and not (0.0 <= pr["rpm_threshold_pct"] <= 100.0):
            raise HTTPException(status_code=422, detail="rpm_threshold_pct must be 0-100")
        if "chunk_size_threshold" in pr and not (100 <= pr["chunk_size_threshold"] <= 50000):
            raise HTTPException(status_code=422, detail="chunk_size_threshold must be 100-50000")
        if "recent_429_min_consecutive" in pr and not (1 <= pr["recent_429_min_consecutive"] <= 10):
            raise HTTPException(status_code=422, detail="recent_429_min_consecutive must be 1-10")
        patch["proxy_rules"] = pr

    if request.guard is not None:
        g = request.guard
        if "warn_threshold" in g and not (0.0 <= g["warn_threshold"] <= 1.0):
            raise HTTPException(status_code=422, detail="warn_threshold must be 0-1")
        if "block_threshold" in g and not (0.0 <= g["block_threshold"] <= 1.0):
            raise HTTPException(status_code=422, detail="block_threshold must be 0-1")
        patch["guard"] = g

    if request.pacer is not None:
        p = request.pacer
        if "tpm_backpressure_pct" in p and not (50 <= p["tpm_backpressure_pct"] <= 100):
            raise HTTPException(status_code=422, detail="tpm_backpressure_pct must be 50-100")
        if "default_concurrency" in p and not (1 <= p["default_concurrency"] <= 16):
            raise HTTPException(status_code=422, detail="default_concurrency must be 1-16")
        patch["pacer"] = p

    if request.cleanup is not None:
        c = request.cleanup
        if "plan_retention_days" in c and not (1 <= c["plan_retention_days"] <= 365):
            raise HTTPException(status_code=422, detail="plan_retention_days must be 1-365")
        if "stress_retention_days" in c and not (1 <= c["stress_retention_days"] <= 90):
            raise HTTPException(status_code=422, detail="stress_retention_days must be 1-90")
        if "history_retention_days" in c and not (1 <= c["history_retention_days"] <= 365):
            raise HTTPException(status_code=422, detail="history_retention_days must be 1-365")
        if "interval_hours" in c and not (1 <= c["interval_hours"] <= 168):
            raise HTTPException(status_code=422, detail="interval_hours must be 1-168")
        patch["cleanup"] = c

    config_store.update(patch)

    return {"status": "updated", "applied": patch}


@router.post("/reset", response_model=RuntimeConfigResponse)
async def reset_config():
    """Reset all configuration to factory defaults."""
    config_store.reset()
    data = config_store.to_dict()
    return {
        "proxy_rules": data["proxy_rules"],
        "guard": data["guard"],
        "pacer": data["pacer"],
        "cleanup": data["cleanup"],
    }


@router.get("/performance-mode", response_model=PerformanceModeResponse)
async def get_performance_mode():
    """
    Get the current Hellcat Protocol performance mode.
    
    Modes:
      - stealth: 3.0x multiplier (maximum safety)
      - balanced: 1.15x multiplier (standard operation)
      - apex: 1.02x multiplier (maximum throughput)
    """
    return config_store.get_performance_mode_info()


@router.post("/performance-mode", response_model=PerformanceModeResponse)
async def set_performance_mode(request: PerformanceModeRequest):
    """
    Set the Hellcat Protocol performance mode.
    
    Changes take effect immediately for all subsequent requests.
    """
    try:
        config_store.set_performance_mode(request.mode)
        # Also update environment variable for backward compatibility
        import os
        os.environ["PEACOCK_PERF_MODE"] = request.mode
        return config_store.get_performance_mode_info()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/providers")
async def get_providers():
    """Get the current provider enable/visible state."""
    return config_store.providers


@router.patch("/providers/{gateway}")
async def patch_provider(gateway: str, request: ProviderConfig):
    """Update enable/visible/label for a single provider."""
    config_store.set_provider_state(
        gateway,
        enabled=request.enabled,
        visible=request.visible,
        label=request.label,
    )
    return config_store.providers.get(gateway)


@router.post("/providers/{gateway}/toggle")
async def toggle_provider(gateway: str):
    """Toggle a provider's enabled state."""
    current = config_store.providers.get(gateway, {})
    config_store.set_provider_state(gateway, enabled=not current.get("enabled", False))
    return config_store.providers.get(gateway)


@router.get("/effective-settings")
async def get_effective_settings():
    """
    Get all effective runtime settings including performance mode,
    guard thresholds, proxy rules, and pacer configuration.
    
    This endpoint shows the actual values being used by the system.
    """
    from app.config import PERFORMANCE_MODES
    
    perf_mode = config_store.performance_mode
    perf_cfg = PERFORMANCE_MODES.get(perf_mode, PERFORMANCE_MODES["balanced"])
    
    return {
        "performance_mode": {
            "active": perf_mode,
            "name": perf_cfg["name"],
            "multiplier": perf_cfg["multiplier"],
        },
        "guard": {
            "warn_threshold": config_store.guard["warn_threshold"],
            "block_threshold": config_store.guard["block_threshold"],
        },
        "proxy_rules": config_store.proxy_rules,
        "pacer": {
            "burn_mode": config_store.burn_mode,
            "tpm_backpressure_pct": config_store.pacer["tpm_backpressure_pct"],
            "default_concurrency": config_store.pacer["default_concurrency"],
        },
        "cleanup": config_store.cleanup,
        "providers": config_store.providers,
    }
