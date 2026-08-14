"""
PEACOCK ENGINE V3 - FastAPI Application
Multi-gateway AI orchestration engine.
"""

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from contextlib import asynccontextmanager
import os
import uuid
import traceback
import logging
import asyncio

# Import all route modules
from app.routes.strike import router as strike_router
from app.routes.models import router as models_router
from app.routes.models_register import router as models_register_router
from app.routes.fs import router as fs_router
from app.routes.keys import router as keys_router
from app.routes.striker import router as striker_router
from app.routes.payload_strike import router as payload_strike_router
from app.routes.proxy_control import router as proxy_control_router
from app.routes.profile import router as profile_router
from app.routes.openai_compat import router as openai_compat_router
from app.routes.chat import router as chat_router
from app.routes.docs import router as docs_router
from app.routes.chat_ui import router as chat_ui_router
from app.routes.audit import router as audit_router
from app.routes.telemetry import router as telemetry_router
from app.routes.neural_link import router as neural_link_router
from app.routes.refinery import router as refinery_router
from app.routes.projects import router as projects_router
from app.routes.codebase import router as codebase_router
from app.routes.buckets import router as buckets_router
from app.routes.pipelines import router as pipelines_router
from app.routes.aviary import router as aviary_router
from app.routes.plans import router as plans_router
from app.routes.history import router as history_router
from app.routes.config import router as config_router
from app.routes.stress import router as stress_router
from app.routes.admin import router as admin_router
from app.routes.payloads import router as payloads_router
from app.routes.skill_scanner import router as skill_scanner_router
from app.routes.ollama_cloud_health import router as ollama_cloud_health_router
from app.routes.groq_health import router as groq_health_router
from app.routes.opencode_health import router as opencode_health_router

# Import key pools for health check
from app.core.key_manager import GroqPool, OllamaPool, OpencodeGoPool, OpencodeZenPool, OpenrouterPool, HetznerPool, ZaiPool, ZaiCodingPool
from app.core.rate_limit_tracker import GroqRateTracker
from app.core.global_pacer import GroqPacer
from app.utils.formatter import CLIFormatter

# Initialize database
from app.db.database import init_db
init_db()


# Lifespan: startup / shutdown hooks for TB-002 persistence + TB-023a cleanup
@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.rate_limit_tracker import GroqRateTracker
    from app.core.cleanup import CleanupManager

    GroqRateTracker.load()
    await GroqRateTracker.start_auto_save(interval=30.0)

    # TB-023a: startup cleanup + background scheduler
    cleanup_mgr = CleanupManager()
    cleanup_mgr.run_on_startup()
    cleanup_task = asyncio.create_task(cleanup_mgr.start_scheduler())

    yield

    await GroqRateTracker.stop_auto_save()
    await GroqRateTracker.save()
    cleanup_mgr.stop_scheduler()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass


# Create FastAPI app
app = FastAPI(
    title="PEACOCK ENGINE V3",
    description="Multi-gateway AI orchestration engine with unified API",
    version="3.0.0",
    lifespan=lifespan
)


