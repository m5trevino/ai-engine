"""
PEACOCK ENGINE — Payload File Manager (TB-031)
List and upload files in the payloads/ directory for plan generation.
"""

import os
from pathlib import Path
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

router = APIRouter()

PAYLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "payloads"
PAYLOADS_DIR.mkdir(parents=True, exist_ok=True)


class PayloadFileItem(BaseModel):
    name: str
    size: int
    modified: float


@router.get("", response_model=List[PayloadFileItem])
async def list_payloads():
    """List all files in the payloads directory."""
    items: List[PayloadFileItem] = []
    if PAYLOADS_DIR.exists():
        for path in sorted(PAYLOADS_DIR.iterdir()):
            if path.is_file():
                stat = path.stat()
                items.append(PayloadFileItem(name=path.name, size=stat.st_size, modified=stat.st_mtime))
    return items


@router.post("/upload")
async def upload_payload(file: UploadFile = File(...)):
    """Upload a file to the payloads directory."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    target = PAYLOADS_DIR / file.filename
    try:
        content = await file.read()
        target.write_bytes(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")
    return {"status": "uploaded", "name": file.filename, "path": str(target), "size": len(content)}


@router.delete("/{filename}")
async def delete_payload(filename: str):
    """Delete a file from the payloads directory."""
    target = PAYLOADS_DIR / filename
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    target.unlink()
    return {"status": "deleted", "name": filename}
