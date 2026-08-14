"""
PEACOCK ENGINE - Keys Routes
API key management and usage tracking.
"""

from fastapi import APIRouter
from app.core.key_manager import list_pools
from app.core.config_store import config_store
from app.db.database import KeyUsageDB
from app.utils.formatter import CLIFormatter

router = APIRouter()


@router.get("")
async def get_keys():
    """Get all available keys (without the actual key values)."""
    result = {}
    for gateway, pool in list_pools().items():
        if not config_store.is_provider_visible(gateway):
            continue
        result[gateway] = {
            "pointer": pool.pointer,
            "keys": [a.account for a in pool.deck]
        }
    return result


@router.get("/usage")
async def get_keys_usage():
    """
    Get detailed usage statistics for all API keys.
    Includes last used timestamp, usage count, and token totals.
    """
    usage_data = KeyUsageDB.get_all_usage()

    pools = {}
    for gateway, pool in list_pools().items():
        if not config_store.is_provider_visible(gateway):
            continue
        pools[gateway] = {
            "total_keys": len(pool.deck),
            "current_pointer": pool.pointer,
            "accounts": [a.account for a in pool.deck]
        }

    return {
        "usage": usage_data,
        "pools": pools,
    }


@router.get("/usage/{gateway}")
async def get_gateway_usage(gateway: str):
    """Get usage statistics for a specific gateway."""
    gateway_lower = gateway.lower()

    pool = list_pools().get(gateway_lower)
    if not pool:
        return {"error": f"Invalid gateway: {gateway_lower}"}

    if not config_store.is_provider_visible(gateway_lower):
        return {"error": f"Provider {gateway_lower} is not visible"}

    usage = KeyUsageDB.get_gateway_usage(gateway_lower)

    return {
        "gateway": gateway_lower,
        "usage": usage,
        "pool": {
            "total_keys": len(pool.deck),
            "current_pointer": pool.pointer,
            "accounts": [a.account for a in pool.deck]
        }
    }
