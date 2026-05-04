import time
import hmac
import hashlib
from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import config # Assuming config has security settings

X_API_KEY = APIKeyHeader(name="X-Peacock-Key", auto_error=False)

class PeacockSecurityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Skip auth for static assets and health checks
        if request.url.path in ["/", "/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        if request.url.path.startswith("/static"):
            return await call_next(request)

        # 2. Check API Key
        api_key = request.headers.get("X-Peacock-Key")
        master_key = getattr(config, "MASTER_KEY", None)

        if not master_key:
            # If no master key set, allow everything (Safe mode)
            # In production, this should be a WARNING
            return await call_next(request)

        if api_key != master_key:
            raise HTTPException(status_code=403, detail="ACCESS_DENIED: UNAUTHORIZED_STRIKE_DETECTED")

        # 3. Rate Limiting Logic (Simplified for now)
        # TODO: Implement Redis-backed sliding window

        response = await call_next(request)
        return response

def generate_session_token(payload: dict, secret: str) -> str:
    """Simple HMAC-based signature for session validation"""
    ts = str(int(time.time()))
    data = f"{ts}.{payload}"
    signature = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{signature}"
