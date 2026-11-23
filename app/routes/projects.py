"""
PROJECTS API — Named working contexts + Project Generation Engine
"""

import uuid
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.db.database import ProjectDB, ProjectBucketDB
from app.core.project_engine import (
    generate_project,
    ProjectConfig,
    project_result_to_json,
    ProjectResult,
)
from app.config import MODEL_REGISTRY

router = APIRouter()


# ─── SAVED PROJECTS (bucket-linked contexts) ─────────────────────────

class SaveProjectRequest(BaseModel):
    id: Optional[str] = Field(default=None, description="Project ID (auto-generated if omitted)")
    name: str = Field(..., description="Display name")
    description: Optional[str] = Field(default="", description="Short description")
    bucket_name: str = Field(..., description="Associated project bucket name")
    conversation_id: Optional[str] = Field(default=None, description="Linked conversation ID")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Extra metadata")


@router.post("/save")
async def save_project(req: SaveProjectRequest):
    """Save (or update) a named project referencing a bucket."""
    project_id = req.id or f"proj_{uuid.uuid4().hex[:8]}"
    
    bucket = ProjectBucketDB.load_bucket(req.bucket_name)
    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{req.bucket_name}' not found")
    
    ProjectDB.create(
        project_id=project_id,
        name=req.name,
        description=req.description or "",
        bucket_name=req.bucket_name,
        conversation_id=req.conversation_id or "",
        metadata=req.metadata or {},
    )
    return {"status": "ok", "project_id": project_id}


@router.get("/list")
async def list_projects(limit: int = 100):
    """List all saved projects, most recently updated first."""
    projects = ProjectDB.list_projects(limit=limit)
    return {"projects": projects, "total": len(projects)}


@router.post("/{project_id}/load")
async def load_project(project_id: str):
    """Load a saved project into active context."""
    project = ProjectDB.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    bucket_name = project.get("bucket_name", "")
    bucket = ProjectBucketDB.load_bucket(bucket_name)
    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{bucket_name}' not found")
    
    return {
        "status": "ok",
        "project": project,
        "bucket": bucket,
    }


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a saved project (does NOT delete the underlying bucket)."""
    ProjectDB.delete_project(project_id)
    return {"status": "ok", "deleted": project_id}


# ─── PROJECT GENERATION ENGINE ───────────────────────────────────────

# In-memory store for generation jobs
_GENERATION_JOBS: Dict[str, ProjectResult] = {}


class GenerateProjectRequest(BaseModel):
    name: str
    description: str
    model: str
    temperature: float = 0.3
    max_iterations: int = 3
    files_per_batch: int = 5
    enable_memory: bool = True
    project_type_hint: Optional[str] = None


class GenerationStatusResponse(BaseModel):
    project_id: str
    status: str
    name: str
    description: str
    model: str
    file_count: int
    iterations: int
    total_tokens: int
    total_duration_ms: int
    errors: List[str]


async def _run_generation_job(job_id: str, req: GenerateProjectRequest):
    """Background worker for project generation."""
    model_cfg = next((m for m in MODEL_REGISTRY if m.id == req.model), None)
    gateway = model_cfg.gateway if model_cfg else "groq"
    
    config = ProjectConfig(
        name=req.name,
        description=req.description,
        model=req.model,
        gateway=gateway,
        temperature=req.temperature,
        max_iterations=req.max_iterations,
        files_per_batch=req.files_per_batch,
        enable_memory=req.enable_memory,
        project_type_hint=req.project_type_hint or None,
    )
    
    result = await generate_project(config)
    _GENERATION_JOBS[job_id] = result


@router.post("/generate")
async def generate_project_endpoint(req: GenerateProjectRequest, background_tasks: BackgroundTasks):
    """Start a new project generation job. Returns immediately; poll /{id} for progress."""
    job_id = f"gen_{uuid.uuid4().hex[:12]}"
    
    # Validate model
    model_cfg = next((m for m in MODEL_REGISTRY if m.id == req.model), None)
    if not model_cfg:
        raise HTTPException(status_code=400, detail=f"Unknown model: {req.model}")
    
    # Placeholder entry so polling doesn't 404 immediately
    placeholder = ProjectResult(
        config=ProjectConfig(
            name=req.name,
            description=req.description,
            model=req.model,
            gateway=model_cfg.gateway,
            temperature=req.temperature,
            max_iterations=req.max_iterations,
            files_per_batch=req.files_per_batch,
            enable_memory=req.enable_memory,
            project_type_hint=req.project_type_hint,
        ),
        status="pending",
    )
    _GENERATION_JOBS[job_id] = placeholder
    
    background_tasks.add_task(_run_generation_job, job_id, req)
    
    return {
        "status": "started",
        "project_id": job_id,
        "name": req.name,
        "model": req.model,
    }


@router.get("/{project_id}")
async def get_project_or_generation(project_id: str):
    """Get a project — checks saved projects first, then generation jobs."""
    # 1. Check saved projects
    project = ProjectDB.get_project(project_id)
    if project:
        return project
    
    # 2. Check generation jobs
    result = _GENERATION_JOBS.get(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return project_result_to_json(result)


@router.get("/{project_id}/deploy")
async def get_deploy_script(project_id: str):
    """Get the deploy.sh script for a generated project."""
    result = _GENERATION_JOBS.get(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"script": result.deploy_script}


@router.get("/{project_id}/readme")
async def get_readme(project_id: str):
    """Get the README for a generated project."""
    result = _GENERATION_JOBS.get(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"readme": result.readme}


@router.get("/{project_id}/manifest")
async def get_manifest(project_id: str):
    """Get the manifest for a generated project."""
    result = _GENERATION_JOBS.get(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {"manifest": result.manifest}


@router.get("/{project_id}/file/{file_path:path}")
async def get_project_file(project_id: str, file_path: str):
    """Get a specific file from a generated project."""
    result = _GENERATION_JOBS.get(project_id)
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    
    for f in result.files:
        if f.path == file_path:
            return {
                "path": f.path,
                "content": f.content,
                "mode": f.mode,
                "executable": f.executable,
            }
    
    raise HTTPException(status_code=404, detail=f"File '{file_path}' not found in project")
