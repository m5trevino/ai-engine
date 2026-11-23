from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
import time
from app.core.striker import execute_strike
from app.config import MODEL_REGISTRY
from app.core.key_manager import GroqPool, GooglePool, DeepSeekPool, MistralPool

router = APIRouter()

class AuditRequest(BaseModel):
    model_id: Optional[str] = None
    gateway: Optional[str] = None
    key_label: Optional[str] = None
    test_all: bool = False

class AuditResponse(BaseModel):
    status: str
    results: List[Dict]
    timestamp: float

@router.post("/model")
async def audit_model(request: AuditRequest):
    """Audit a single model or a gateway's models."""
    targets = []
    if request.model_id:
        targets = [m for m in MODEL_REGISTRY if m.id == request.model_id]
    elif request.gateway:
        targets = [m for m in MODEL_REGISTRY if m.gateway == request.gateway]
    elif request.test_all:
        targets = [m for m in MODEL_REGISTRY if m.status == "active"]
    
    if not targets:
        raise HTTPException(status_code=404, detail="No models found for audit criteria")

    results = []
    for m in targets:
        # Avoid auditing non-text models for generic health check
        if any(x in m.id for x in ["embedding", "whisper", "lyria", "veo"]):
            results.append({"id": m.id, "status": "skipped", "note": "Specialized model"})
            continue
            
        try:
            # Quick health check strike
            start = time.time()
            res = await execute_strike(
                gateway=m.gateway,
                model_id=m.id,
                prompt="respond with 'OK'",
                temp=0.0,
                is_manual=True,
                timeout=30
            )
            duration = round((time.time() - start) * 1000, 2)
            results.append({
                "id": m.id, 
                "status": "online", 
                "tag": res.get("tag"), 
                "latency_ms": duration
            })
        except Exception as e:
            results.append({
                "id": m.id, 
                "status": "offline", 
                "error": str(e)[:100]
            })

    return AuditResponse(status="complete", results=results, timestamp=time.time())

@router.post("/key")
async def audit_key(request: AuditRequest):
    """Audit a specific key or all keys in a pool."""
    pools = {
        "groq": GroqPool,
        "google": GooglePool,
        "deepseek": DeepSeekPool,
        "mistral": MistralPool
    }
    
    # Probe models (cheapest/fastest for each gateway)
    probes = {
        "groq": "llama-3.1-8b-instant",
        "google": "gemini-2.0-flash",
        "deepseek": "deepseek-chat",
        "mistral": "mistral-large-latest"
    }

    results = []
    
    target_pools = [request.gateway] if request.gateway and request.gateway in pools else pools.keys()
    
    for gw in target_pools:
        pool = pools[gw]
        probe_model = probes.get(gw)
        
        if not pool.deck:
            continue
            
        for asset in pool.deck:
            # If a specific key_label is requested, skip others
            if request.key_label and asset.label != request.key_label:
                continue
                
            try:
                start = time.time()
                res = await execute_strike(
                    gateway=gw,
                    model_id=probe_model,
                    prompt="ping",
                    temp=0.0,
                    is_manual=True,
                    timeout=20,
                    key_override=asset.key
                )
                duration = round((time.time() - start) * 1000, 2)
                results.append({
                    "gateway": gw,
                    "label": asset.label,
                    "status": "online",
                    "latency_ms": duration,
                    "tag": res.get("tag")
                })
            except Exception as e:
                results.append({
                    "gateway": gw,
                    "label": asset.label,
                    "status": "offline",
                    "error": str(e)[:100]
                })

    return AuditResponse(status="complete", results=results, timestamp=time.time())

@router.get("/status")
async def get_system_health():
    """Summary of all registries and pools."""
    return {
        "models": {
            "total": len(MODEL_REGISTRY),
            "gateways": list(set(m.gateway for m in MODEL_REGISTRY))
        },
        "pools": {
            "groq": len(GroqPool.deck),
            "google": len(GooglePool.deck),
            "deepseek": len(DeepSeekPool.deck),
            "mistral": len(MistralPool.deck)
        },
        "timestamp": time.time()
    }
