"""
Enhanced Model API for WebUI
Supports: registry view, freeze/unfreeze, test, set default
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict
import time
import asyncio

from app.config import MODEL_REGISTRY, FROZEN_IDS, FROZEN_FILE
import json

router = APIRouter()


class ModelDetail(BaseModel):
    """Full model details for WebUI."""
    id: str
    gateway: str
    tier: str
    status: str
    note: str
    rpm: Optional[int] = None
    tpm: Optional[int] = None
    rpd: Optional[int] = None
    context_window: Optional[int] = None
    input_price_1m: float = 0.0
    output_price_1m: float = 0.0


class ModelListResponse(BaseModel):
    """Model list with gateway grouping."""
    models: List[ModelDetail]
    by_gateway: Dict[str, List[ModelDetail]]
    frozen_count: int
    active_count: int


class ModelTestResult(BaseModel):
    """Result of testing a model."""
    model_id: str
    working: bool
    latency_ms: float
    error: Optional[str] = None
    tokens_used: int = 0


class FreezeRequest(BaseModel):
    """Freeze model request."""
    reason: Optional[str] = "manual"


@router.get("/registry", response_model=ModelListResponse)
async def get_model_registry():
    """
    Get all models for the Model Registry screen.
    Includes full details grouped by gateway.
    """
    models = []
    by_gateway = {}
    
    for m in MODEL_REGISTRY:
        detail = ModelDetail(
            id=m.id,
            gateway=m.gateway,
            tier=m.tier,
            status=m.status,
            note=m.note,
            rpm=m.rpm,
            tpm=m.tpm,
            rpd=m.rpd,
            context_window=m.context_window,
            input_price_1m=m.input_price_1m,
            output_price_1m=m.output_price_1m
        )
        models.append(detail)
        
        if m.gateway not in by_gateway:
            by_gateway[m.gateway] = []
        by_gateway[m.gateway].append(detail)
    
    return ModelListResponse(
        models=models,
        by_gateway=by_gateway,
        frozen_count=len([m for m in models if m.status == "frozen"]),
        active_count=len([m for m in models if m.status == "active"])
    )


@router.get("/{model_id}", response_model=ModelDetail)
async def get_model_details(model_id: str):
    """Get details for a specific model."""
    model = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    return ModelDetail(
        id=model.id,
        gateway=model.gateway,
        tier=model.tier,
        status=model.status,
        note=model.note,
        rpm=model.rpm,
        tpm=model.tpm,
        rpd=model.rpd,
        context_window=model.context_window,
        input_price_1m=model.input_price_1m,
        output_price_1m=model.output_price_1m
    )


@router.post("/{model_id}/test", response_model=ModelTestResult)
async def test_model(model_id: str):
    """
    Test a model by running a simple inference.
    Returns latency and success status.
    """
    from app.config import MODEL_REGISTRY
    from app.core.key_manager import GooglePool, GroqPool, DeepSeekPool, MistralPool
    
    model = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    if model.status == "frozen":
        raise HTTPException(status_code=400, detail=f"Model {model_id} is frozen")
    
    # Get appropriate key pool
    pool = None
    if model.gateway == "groq":
        pool = GroqPool
    elif model.gateway == "google":
        pool = GooglePool
    elif model.gateway == "deepseek":
        pool = DeepSeekPool
    elif model.gateway == "mistral":
        pool = MistralPool
    
    if not pool or not pool.deck:
        raise HTTPException(status_code=503, detail=f"No keys available for {model.gateway}")
    
    # Test with quick strike
    start = time.time()
    test_prompt = "Say 'TEST_OK' and nothing else."
    
    try:
        from app.core.striker import execute_strike
        result = await execute_strike(
            gateway=model.gateway,
            model_id=model_id,
            prompt=test_prompt,
            temp=0.1,
            is_manual=False
        )
        
        latency = (time.time() - start) * 1000
        usage = result.get("usage", {})
        
        return ModelTestResult(
            model_id=model_id,
            working=True,
            latency_ms=latency,
            tokens_used=usage.get("total_tokens", 0)
        )
        
    except Exception as e:
        latency = (time.time() - start) * 1000
        return ModelTestResult(
            model_id=model_id,
            working=False,
            latency_ms=latency,
            error=str(e)[:200]
        )


@router.post("/{model_id}/freeze")
async def freeze_model(model_id: str, request: Optional[FreezeRequest] = None):
    """Freeze a model (mark as unavailable)."""
    model = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    if model_id in FROZEN_IDS:
        return {"message": f"Model {model_id} already frozen"}
    
    FROZEN_IDS.append(model_id)
    model.status = "frozen"
    
    # Persist to file
    try:
        FROZEN_FILE.write_text(json.dumps(FROZEN_IDS))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist freeze: {e}")
    
    reason = request.reason if request else "manual"
    return {
        "message": f"Model {model_id} frozen",
        "reason": reason,
        "frozen_at": time.time()
    }


@router.post("/{model_id}/unfreeze")
async def unfreeze_model(model_id: str):
    """Unfreeze a model (mark as available)."""
    model = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    if model_id not in FROZEN_IDS:
        return {"message": f"Model {model_id} was not frozen"}
    
    FROZEN_IDS.remove(model_id)
    model.status = "active"
    
    # Persist to file
    try:
        FROZEN_FILE.write_text(json.dumps(FROZEN_IDS))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist unfreeze: {e}")
    
    return {"message": f"Model {model_id} unfrozen"}


@router.post("/{model_id}/default")
async def set_default_model(model_id: str):
    """Set a model as the default for new conversations."""
    model = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    if model.status == "frozen":
        raise HTTPException(status_code=400, detail=f"Cannot set frozen model as default")
    
    # Store default in a simple config file
    config_file = Path("default_model.txt")
    config_file.write_text(model_id)
    
    return {"message": f"Model {model_id} set as default"}


@router.get("/{model_id}/traffic-logs")
async def get_model_traffic_logs(model_id: str, limit: int = 10):
    """
    Get recent traffic logs for a model.
    Returns last N requests with timing info.
    """
    # This would ideally query from database
    # For now, return mock data structure
    return {
        "model_id": model_id,
        "logs": [
            {
                "timestamp": time.time() - i * 60,
                "request_id": f"req_{i}",
                "status": "success",
                "latency_ms": 1200,
                "tokens": 150
            }
            for i in range(limit)
        ]
    }
