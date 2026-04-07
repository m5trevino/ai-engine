from fastapi import APIRouter
from app.config import MODEL_REGISTRY

router = APIRouter()

@router.get("")
async def get_models():
    return MODEL_REGISTRY
