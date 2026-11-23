from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import os
from app.core.striker import execute_strike
from app.config import MODEL_REGISTRY

router = APIRouter()

class PayloadStrikeRequest(BaseModel):
    modelId: str
    prompt: str
    files: List[str]
    temp: Optional[float] = 0.7
    format_mode: Optional[str] = None

def get_all_files(path: Path) -> List[Path]:
    """Recursively find all relevant text/code files in a directory or return the file itself."""
    valid_extensions = {'.txt', '.json', '.md', '.py', '.js', '.ts', '.yaml', '.yml', '.html', '.css'}

    if path.is_file():
        return [path]

    found_files = []
    if path.is_dir():
        for root, dirs, files in os.walk(path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if not file.startswith('.'):
                    p = Path(root) / file
                    if p.suffix.lower() in valid_extensions:
                        found_files.append(p)
    return found_files

@router.post("")
async def payload_strike(request: PayloadStrikeRequest):
    print(f"[💥 PAYLOAD STRIKE] MODEL: {request.modelId} | FILES: {len(request.files)}")

    try:
        model_config = next((m for m in MODEL_REGISTRY if m.id == request.modelId), None)
        if not model_config:
            raise HTTPException(status_code=400, detail="Unknown Model ID")

        # 1. Resolve all files
        all_resolved_paths = []
        for f_path in request.files:
            p = Path(f_path)
            if not p.exists():
                print(f"[⚠️] Path not found: {f_path}")
                continue
            all_resolved_paths.extend(get_all_files(p))

        if not all_resolved_paths:
            raise HTTPException(status_code=400, detail="No valid files found in the provided paths")

        # 2. Build combined payload
        payload_blocks = []
        for p in all_resolved_paths:
            try:
                content = p.read_text(encoding='utf-8', errors='ignore')
                payload_blocks.append(f"\n\n--- FILE: {str(p.absolute())} ---\n{content}")
            except Exception as e:
                print(f"[⚠️] Failed to read {p}: {e}")

        combined_payload = "".join(payload_blocks)
        final_prompt = f"{request.prompt}\n\nPAYLOAD:{combined_payload}"

        # 3. Execute Strike
        result = await execute_strike(
            gateway=model_config.gateway,
            model_id=request.modelId,
            prompt=final_prompt,
            temp=request.temp,
            format_mode=request.format_mode
        )
        return result

    except Exception as e:
        print(f"[❌ PAYLOAD STRIKE ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
