"""
PEACOCK ENGINE - App Profile Models
Pydantic models for app registration and management.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class AppRegistrationRequest(BaseModel):
    name: str = Field(..., description="The human-readable name of your application")
    description: Optional[str] = Field(None, description="Optional description of the app's purpose")
    model_pack: str = Field("standard", description="Model pack: 'fast', 'smart', or 'all'")

class AppRegistrationResponse(BaseModel):
    app_id: str
    api_secret: str
    name: str
    created_at: str
    allowed_models: List[str]
    integration_kit: Dict[str, Any]
