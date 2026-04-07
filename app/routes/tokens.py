"""
PEACOCK ENGINE - Token Counting API
Provides token counting and cost estimation endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.config import MODEL_REGISTRY
from app.utils.gemini_token_counter import GeminiTokenCounter
from app.utils.groq_token_counter import GroqTokenCounter

router = APIRouter()

# Initialize counters
gemini_counter = GeminiTokenCounter()
groq_counter = GroqTokenCounter()


class TokenCountRequest(BaseModel):
    """Request to count tokens."""
    text: str
    model: Optional[str] = None
    gateway: Optional[str] = None


class TokenCountResponse(BaseModel):
    """Response with token count."""
    token_count: int
    model: str
    gateway: str
    estimated_cost_usd: float


class TokenCountFileRequest(BaseModel):
    """Request to count tokens in a file."""
    file_path: str
    model: Optional[str] = None


def get_gateway_for_model(model_id: str) -> str:
    """Determine gateway from model ID."""
    model = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if model:
        return model.gateway
    # Fallback detection
    if "gemini" in model_id.lower():
        return "google"
    elif "llama" in model_id.lower() or "mixtral" in model_id.lower():
        return "groq"
    elif "deepseek" in model_id.lower():
        return "deepseek"
    elif "mistral" in model_id.lower():
        return "mistral"
    return "groq"  # Default


def estimate_cost(model_id: str, token_count: int) -> float:
    """Estimate cost in USD based on model pricing."""
    model = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if not model:
        # Default pricing
        return (token_count / 1000) * 0.002
    
    # Use input price from registry
    price_per_1m = model.input_price_1m
    return (token_count / 1_000_000) * price_per_1m


@router.post("/count", response_model=TokenCountResponse)
async def count_tokens(request: TokenCountRequest):
    """
    Count tokens for given text.
    Automatically detects gateway from model if not provided.
    """
    # Determine model and gateway
    model_id = request.model or "gemini-2.0-flash-lite"
    gateway = request.gateway or get_gateway_for_model(model_id)
    
    # Count tokens based on gateway
    try:
        if gateway == "google":
            token_count = gemini_counter.count_tokens_offline(request.text, model_id)
        elif gateway == "groq":
            token_count = groq_counter.count_tokens_in_prompt(request.text, model_id)
        elif gateway in ["deepseek", "mistral"]:
            # Use cl100k_base approximation
            token_count = groq_counter.count_tokens_in_prompt(request.text, "llama-3.3-70b-versatile")
        else:
            # Default approximation
            token_count = len(request.text.split()) * 1.3
            token_count = int(token_count)
        
        # Calculate estimated cost
        cost = estimate_cost(model_id, token_count)
        
        return TokenCountResponse(
            token_count=token_count,
            model=model_id,
            gateway=gateway,
            estimated_cost_usd=round(cost, 6)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token counting failed: {str(e)}")


@router.get("/models/{model_id}")
async def get_model_token_info(model_id: str):
    """
    Get token counting information for a specific model.
    Returns context window, pricing, etc.
    """
    model = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
    
    return {
        "model_id": model.id,
        "gateway": model.gateway,
        "context_window": model.context_window,
        "input_price_per_1m": model.input_price_1m,
        "output_price_per_1m": model.output_price_1m,
        "rpm": model.rpm,
        "tpm": model.tpm,
        "rpd": model.rpd,
        "status": model.status
    }


@router.get("/models")
async def list_models_with_token_info():
    """
    List all models with token counting information.
    """
    models = []
    for m in MODEL_REGISTRY:
        if m.status != "frozen":
            models.append({
                "model_id": m.id,
                "gateway": m.gateway,
                "context_window": m.context_window,
                "input_price_per_1m": m.input_price_1m,
                "output_price_per_1m": m.output_price_1m,
                "rpm": m.rpm,
                "tpm": m.tpm,
                "status": m.status
            })
    return {"models": models}
