from fastapi import APIRouter
from app.config import MODEL_REGISTRY
from app.core.config_store import config_store

router = APIRouter()


def _model_sort_key(m):
    """Sort by explicit index first, then by context window desc, then by name."""
    idx = m.index if m.index is not None else 9999
    ctx = -(m.context_window or 0)
    return (idx, ctx, m.id)


def _model_to_dict(m):
    return {
        "id": m.id,
        "gateway": m.gateway,
        "tier": m.tier,
        "status": m.status,
        "note": m.note,
        "rpm": m.rpm,
        "tpm": m.tpm,
        "rpd": m.rpd,
        "context_window": m.context_window,
        "input_price_1m": m.input_price_1m,
        "output_price_1m": m.output_price_1m,
        "tools_supported": m.tools_supported,
        "index": m.index,
        "base_url": m.base_url,
        "display_name": m.display_name,
    }


@router.get("")
async def get_models(include_frozen: bool = False, only_enabled_providers: bool = True):
    """
    Get all models from the registry, sorted by priority index.

    Args:
        include_frozen: If True, include frozen and deprecated models
        only_enabled_providers: If True, exclude models from disabled/hidden providers

    Returns:
        List of model configurations grouped by gateway
    """
    models = []
    by_gateway = {}
    for m in sorted(MODEL_REGISTRY, key=_model_sort_key):
        if not include_frozen and m.status in ("frozen", "deprecated"):
            continue
        if only_enabled_providers and not config_store.is_provider_enabled(m.gateway):
            continue
        detail = _model_to_dict(m)
        models.append(detail)
        by_gateway.setdefault(m.gateway, []).append(detail)
    return {
        "models": models,
        "count": len(models),
        "by_gateway": by_gateway,
        "providers": config_store.providers,
    }
