"""
PEACOCK ENGINE - Batch Striker Module
Handles high-volume asynchronous strike jobs via Google GenAI Batch API.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from app.core.key_manager import GooglePool
from app.utils.logger import HighSignalLogger
from app.utils.formatter import CLIFormatter

class BatchStriker:
    """Orchestrates Google Batch API jobs."""
    
    @staticmethod
    async def create_job(model_id: str, requests: List[Dict[str, Any]], api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new batch strike job.
        requests: List of {'prompt': str, 'temp': float, ...}
        """
        if not api_key:
            asset = GooglePool.get_next()
            api_key = asset.key
            account = asset.account
        else:
            account = "MANUAL_KEY"

        client = genai.Client(api_key=api_key)
        
        # Transform Peacock requests into Google SDK format
        # Inline requests support: [{'contents': [{'role': 'user', 'parts': [{'text': '...'}]}]}]
        google_requests = []
        for req in requests:
            google_requests.append({
                'contents': [{'role': 'user', 'parts': [{'text': req['prompt']}]}]
            })

        try:
            # client.batches.create(model, src)
            # Reference: gemini-2.0-flash, etc.
            clean_model = model_id.replace("models/", "")
            
            job = client.batches.create(
                model=clean_model,
                src=google_requests
            )
            
            # Log the dispatch
            HighSignalLogger.log_event("BATCH_DISPATCH", {
                "job_name": job.name,
                "model": model_id,
                "request_count": len(requests),
                "account": account
            })
            
            return {
                "job_id": job.name,
                "state": job.state,
                "created_at": job.create_time,
                "model": model_id,
                "request_count": len(requests)
            }
        except Exception as e:
            CLIFormatter.error("BATCH_STRIKE_FAILED", str(e))
            raise e

    @staticmethod
    async def get_status(job_id: str, api_key: str) -> Dict[str, Any]:
        """Check the status of a specific batch job."""
        client = genai.Client(api_key=api_key)
        try:
            job = client.batches.get(name=job_id)
            return {
                "job_id": job.name,
                "state": job.state, # PENDING, RUNNING, SUCCEEDED, FAILED
                "progress": job.completion_stats if hasattr(job, 'completion_stats') else None,
                "error": job.error if hasattr(job, 'error') else None
            }
        except Exception as e:
            return {"error": str(e)}
