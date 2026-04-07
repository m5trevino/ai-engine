"""
PEACOCK ENGINE - Dashboard & Analytics API
Endpoints for the browser-based Command Center.
"""

import os
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
from app.utils.logger import SUCCESS_LOG, FAILED_LOG, VAULT_DIR

router = APIRouter()

@router.get("/history")
async def get_history(limit: int = 50, gateway: Optional[str] = None):
    """Retrieve the latest strike history from the master logs."""
    history = []
    
    # Combined logs logic
    for log_path in [SUCCESS_LOG, FAILED_LOG]:
        if log_path.exists():
            with open(log_path, "r") as f:
                lines = f.readlines()[-limit*2:] # Grab extra to account for filtering
                for line in lines:
                    try:
                        # Format: [timestamp] TAG | GATEWAY | MODEL | TOKENS | COST
                        parts = line.split("|")
                        ts_tag = parts[0].strip().split("]")
                        entry = {
                            "timestamp": ts_tag[0].replace("[", ""),
                            "tag": ts_tag[1].strip(),
                            "gateway": parts[1].strip(),
                            "model": parts[2].strip(),
                            "tokens": parts[3].strip(),
                            "cost": parts[4].strip(),
                            "status": "SUCCESS" if "success" in str(log_path) else "FAILED"
                        }
                        
                        if gateway and entry["gateway"].lower() != gateway.lower():
                            continue
                            
                        history.append(entry)
                    except: continue
                    
    # Sort by timestamp descending
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    return history[:limit]

@router.get("/vault/{tag}")
async def get_vault_item(tag: str):
    """Retrieve verbatim I/O from the forensic vault."""
    for subdir in ["successful", "failed"]:
        path = VAULT_DIR / subdir / f"{tag}.txt"
        if path.exists():
            return {"tag": tag, "content": path.read_text()}
            
    raise HTTPException(status_code=404, detail="Forensic evidence not found for this tag.")

@router.get("/settings")
async def get_settings():
    """Retrieve current engine settings."""
    return {
        "tunnel_mode": os.getenv("PEACOCK_TUNNEL", "false").lower() == "true",
        "quiet_mode": os.getenv("PEACOCK_QUIET", "false").lower() == "true",
        "success_logging": os.getenv("LOG_SUCCESS", "true").lower() == "true",
        "failed_logging": os.getenv("LOG_FAILED", "true").lower() == "true",
        "verbose": os.getenv("PEACOCK_VERBOSE", "false").lower() == "true"
    }

@router.post("/settings/performance/{mode}")
async def set_performance_mode(mode: str):
    """Switch the Hellcat Protocol performance key."""
    if mode not in ["stealth", "balanced", "apex"]:
        raise HTTPException(status_code=400, detail="Invalid mode. Choose: stealth, balanced, apex")
    
    os.environ["PEACOCK_PERF_MODE"] = mode
    return {"status": "success", "active_key": mode.upper()}

@router.post("/settings/toggle/{key}")
async def toggle_setting(key: str):
    """
    Toggle a specific engine setting.
    In this 'headless' version, we simulate the state change.
    In a full production build, this would update a persistent config or state db.
    """
    # Map the incoming key to our environment variables
    env_map = {
        "tunnel": "PEACOCK_TUNNEL",
        "stealth": "PEACOCK_QUIET",
        "success_logs": "LOG_SUCCESS",
        "fail_logs": "LOG_FAILED"
    }
    
    if key not in env_map:
        raise HTTPException(status_code=400, detail=f"Unknown setting: {key}")
        
    target_env = env_map[key]
    current = os.getenv(target_env, "true" if "LOG" in target_env else "false").lower() == "true"
    new_val = "false" if current else "true"
    
    # Update for current process
    os.environ[target_env] = new_val
    
    return {"status": "success", "key": key, "new_state": new_val == "true"}
