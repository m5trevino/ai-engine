from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import re
from pathlib import Path

router = APIRouter()

class ProxySettings(BaseModel):
    enable_dataimpulse: bool

def get_env_path():
    """Find .env file relative to project root"""
    # This file is at app/routes/proxy_control.py, so project root is 3 levels up
    project_root = Path(__file__).parent.parent.parent.resolve()
    return project_root / ".env"

@router.post("/v1/proxy/toggle")
async def toggle_dataimpulse_proxy(settings: ProxySettings):
    env_path = get_env_path()

    try:
        with open(env_path, "r") as f:
            lines = f.readlines()

        with open(env_path, "w") as f:
            for line in lines:
                if "PROXY_ENABLED=" in line:
                    f.write(f"PROXY_ENABLED={'true' if settings.enable_dataimpulse else 'false'}\n")
                elif "PROXY_URL=" in line and "DATAIMPULSE_URL=" not in line and "LOCAL_PROXY=" not in line:
                    if settings.enable_dataimpulse:
                        # Attempt to get DATAIMPULSE_URL if enabling
                        dataimpulse_url_match = next((l for l in lines if "DATAIMPULSE_URL=" in l), None)
                        if dataimpulse_url_match:
                            dataimpulse_url = dataimpulse_url_match.split("=")[1].strip()
                            f.write(f"PROXY_URL={dataimpulse_url}\n")
                        else:
                            raise HTTPException(status_code=500, detail="DATAIMPULSE_URL not found in .env")
                    else:
                        # Attempt to get LOCAL_PROXY if disabling
                        local_proxy_match = next((l for l in lines if "LOCAL_PROXY=" in l), None)
                        if local_proxy_match:
                            local_proxy_url = local_proxy_match.split("=")[1].strip()
                            f.write(f"PROXY_URL={local_proxy_url}\n")
                        else:
                            raise HTTPException(status_code=500, detail="LOCAL_PROXY not found in .env")
                else:
                    f.write(line)
        return {"message": f"DataImpulse proxy set to {'enabled' if settings.enable_dataimpulse else 'disabled'}."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
