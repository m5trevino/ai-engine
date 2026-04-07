"""
PEACOCK ENGINE - Token & Cost API
Exposes token counting and cost estimation to the WebUI.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.utils.token_counter import PeacockTokenCounter
from app.utils.formatter import CLIFormatter
from app.config import MODEL_REGISTRY

router = APIRouter()

class TokenCountRequest(BaseModel):
    model: str
    prompt: str
    files: Optional[List[str]] = []

class TokenCountResponse(BaseModel):
    model: str
    prompt_tokens: int
    completion_tokens_est: int
    total_tokens_est: int
    cost_est: float
    limit_tpm: Optional[int]

@router.post("/count")
async def count_tokens(request: TokenCountRequest):
    """
    Count tokens for a given prompt and model.
    Provides real-time estimation for the WebUI.
    """
    try:
        prompt_tokens = PeacockTokenCounter.count_prompt_tokens(
            request.model, request.prompt, request.files or []
        )
        
        # Simple estimation for response (assuming 100 tokens as baseline)
        completion_tokens_est = 100 
        total_tokens_est = prompt_tokens + completion_tokens_est
        
        cost_est = PeacockTokenCounter.calculate_cost(
            request.model, prompt_tokens, completion_tokens_est
        )
        
        limit_tpm = PeacockTokenCounter.get_token_limit(request.model)
        
        return TokenCountResponse(
            model=request.model,
            prompt_tokens=prompt_tokens,
            completion_tokens_est=completion_tokens_est,
            total_tokens_est=total_tokens_est,
            cost_est=cost_est,
            limit_tpm=limit_tpm
        )
    except Exception as e:
        CLIFormatter.error(f"Token count failure: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/models")
async def list_models_with_token_info():
    """List all active models with their context windows and limits."""
    return {
        "models": [
            {
                "id": m.id,
                "gateway": m.gateway,
                "context_window": m.context_window,
                "tpm": m.tpm,
                "rpm": m.rpm,
                "rpd": m.rpd,
                "input_price": m.input_price_1m,
                "output_price": m.output_price_1m
            }
            for m in MODEL_REGISTRY if m.status != "frozen"
        ]
    }
