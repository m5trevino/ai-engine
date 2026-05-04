"""
Dynamic model registration endpoint.
Allows runtime addition of models to the registry via a persistent JSON file.
"""

import json
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal

from app.config import MODEL_REGISTRY, ModelConfig

router = APIRouter()

DYNAMIC_MODELS_PATH = os.path.join(os.path.dirname(__file__), "..", "dynamic_models.json")

class RegisterModelRequest(BaseModel):
    id: str
    gateway: Literal['groq', 'google', 'deepseek', 'mistral']
    tier: Literal['free', 'cheap', 'expensive']
    note: Optional[str] = ""
    rpm: Optional[int] = None
    rpd: Optional[int] = None
    tpm: Optional[int] = None
    context_window: Optional[int] = None
    input_price_1m: Optional[float] = None
    output_price_1m: Optional[float] = None
    status: Optional[Literal['active', 'frozen', 'deprecated']] = 'active'

@router.post("/register")
async def register_model(req: RegisterModelRequest):
    # Check for duplicates
    if any(m.id == req.id for m in MODEL_REGISTRY):
        raise HTTPException(status_code=400, detail=f"Model '{req.id}' already exists")

    new_model = ModelConfig(
        id=req.id,
        gateway=req.gateway,
        tier=req.tier,
        note=req.note or "",
        rpm=req.rpm,
        rpd=req.rpd,
        tpm=req.tpm,
        context_window=req.context_window,
        input_price_1m=req.input_price_1m,
        output_price_1m=req.output_price_1m,
        status=req.status or 'active'
    )

    # Append to in-memory registry
    MODEL_REGISTRY.append(new_model)

    # Persist to JSON
    existing = []
    if os.path.exists(DYNAMIC_MODELS_PATH):
        with open(DYNAMIC_MODELS_PATH, 'r') as f:
            existing = json.load(f)

    existing.append({
        "id": req.id,
        "gateway": req.gateway,
        "tier": req.tier,
        "note": req.note or "",
        "rpm": req.rpm,
        "rpd": req.rpd,
        "tpm": req.tpm,
        "context_window": req.context_window,
        "input_price_1m": req.input_price_1m,
        "output_price_1m": req.output_price_1m,
        "status": req.status or 'active'
    })

    with open(DYNAMIC_MODELS_PATH, 'w') as f:
        json.dump(existing, f, indent=2)

    return {"status": "ok", "model": req.id}

@router.delete("/register/{model_id}")
async def unregister_model(model_id: str):
    global MODEL_REGISTRY
    original_len = len(MODEL_REGISTRY)
    MODEL_REGISTRY = [m for m in MODEL_REGISTRY if m.id != model_id]
    if len(MODEL_REGISTRY) == original_len:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")

    if os.path.exists(DYNAMIC_MODELS_PATH):
        with open(DYNAMIC_MODELS_PATH, 'r') as f:
            existing = json.load(f)
        existing = [m for m in existing if m.get('id') != model_id]
        with open(DYNAMIC_MODELS_PATH, 'w') as f:
            json.dump(existing, f, indent=2)

    return {"status": "ok", "deleted": model_id}
