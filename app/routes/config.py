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


class ConfigPatchRequest(BaseModel):
    proxy_rules: Optional[Dict[str, Any]] = None
    guard: Optional[Dict[str, Any]] = None
    pacer: Optional[Dict[str, Any]] = None
    cleanup: Optional[Dict[str, Any]] = None


class ConfigUpdateResponse(BaseModel):
    status: str
    applied: Dict[str, Any]


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