# ═══════════════════════════════════════════════════════════════════════════════
# REQUEST ID MIDDLEWARE
# ═══════════════════════════════════════════════════════════════════════════════

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a unique request ID to every incoming request."""
    request.state.request_id = str(uuid.uuid4())[:12]
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    return response


# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL EXCEPTION HANDLER
# ═══════════════════════════════════════════════════════════════════════════════

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions and return a clean JSON response."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger = logging.getLogger("peacock.errors")
    logger.error(f"Unhandled exception [req={request_id}]: {exc}")
    logger.debug(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") == "1" else "An unexpected error occurred",
            "request_id": request_id,
        },
    )


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes.onboarding import router as onboarding_router
from app.routes.dashboard import router as dashboard_router

# WebUI API routes
from app.routes.models_api import router as models_api_router
from app.routes.keys_api import router as keys_api_router
from app.routes.chat_api import router as chat_api_router
from app.routes.tokens import router as tokens_router

from app.routes.groq_proxy import router as groq_proxy_router
from app.routes.gateway_proxy import router as gateway_proxy_router
from app.routes.unified_routes import router as unified_router
# Include all routers
# NOTE: models_router must be registered BEFORE openai_compat_router
# because both have /models endpoint, and we want our native endpoint to take precedence
app.include_router(models_router, prefix="/v1/models", tags=["MODELS"])
app.include_router(models_register_router, prefix="/v1/models", tags=["MODELS_REGISTER"])
app.include_router(openai_compat_router, prefix="/v1", tags=["OPENAI_COMPAT"])
app.include_router(chat_router, prefix="/v1/chat", tags=["CHAT"])
app.include_router(strike_router, prefix="/v1/strike", tags=["STRIKE (Legacy)"])
app.include_router(onboarding_router, prefix="/v1/onboarding", tags=["ONBOARDING"])
app.include_router(dashboard_router, prefix="/v1/dashboard", tags=["DASHBOARD"])
app.include_router(fs_router, prefix="/v1/fs", tags=["FILESYSTEM"])
app.include_router(keys_router, prefix="/v1/keys", tags=["KEYS"])
app.include_router(striker_router, prefix="/v1/striker", tags=["STRIKER"])
app.include_router(payload_strike_router, prefix="/v1/payload-strike", tags=["PAYLOAD_STRIKE"])
app.include_router(proxy_control_router, prefix="/v1/proxy", tags=["PROXY_CONTROL"])
app.include_router(profile_router, prefix="/v1/profile", tags=["PROFILE"])
app.include_router(docs_router, prefix="/v1/docs", tags=["DOCS"])
app.include_router(audit_router, prefix="/v1/audit", tags=["AUDIT"])
app.include_router(telemetry_router, prefix="/v1/telemetry", tags=["TELEMETRY"])
app.include_router(neural_link_router, prefix="/v1/neural-link", tags=["NEURAL_LINK"])
app.include_router(refinery_router, prefix="/v1/refinery", tags=["REFINERY"])
app.include_router(projects_router, prefix="/v1/projects", tags=["PROJECTS"])
app.include_router(codebase_router, prefix="/v1/codebase", tags=["CODEBASE"])
app.include_router(buckets_router, prefix="/v1/buckets", tags=["BUCKETS"])
app.include_router(pipelines_router, prefix="/v1/pipelines", tags=["PIPELINES"])
app.include_router(aviary_router, prefix="/v1/aviary", tags=["AVIARY"])
app.include_router(plans_router, prefix="/v1/plans", tags=["PLANS"])
app.include_router(history_router, prefix="/v1/history", tags=["HISTORY"])
app.include_router(config_router, prefix="/v1/config", tags=["CONFIG"])
app.include_router(stress_router, prefix="/v1/stress", tags=["STRESS"])
app.include_router(admin_router, prefix="/v1/admin", tags=["ADMIN"])
app.include_router(skill_scanner_router, prefix="/v1/skill-scanner", tags=["SKILL_SCANNER"])
app.include_router(payloads_router, prefix="/v1/payloads", tags=["PAYLOADS"])
app.include_router(ollama_cloud_health_router, prefix="/health", tags=["OLLAMA_CLOUD_HEALTH"])
app.include_router(opencode_health_router, prefix="/health", tags=["OPENCODE_HEALTH"])
app.include_router(groq_health_router, prefix="/health", tags=["GROQ_HEALTH"])

# Include WebUI API routes
app.include_router(models_api_router, prefix="/v1/webui/models", tags=["WEBUI_MODELS"])
app.include_router(keys_api_router, prefix="/v1/webui/keys", tags=["WEBUI_KEYS"])
app.include_router(chat_api_router, prefix="/v1/webui/chat", tags=["WEBUI_CHAT"])
app.include_router(tokens_router, prefix="/v1/tokens", tags=["TOKENS"])

app.include_router(groq_proxy_router, prefix="/v1/groq", tags=["GROQ_PROXY"])
app.include_router(gateway_proxy_router, prefix="/v1", tags=["GATEWAY_PROXY"])
app.include_router(unified_router, prefix="/v1", tags=["UNIFIED"])
# Unified Chat UI Router
app.include_router(chat_ui_router, prefix="/chat/api", tags=["CHAT_UI"])


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH + SYSTEM STATUS
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    """Health check endpoint with key pool status and Groq rate limit snapshot."""
    from app.config import MODEL_REGISTRY
    from app.core.config_store import config_store
    from app.config import PERFORMANCE_MODES
    
    key_labels = [a.account for a in GroqPool.deck]
    governor = GroqRateTracker.get_snapshot(key_labels=key_labels)
    pacer = GroqPacer.get_pacer_snapshot()
    
    # Model registry health
    total_models = len(MODEL_REGISTRY)
    frozen_count = sum(1 for m in MODEL_REGISTRY if m.status == "frozen")
    deprecated_count = sum(1 for m in MODEL_REGISTRY if m.status == "deprecated")
    active_count = total_models - frozen_count - deprecated_count
    
    # Count by gateway
    by_gateway = {}
    for m in MODEL_REGISTRY:
        if m.gateway not in by_gateway:
            by_gateway[m.gateway] = {"total": 0, "active": 0, "frozen": 0, "deprecated": 0}
        by_gateway[m.gateway]["total"] += 1
        by_gateway[m.gateway][m.status] += 1
    
    # Get current performance mode
    perf_mode = config_store.performance_mode
    perf_cfg = PERFORMANCE_MODES.get(perf_mode, PERFORMANCE_MODES["balanced"])
    
    return {
        "status": "ONLINE",
        "system": "PEACOCK_ENGINE_V3",
        "version": "3.0.0",
        "integrity": {
            "groq": len(GroqPool.deck),
            "opencode-go": len(OpencodeGoPool.deck),
            "opencode-zen": len(OpencodeZenPool.deck),
            "openrouter": len(OpenrouterPool.deck),
            "ollama": len(OllamaPool.deck),
            "hetzner": len(HetznerPool.deck),
            "zai": len(ZaiPool.deck),
            "zai-coding": len(ZaiCodingPool.deck),
        },
        "providers": config_store.providers,
        "models": {
            "total": total_models,
            "active": active_count,
            "frozen": frozen_count,
            "deprecated": deprecated_count,
            "by_gateway": by_gateway
        },
        "features": {
            "chat_ui": True,
            "key_tracking": True,
            "generic_endpoint": True
        },
        "performance_mode": {
            "active": perf_mode,
            "name": perf_cfg["name"],
            "multiplier": perf_cfg["multiplier"],
        },
        "effective_settings": {
            "guard_warn_threshold": config_store.guard["warn_threshold"],
            "guard_block_threshold": config_store.guard["block_threshold"],
            "proxy_tpm_threshold_pct": config_store.proxy_rules["tpm_threshold_pct"],
            "proxy_rpm_threshold_pct": config_store.proxy_rules["rpm_threshold_pct"],
            "pacer_burn_mode": config_store.burn_mode,
            "pacer_tpm_backpressure_pct": config_store.pacer["tpm_backpressure_pct"],
        },
        "governor": {
            "pool_health": governor.pool_health,
            "key_count": len(governor.keys),
            "timestamp": governor.timestamp,
        },
        "pacer": pacer,
    }


@app.get("/v1/admin/system")
async def system_status():
    """
    Comprehensive system health snapshot.
    Returns queue depth, recent failure rate, storage health, and Groq rate limits.
    """
    from app.core.plan_queue import PlanQueueSingleton, PlanRunnerSingleton
    from app.core.history import HistoryStore
    from app.core.cleanup import CleanupManager
    from app.core.config_store import config_store
    from app.config import PERFORMANCE_MODES

    queue_snap = await PlanRunnerSingleton.snapshot()
    history_stats = HistoryStore.get_stats(days=1)
    storage = CleanupManager.storage_stats()

    total_storage = storage["total_bytes"]
    storage_mb = round(total_storage / (1024 * 1024), 2)

    key_labels = [a.account for a in GroqPool.deck]
    governor = GroqRateTracker.get_snapshot(key_labels=key_labels)
    pacer = GroqPacer.get_pacer_snapshot()
    
    # Get current performance mode
    perf_mode = config_store.performance_mode
    perf_cfg = PERFORMANCE_MODES.get(perf_mode, PERFORMANCE_MODES["balanced"])

    return {
        "status": "healthy",
        "queue": {
            "state": queue_snap.state,
            "depth": queue_snap.length,
            "current_plan_id": queue_snap.current_plan_id,
            "completed_today": history_stats["completed_runs"],
            "failed_today": history_stats["failed_runs"],
        },
        "failure_rate_24h": history_stats["failure_rate"],
        "storage": {
            "plans": storage["plans"]["count"],
            "history": storage["history"]["count"],
            "stress": storage["stress"]["count"],
            "total_mb": storage_mb,
        },
        "keys": {
            "groq": len(GroqPool.deck),
            "opencode-go": len(OpencodeGoPool.deck),
            "opencode-zen": len(OpencodeZenPool.deck),
            "openrouter": len(OpenrouterPool.deck),
            "ollama": len(OllamaPool.deck),
            "hetzner": len(HetznerPool.deck),
            "zai": len(ZaiPool.deck),
            "zai-coding": len(ZaiCodingPool.deck),
        },
        "providers": config_store.providers,
        "performance_mode": {
            "active": perf_mode,
            "name": perf_cfg["name"],
            "multiplier": perf_cfg["multiplier"],
        },
        "effective_settings": {
            "guard_warn_threshold": config_store.guard["warn_threshold"],
            "guard_block_threshold": config_store.guard["block_threshold"],
            "proxy_tpm_threshold_pct": config_store.proxy_rules["tpm_threshold_pct"],
            "proxy_rpm_threshold_pct": config_store.proxy_rules["rpm_threshold_pct"],
            "pacer_burn_mode": config_store.burn_mode,
            "pacer_tpm_backpressure_pct": config_store.pacer["tpm_backpressure_pct"],
        },
        "governor": {
            "pool_health": governor.pool_health,
            "key_count": len(governor.keys),
            "timestamp": governor.timestamp,
        },
        "pacer": pacer,
    }


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    CLIFormatter.section_header("PEACOCK ENGINE V3 BOOT SEQUENCE")
    CLIFormatter.success(f"Groq Pool: {len(GroqPool.deck)} keys")
    CLIFormatter.success(f"OpenCode Go Pool: {len(OpencodeGoPool.deck)} keys")
    CLIFormatter.success(f"OpenCode Zen Pool: {len(OpencodeZenPool.deck)} keys")
    CLIFormatter.success(f"OpenRouter Pool: {len(OpenrouterPool.deck)} keys")
    CLIFormatter.success(f"Ollama Cloud Pool: {len(OllamaPool.deck)} keys")
    CLIFormatter.success(f"Hetzner Pool: {len(HetznerPool.deck)} keys")
    CLIFormatter.success(f"ZAI Pool: {len(ZaiPool.deck)} keys")
    CLIFormatter.success(f"ZAI Coding Plan Pool: {len(ZaiCodingPool.deck)} keys")
    CLIFormatter.info("CHAT UI: Unified Root Stream Enabled")
    print()

# Mount PEACOCK ENGINE WebUI (Vite Build)
# Serving at root / and /static at the end to allow API routes to catch first
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.mount("/", StaticFiles(directory="app/static", html=True), name="root_ui")

# SPA Catch-All Route
# Must be at the very bottom to avoid intercepting valid API routes
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    """Serve index.html for all non-API, non-static GET requests."""
    # Skip for API routes (they should return real 404s)
    if full_path.startswith("v1/") or full_path.startswith("static/"):
        return {"detail": "Not Found"}
    
    # Path to index.html
    index_path = os.path.join("app/static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    return {"detail": "Not Found"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3099))
    uvicorn.run(app, host="0.0.0.0", port=port)
