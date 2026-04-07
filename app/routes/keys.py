"""
PEACOCK ENGINE - Keys Routes
API key management and usage tracking.
"""

from fastapi import APIRouter
from app.core.key_manager import GroqPool, GooglePool, DeepSeekPool, MistralPool
from app.db.database import KeyUsageDB
from app.utils.formatter import CLIFormatter

router = APIRouter()


@router.get("")
async def get_keys():
    """Get all available keys (without the actual key values)."""
    return {
        "groq": {
            "pointer": GroqPool.pointer,
            "keys": [a.account for a in GroqPool.deck]
        },
        "google": {
            "pointer": GooglePool.pointer,
            "keys": [a.account for a in GooglePool.deck]
        },
        "deepseek": {
            "pointer": DeepSeekPool.pointer,
            "keys": [a.account for a in DeepSeekPool.deck]
        },
        "mistral": {
            "pointer": MistralPool.pointer,
            "keys": [a.account for a in MistralPool.deck]
        }
    }


@router.get("/usage")
async def get_keys_usage():
    """
    Get detailed usage statistics for all API keys.
    Includes last used timestamp, usage count, and token totals.
    """
    usage_data = KeyUsageDB.get_all_usage()
    
    # Also include current pool status
    return {
        "usage": usage_data,
        "pools": {
            "groq": {
                "total_keys": len(GroqPool.deck),
                "current_pointer": GroqPool.pointer,
                "accounts": [a.account for a in GroqPool.deck]
            },
            "google": {
                "total_keys": len(GooglePool.deck),
                "current_pointer": GooglePool.pointer,
                "accounts": [a.account for a in GooglePool.deck]
            },
            "deepseek": {
                "total_keys": len(DeepSeekPool.deck),
                "current_pointer": DeepSeekPool.pointer,
                "accounts": [a.account for a in DeepSeekPool.deck]
            },
            "mistral": {
                "total_keys": len(MistralPool.deck),
                "current_pointer": MistralPool.pointer,
                "accounts": [a.account for a in MistralPool.deck]
            }
        }
    }


@router.get("/usage/{gateway}")
async def get_gateway_usage(gateway: str):
    """Get usage statistics for a specific gateway."""
    gateway_lower = gateway.lower()
    
    valid_gateways = ["groq", "google", "deepseek", "mistral"]
    if gateway_lower not in valid_gateways:
        return {"error": f"Invalid gateway. Must be one of: {valid_gateways}"}
    
    usage = KeyUsageDB.get_gateway_usage(gateway_lower)
    
    # Get pool info
    pool_map = {
        "groq": GroqPool,
        "google": GooglePool,
        "deepseek": DeepSeekPool,
        "mistral": MistralPool
    }
    pool = pool_map[gateway_lower]
    
    return {
        "gateway": gateway_lower,
        "usage": usage,
        "pool": {
            "total_keys": len(pool.deck),
            "current_pointer": pool.pointer,
            "accounts": [a.account for a in pool.deck]
        }
    }
