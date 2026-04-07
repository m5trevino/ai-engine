"""
PEACOCK ENGINE - Documentation Routes
Endpoint discovery and API documentation.
"""

from fastapi import APIRouter
from typing import List, Dict, Any

router = APIRouter()

# Endpoint registry - describes all available endpoints
ENDPOINTS: List[Dict[str, Any]] = [
    {
        "path": "/v1/chat",
        "method": "POST",
        "name": "Generic Chat",
        "description": "Unified endpoint for chatting with any model from any gateway. Supports file payloads and multiple output formats.",
        "for_apps": ["CLI tools", "Generic integrations", "New applications"],
        "payload_example": {
            "model": "gemini-2.0-flash-lite",
            "prompt": "Your prompt here",
            "files": ["/path/to/file.py"],
            "format": "text",
            "temp": 0.7
        },
        "response_example": {
            "content": "Response text",
            "model": "gemini-2.0-flash-lite",
            "gateway": "google",
            "key_used": "PEACOCK_MAIN",
            "format": "text",
            "usage": {"prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60},
            "duration_ms": 1240
        }
    },
    {
        "path": "/v1/chat/models",
        "method": "GET",
        "name": "List Chat Models",
        "description": "Get all available models grouped by gateway for the chat endpoint.",
        "for_apps": ["CLI tools", "Model selectors"],
        "payload_example": None,
        "response_example": {
            "google": [{"id": "gemini-2.0-flash-lite", "tier": "free", "note": "..."}],
            "groq": [{"id": "llama-3.1-8b-instant", "tier": "free", "note": "..."}]
        }
    },
    {
        "path": "/v1/strike",
        "method": "POST",
        "name": "Legacy Strike",
        "description": "Original strike endpoint. Supports structured output (EagleScaffold). Maintained for backward compatibility.",
        "for_apps": ["Peacock HUD V21", "Legacy clients"],
        "payload_example": {
            "modelId": "gemini-2.0-flash-lite",
            "prompt": "Your prompt here",
            "temp": 0.7,
            "format_mode": None
        },
        "response_example": {
            "content": "Response text",
            "keyUsed": "PEACOCK_MAIN",
            "usage": {"prompt_tokens": 10, "completion_tokens": 50, "total_tokens": 60}
        }
    },
    {
        "path": "/v1/payload-strike",
        "method": "POST",
        "name": "Payload Strike",
        "description": "Multi-file context strikes. Recursively includes files from directories.",
        "for_apps": ["Code review tools", "Batch processors", "Document analyzers"],
        "payload_example": {
            "modelId": "gemini-2.0-flash-lite",
            "prompt": "Review this code",
            "files": ["/path/to/project"],
            "temp": 0.7
        },
        "response_example": {
            "content": "Code review results...",
            "keyUsed": "PEACOCK_MAIN",
            "usage": {"prompt_tokens": 1000, "completion_tokens": 500, "total_tokens": 1500}
        }
    },
    {
        "path": "/v1/striker/files",
        "method": "GET",
        "name": "List Striker Files",
        "description": "List files available for batch processing in the Striker system.",
        "for_apps": ["MissionVault", "Document processors"]
    },
    {
        "path": "/v1/striker/execute",
        "method": "POST",
        "name": "Execute Striker Batch",
        "description": "Batch file processing with metadata extraction. Supports pause/resume.",
        "for_apps": ["MissionVault", "Document processors"],
        "payload_example": {
            "files": ["/path/to/file1.md", "/path/to/file2.md"],
            "prompt": "Extract metadata",
            "modelId": "gemini-2.0-flash-lite",
            "delay": 5,
            "throttle": 1.0
        }
    },
    {
        "path": "/v1/striker/status",
        "method": "GET",
        "name": "Striker Status",
        "description": "Get current status of batch processing (telemetry, progress, etc).",
        "for_apps": ["MissionVault", "Monitoring tools"]
    },
    {
        "path": "/v1/striker/pause",
        "method": "POST",
        "name": "Pause Striker",
        "description": "Pause an ongoing batch processing job.",
        "for_apps": ["MissionVault"]
    },
    {
        "path": "/v1/striker/resume",
        "method": "POST",
        "name": "Resume Striker",
        "description": "Resume a paused batch processing job.",
        "for_apps": ["MissionVault"]
    },
    {
        "path": "/v1/profile/syndicate",
        "method": "POST",
        "name": "Syndicate Strike",
        "description": "Target a specific API key account for testing or specialized routing.",
        "for_apps": ["Syndicate testing", "Key validation", "Account-specific routing"],
        "payload_example": {
            "modelId": "gemini-2.0-flash-lite",
            "prompt": "Test prompt",
            "target_account": "PEACOCK_MAIN",
            "temp": 0.7
        }
    },
    {
        "path": "/v1/keys",
        "method": "GET",
        "name": "List Keys",
        "description": "List all available API keys (account names only, no secrets).",
        "for_apps": ["Key management", "Monitoring"]
    },
    {
        "path": "/v1/keys/usage",
        "method": "GET",
        "name": "Key Usage Stats",
        "description": "Get detailed usage statistics for all API keys including last used timestamp.",
        "for_apps": ["Key management", "Usage monitoring", "CLI tools"],
        "response_example": {
            "usage": {
                "groq": [{"account": "mtrev2024", "last_used": "2026-03-19T14:32:01Z", "usage_count": 42}]
            },
            "pools": {
                "groq": {"total_keys": 15, "current_pointer": 3}
            }
        }
    },
    {
        "path": "/v1/keys/usage/{gateway}",
        "method": "GET",
        "name": "Gateway Key Usage",
        "description": "Get usage statistics for a specific gateway.",
        "for_apps": ["Key management"]
    },
    {
        "path": "/v1/models",
        "method": "GET",
        "name": "List Models",
        "description": "Get all available models from the registry with tiers and rate limits.",
        "for_apps": ["All clients"]
    },
    {
        "path": "/v1/fs/ammo",
        "method": "GET",
        "name": "List Ammo",
        "description": "List files from the ammo directory.",
        "for_apps": ["Peacock HUD", "File management"]
    },
    {
        "path": "/v1/fs/ammo/{file_name}",
        "method": "GET",
        "name": "Get Ammo File",
        "description": "Read a specific ammo file.",
        "for_apps": ["Peacock HUD"]
    },
    {
        "path": "/v1/fs/prompts/{phase}",
        "method": "GET",
        "name": "List Prompts",
        "description": "List prompts for a specific phase.",
        "for_apps": ["Peacock HUD"]
    },
    {
        "path": "/v1/fs/prompts/{phase}",
        "method": "POST",
        "name": "Save Prompt",
        "description": "Save a prompt for a specific phase.",
        "for_apps": ["Peacock HUD"]
    },
    {
        "path": "/health",
        "method": "GET",
        "name": "Health Check",
        "description": "Get system health status including key pool integrity.",
        "for_apps": ["Monitoring", "Load balancers"]
    }
]


@router.get("/endpoints")
async def get_endpoints():
    """
    Get all available endpoints with descriptions and examples.
    
    This endpoint is designed to help AI bots and developers understand
    the PEACOCK ENGINE API without guessing.
    """
    return {
        "engine": "PEACOCK ENGINE V3",
        "version": "3.0.0",
        "description": "Multi-gateway AI orchestration engine",
        "gateways": ["groq", "google", "deepseek", "mistral"],
        "endpoints": ENDPOINTS
    }


@router.get("/endpoints/by-app/{app_name}")
async def get_endpoints_by_app(app_name: str):
    """Get endpoints recommended for a specific app type."""
    app_lower = app_name.lower()
    
    # Filter endpoints that mention this app
    matching = []
    for ep in ENDPOINTS:
        for_apps = [a.lower() for a in ep.get("for_apps", [])]
        if app_lower in for_apps or any(app_lower in a for a in for_apps):
            matching.append(ep)
    
    if not matching:
        return {
            "message": f"No specific endpoints found for '{app_name}'",
            "suggestion": "Try using /v1/chat for generic integration",
            "all_endpoints": f"/v1/docs/endpoints"
        }
    
    return {
        "app": app_name,
        "recommended_endpoints": matching
    }


@router.get("/integration-guide")
async def get_integration_guide():
    """Get a quick integration guide for new applications."""
    return {
        "title": "PEACOCK ENGINE Integration Guide",
        "steps": [
            {
                "step": 1,
                "title": "Discover Models",
                "action": "GET /v1/chat/models",
                "description": "Get list of available models grouped by gateway"
            },
            {
                "step": 2,
                "title": "Make a Request",
                "action": "POST /v1/chat",
                "description": "Send prompt to any model",
                "example": {
                    "model": "gemini-2.0-flash-lite",
                    "prompt": "Hello, world!",
                    "format": "text"
                }
            },
            {
                "step": 3,
                "title": "Monitor Usage",
                "action": "GET /v1/keys/usage",
                "description": "Track API key usage and rotation"
            }
        ],
        "recommendations": {
            "new_apps": "Use /v1/chat - it's the most flexible and future-proof",
            "legacy_support": "/v1/strike is maintained but deprecated for new apps",
            "batch_processing": "Use /v1/striker/* for document batch processing",
            "file_analysis": "Use /v1/payload-strike with file paths"
        }
    }
