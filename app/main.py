"""
PEACOCK ENGINE V3 - FastAPI Application
Multi-gateway AI orchestration engine.
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

# Import all route modules
from app.routes.strike import router as strike_router
from app.routes.models import router as models_router
from app.routes.fs import router as fs_router
from app.routes.keys import router as keys_router
from app.routes.striker import router as striker_router
from app.routes.payload_strike import router as payload_strike_router
from app.routes.proxy_control import router as proxy_control_router
from app.routes.profile import router as profile_router
from app.routes.chat import router as chat_router
from app.routes.docs import router as docs_router
from app.routes.chat_ui import router as chat_ui_router
from app.routes.audit import router as audit_router
from app.routes.telemetry import router as telemetry_router

# Import key pools for health check
from app.core.key_manager import GroqPool, GooglePool, DeepSeekPool, MistralPool
from app.utils.formatter import CLIFormatter

# Initialize database
from app.db.database import init_db
init_db()

# Create FastAPI app
app = FastAPI(
    title="PEACOCK ENGINE V3",
    description="Multi-gateway AI orchestration engine with unified API",
    version="3.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount PEACOCK ENGINE WebUI (Vite Build)
# Serving at root / and /ui for unified access
if os.path.exists("peacock-ui/dist"):
    app.mount("/ui", StaticFiles(directory="peacock-ui/dist", html=True), name="ui")
    app.mount("/", StaticFiles(directory="peacock-ui/dist", html=True), name="root_ui")

from app.routes.onboarding import router as onboarding_router
from app.routes.dashboard import router as dashboard_router

# WebUI API routes
from app.routes.models_api import router as models_api_router
from app.routes.keys_api import router as keys_api_router
from app.routes.chat_api import router as chat_api_router
from app.routes.tokens import router as tokens_router

# Include all routers
app.include_router(chat_router, prefix="/v1/chat", tags=["CHAT"])
app.include_router(strike_router, prefix="/v1/strike", tags=["STRIKE (Legacy)"])
app.include_router(onboarding_router, prefix="/v1/onboarding", tags=["ONBOARDING"])
app.include_router(dashboard_router, prefix="/v1/dashboard", tags=["DASHBOARD"])
app.include_router(models_router, prefix="/v1/models", tags=["MODELS"])
app.include_router(models_router, prefix="/v1/chat/models", tags=["MODELS_ALIAS"])
app.include_router(fs_router, prefix="/v1/fs", tags=["FILESYSTEM"])
app.include_router(keys_router, prefix="/v1/keys", tags=["KEYS"])
app.include_router(keys_router, prefix="/v1/keys/usage", tags=["KEYS_ALIAS"])
app.include_router(striker_router, prefix="/v1/striker", tags=["STRIKER"])
app.include_router(payload_strike_router, prefix="/v1/payload-strike", tags=["PAYLOAD_STRIKE"])
app.include_router(proxy_control_router, prefix="/v1/proxy", tags=["PROXY_CONTROL"])
app.include_router(profile_router, prefix="/v1/profile", tags=["PROFILE"])
app.include_router(docs_router, prefix="/v1/docs", tags=["DOCS"])
app.include_router(audit_router, prefix="/v1/audit", tags=["AUDIT"])
app.include_router(telemetry_router, prefix="/v1/telemetry", tags=["TELEMETRY"])

# Include WebUI API routes
app.include_router(models_api_router, prefix="/v1/webui/models", tags=["WEBUI_MODELS"])
app.include_router(keys_api_router, prefix="/v1/webui/keys", tags=["WEBUI_KEYS"])
app.include_router(chat_api_router, prefix="/v1/webui/chat", tags=["WEBUI_CHAT"])
app.include_router(tokens_router, prefix="/v1/tokens", tags=["TOKENS"])

# Unified Chat UI Router
app.include_router(chat_ui_router, prefix="/chat/api", tags=["CHAT_UI"])

@app.get("/health")
async def health():
    """Health check endpoint with key pool status."""
    return {
        "status": "ONLINE",
        "system": "PEACOCK_ENGINE_V3",
        "version": "3.0.0",
        "integrity": {
            "groq": len(GroqPool.deck),
            "google": len(GooglePool.deck),
            "deepseek": len(DeepSeekPool.deck),
            "mistral": len(MistralPool.deck)
        },
        "features": {
            "chat_ui": True,
            "key_tracking": True,
            "generic_endpoint": True
        }
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    CLIFormatter.section_header("PEACOCK ENGINE V3 BOOT SEQUENCE")
    CLIFormatter.success(f"Groq Pool: {len(GroqPool.deck)} keys")
    CLIFormatter.success(f"Google Pool: {len(GooglePool.deck)} keys")
    CLIFormatter.success(f"DeepSeek Pool: {len(DeepSeekPool.deck)} keys")
    CLIFormatter.success(f"Mistral Pool: {len(MistralPool.deck)} keys")
    CLIFormatter.info("CHAT UI: Unified Root Stream Enabled")
    print()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3099))
    uvicorn.run(app, host="0.0.0.0", port=port)
