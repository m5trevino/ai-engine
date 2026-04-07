"""
PEACOCK ENGINE - Onboarding API
Handles new app registration and provides integration kits.
"""

import uuid
import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from app.models.app_profile import AppRegistrationRequest, AppRegistrationResponse
from app.db.database import get_db
from app.config import MODEL_REGISTRY

router = APIRouter()

MODEL_PACKS = {
    "fast": ["gemini-3.1-flash-lite", "llama-3.1-8b-instant", "llama-4-scout"],
    "smart": ["gemini-3.1-pro", "llama-3.3-70b-versatile", "llama-4-maverick"],
    "all": [m.id for m in MODEL_REGISTRY if m.status == "active"]
}

@router.post("/onboard", response_model=AppRegistrationResponse)
async def onboard_app(request: AppRegistrationRequest):
    """Register a new application and get an integration kit."""
    app_id = str(uuid.uuid4())[:8]
    api_secret = f"pk_{uuid.uuid4().hex[:24]}"
    
    allowed_models = MODEL_PACKS.get(request.model_pack, MODEL_PACKS["fast"])
    
    # Save to DB
    try:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO apps (id, name, description, default_models, api_secret)
                VALUES (?, ?, ?, ?, ?)
            """, (app_id, request.name, request.description, json.dumps(allowed_models), api_secret))
            conn.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Generate Integration Kit
    kit = {
        "sdk_init": f"from app.client.sdk import PeacockClient\nclient = PeacockClient(api_key='{api_secret}')",
        "curl_example": f"curl -X POST http://localhost:3099/v1/strike -H 'Authorization: Bearer {api_secret}' -d '{{\"modelId\": \"{allowed_models[0]}\", \"prompt\": \"Hello!\"}}'",
        "documentation_link": "http://localhost:3099/v1/docs/endpoints"
    }

    return AppRegistrationResponse(
        app_id=app_id,
        api_secret=api_secret,
        name=request.name,
        created_at=datetime.now().isoformat(),
        allowed_models=allowed_models,
        integration_kit=kit
    )
