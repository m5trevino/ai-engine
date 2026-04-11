from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
from pathlib import Path
import time
from app.core.striker import execute_streaming_strike, execute_strike
from app.utils.logger import HighSignalLogger
import asyncio

router = APIRouter()

# ABSOLUTE REFINERY PATHS
REFINERY_BASE = Path("/root/hetzner/herbert/liquid-semiotic")
MOLDS_DIR = REFINERY_BASE / "semiotic-mold"
LEGOS_DIR = REFINERY_BASE / "legos"
RESULTS_DIR = REFINERY_BASE / "invariants"
DISTILLED_DIR = REFINERY_BASE / "english"

class StrikeRequest(BaseModel):
    mold_path: str
    lego_paths: List[str]
    model_id: str
    temperature: float = 0.7

@router.get("/molds")
async def get_molds():
    """List available Semiotic-Molds (Directives)."""
    try:
        if not MOLDS_DIR.exists():
            return []
        files = []
        for f in MOLDS_DIR.glob("*.txt"):
            files.append({
                "name": f.name,
                "path": str(f.absolute()),
                "content": f.read_text(encoding="utf-8") if f.stat().st_size < 100000 else "FILE_TOO_LARGE"
            })
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/browse")
async def browse_legos(path: Optional[str] = None):
    """Deep-walk directory browser for Clean-Room Primitives (Legos)."""
    target = Path(path) if path else LEGOS_DIR
    
    if not str(target).startswith(str(LEGOS_DIR)):
        # Security: Lock to legos tree
        target = LEGOS_DIR

    try:
        if not target.exists() or not target.is_dir():
            return {"items": [], "current": str(target), "parent": str(LEGOS_DIR)}
            
        items = []
        for item in target.iterdir():
            if item.name.startswith('.'):
                continue
            items.append({
                "name": item.name,
                "path": str(item.absolute()),
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None
            })
        
        items.sort(key=lambda x: (x["type"] != "directory", x["name"].lower()))
        
        return {
            "current": str(target.absolute()),
            "parent": str(target.parent.absolute()) if target != LEGOS_DIR else None,
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/file")
async def get_file_content(path: str):
    """View content for CORE MODE forensics."""
    try:
        p = Path(path)
        if not p.exists() or not p.is_file():
            raise HTTPException(status_code=404, detail="File not found")
        
        # Read first 500KB to be safe
        content = p.read_text(encoding="utf-8", errors="replace")
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    results = []
    mold_content = mold_file.read_text(encoding="utf-8")
    
    for lego_path in request.lego_paths:
        lego_file = Path(lego_path)
        if not lego_file.exists():
            continue
            
        lego_content = lego_file.read_text(encoding="utf-8")
        
        # Build prompt: Mold + Lego Content
        prompt = f"{mold_content}\n\n[CLEAN_ROOM_PRIMITIVE: {lego_file.name}]\n{lego_content}"
        
        # Execute strike
        strike_result = await execute_strike(
            model_id=request.model_id,
            prompt=prompt,
            temp=request.temperature
        )
        
        # Save to invariants
        output_name = f"INVARIANT_{lego_file.stem}_{int(time.time())}.txt"
        output_path = RESULTS_DIR / output_name
        output_path.write_text(strike_result["content"], encoding="utf-8")
        
        results.append({
            "lego": lego_file.name,
            "invariant_path": str(output_path.absolute()),
            "status": "SUCCESS"
        })
    
    return {
        "status": "REFINERY_SEQUENCE_COMPLETE",
        "cast_results": results
    }
