"""
PIPELINE API — Expose RECON, RELAY, SWARM pipeline modes via REST.
"""

import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

from app.core.pipeline_modes import run_pipeline, format_pipeline_report, PipelineResult
from app.db.database import ProjectBucketDB

router = APIRouter()

_ACTIVE_PIPELINES: Dict[str, Any] = {}


class RunPipelineRequest(BaseModel):
    mode: str = Field(..., description="recon, relay, or swarm")
    bucket_name: str = Field(..., description="Project bucket to use as data source")
    objective: str = Field(..., description="What to build or analyze")
    project_type_hint: Optional[str] = ""
    model_id: Optional[str] = "llama-3.3-70b-versatile"


@router.post("/run")
async def start_pipeline(req: RunPipelineRequest, background_tasks: BackgroundTasks):
    """Start a pipeline job (RECON, RELAY, or SWARM). Returns immediately; poll /{id} for status."""
    if req.mode not in ("recon", "relay", "swarm"):
        raise HTTPException(status_code=400, detail="mode must be recon, relay, or swarm")
    
    bucket = ProjectBucketDB.load_bucket(req.bucket_name)
    if not bucket:
        raise HTTPException(status_code=404, detail=f"Bucket '{req.bucket_name}' not found")
    
    job_id = f"pipe_{uuid.uuid4().hex[:12]}"
    
    async def _run():
        _ACTIVE_PIPELINES[job_id] = {"status": "running", "result": None, "error": None}
        try:
            result = await run_pipeline(
                mode=req.mode,
                bucket_items=bucket["items"],
                objective=req.objective,
                project_type_hint=req.project_type_hint or "",
                model_id=req.model_id or "llama-3.3-70b-versatile",
            )
            _ACTIVE_PIPELINES[job_id] = {"status": "complete", "result": result, "error": None}
        except Exception as e:
            _ACTIVE_PIPELINES[job_id] = {"status": "failed", "result": None, "error": str(e)}
    
    background_tasks.add_task(_run)
    
    return {
        "status": "started",
        "pipeline_id": job_id,
        "mode": req.mode,
        "bucket_name": req.bucket_name,
        "objective": req.objective,
    }


@router.get("/{pipeline_id}")
async def get_pipeline_status(pipeline_id: str):
    """Get the status and results of a pipeline job."""
    job = _ACTIVE_PIPELINES.get(pipeline_id)
    if not job:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    if job["status"] == "running":
        return {"status": "running", "pipeline_id": pipeline_id}
    
    if job["status"] == "failed":
        return {"status": "failed", "pipeline_id": pipeline_id, "error": job["error"]}
    
    result: PipelineResult = job["result"]
    return {
        "status": "complete",
        "pipeline_id": pipeline_id,
        "mode": result.mode,
        "docs_processed": result.docs_processed,
        "docs_total": result.docs_total,
        "total_tokens": result.total_tokens,
        "total_latency_ms": result.total_latency_ms,
        "strikes_fired": len(result.strikes),
        "strikes": [
            {
                "strike_id": s.strike_id,
                "role": s.role,
                "status": s.status,
                "actual_tokens": s.actual_tokens,
                "latency_ms": s.latency_ms,
                "result_preview": s.result[:500] + "..." if len(s.result) > 500 else s.result,
            }
            for s in result.strikes
        ],
        "final_output": result.final_output,
        "report": format_pipeline_report(result),
    }
