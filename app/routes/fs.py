import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from pathlib import Path

router = APIRouter()

# Dynamic root detection logic to handle VPS vs Local transitions
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
# If in /root/hetzner/ai-engine, the relative root is /root/hetzner
# If in /home/flintx/hetzner/ai-engine, the relative root is /home/flintx/hetzner
HETZNER_ROOT = PROJECT_ROOT.parent

AMMO_DIR = str(HETZNER_ROOT / "ammo")
START_DIR = str(HETZNER_ROOT / "peacock" / "start")
PROMPTS_BASE = str(HETZNER_ROOT / "peacock" / "prompts")

class PromptAsset(BaseModel):
    id: str
    name: str
    phase: str
    content: str

class PromptSaveRequest(BaseModel):
    name: str
    content: str

@router.get("/start")
async def get_start_files():
    try:
        path = Path(START_DIR)
        if not path.exists():
            return []
        files = [f.name for f in path.iterdir() if not f.name.startswith('.')]
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to read start dir")

@router.get("/start/{file_name}")
async def get_start_file(file_name: str):
    try:
        file_path = Path(START_DIR) / file_name
        return {"content": file_path.read_text(encoding="utf-8")}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to read start file")

@router.get("/ammo")
async def get_ammo():
    try:
        path = Path(AMMO_DIR)
        if not path.exists():
            return []
        files = [f.name for f in path.iterdir() if f.suffix in ['.md', '.txt', '.json']]
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to read ammo dir")

@router.get("/ammo/{file_name}")
async def get_ammo_file(file_name: str):
    try:
        file_path = Path(AMMO_DIR) / file_name
        return {"content": file_path.read_text(encoding="utf-8")}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to read file")

@router.get("/prompts/{phase}", response_model=List[PromptAsset])
async def get_prompts(phase: str):
    dir_path = Path(PROMPTS_BASE) / phase
    try:
        if not dir_path.exists():
            return []
        prompts = []
        extensions = ["*.md", "*.txt"]
        for ext in extensions:
            for f in dir_path.glob(ext):
                prompts.append(PromptAsset(
                    id=f.name,
                    name=f.stem,
                    phase=phase,
                    content=f.read_text(encoding="utf-8")
                ))
        return prompts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read prompts for {phase}")

@router.post("/prompts/{phase}")
async def save_prompt(phase: str, request: PromptSaveRequest):
    dir_path = Path(PROMPTS_BASE) / phase
    try:
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / f"{request.name}.md"
        file_path.write_text(request.content, encoding="utf-8")
        return {"status": "SECURED"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to secure prompt")

@router.delete("/prompts/{phase}/{name}")
async def delete_prompt(phase: str, name: str):
    file_path = Path(PROMPTS_BASE) / phase / f"{name}.md"
    try:
        if file_path.exists():
            file_path.unlink()
        return {"status": "PURGED"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to purge asset")

@router.get("/browse")
async def browse_directory(path: str = None):
    try:
        if path is None:
            path = str(HETZNER_ROOT)
        target = Path(path)
        if not target.exists() or not target.is_dir():
            raise HTTPException(status_code=400, detail="Invalid path")
            
        # Only return directories
        items = []
        for item in target.iterdir():
            if item.name.startswith('.'):
                continue
            
            items.append({
                "name": item.name,
                "path": str(item.absolute()),
                "type": "directory" if item.is_dir() else "file"
            })
        
        # Sort alphabetically
        items.sort(key=lambda x: x["name"].lower())
        
        return {
            "current": str(target.absolute()),
            "parent": str(target.parent.absolute()) if target.parent != target else None,
            "items": items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))