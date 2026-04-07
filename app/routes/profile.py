from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.core.striker import execute_precision_strike
from app.config import MODEL_REGISTRY

router = APIRouter()

class SyndicateStrikeRequest(BaseModel):
    modelId: str
    prompt: str
    target_account: str
    temp: Optional[float] = 0.7

@router.post("/syndicate")
async def syndicate_strike(request: SyndicateStrikeRequest):
    print(f"[🛡️ PROFILE STRIKE] MODEL: {request.modelId} | TARGET: {request.target_account}")
    
    try:
        # 1. Resolve Gateway
        model_config = next((m for m in MODEL_REGISTRY if m.id == request.modelId), None)
        if not model_config:
            raise HTTPException(status_code=400, detail=f"Unknown Model ID: {request.modelId}")
        
        # 2. Execute Precision Strike
        result = await execute_precision_strike(
            gateway=model_config.gateway,
            model_id=request.modelId,
            prompt=request.prompt,
            target_account=request.target_account,
            temp=request.temp
        )
        return result
        
    except Exception as e:
        error_msg = str(e)
        if "not found in" in error_msg:
            # Handle the specific "account not found" error with 404/400
            print(f"[⚠️ PRECISION FAIL] {error_msg}")
            raise HTTPException(status_code=404, detail=error_msg)
            
        print(f"[❌ PROFILE STRIKE ERROR] {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
