import asyncio
import json
import time
import uuid
import re
import yaml
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.striker import execute_streaming_strike
from app.db.database import BatchDB
from app.config import MODEL_REGISTRY

router = APIRouter()

# Dirs (mirroring striker.py routes for parity)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
MISSION_VAULT_DIR = PROJECT_ROOT / "MissionVault"
MISSION_VAULT_DIR.mkdir(parents=True, exist_ok=True)

class StrikeSettings(BaseModel):
    temperature: float = 0.3
    max_tokens: int = 4096
    output_format: str = "markdown"

class MissionRequest(BaseModel):
    name: str = "UNNAMED_MISSION"
    prompt_path: str
    file_paths: List[str]
    model_id: str
    settings: StrikeSettings = StrikeSettings()

# Global registry for active mission streams (Live Wire)
# batch_id -> asyncio.Queue
active_streams: Dict[str, asyncio.Queue] = {}

@router.post("/strike")
async def initiate_mission(req: MissionRequest, background_tasks: BackgroundTasks):
    """Initiate a mission and return batch ID."""
    batch_id = str(uuid.uuid4())[:8]
    
    # 1. Persist to DB
    BatchDB.create_batch(
        batch_id=batch_id,
        name=req.name,
        prompt_path=req.prompt_path,
        model_id=req.model_id,
        total_items=len(req.file_paths),
        settings=req.settings.dict()
    )
    BatchDB.add_items(batch_id, req.file_paths)
    
    # 2. Queue for Live Stream
    active_streams[batch_id] = asyncio.Queue()
    
    # 3. Start background processing
    background_tasks.add_task(orchestrate_mission, batch_id, req)
    
    return {"status": "MISSION_INITIATED", "batch_id": batch_id, "items": len(req.file_paths)}

@router.get("/stream/{batch_id}")
async def stream_mission(batch_id: str, request: Request):
    """SSE stream for real-time mission telemetry."""
    if batch_id not in active_streams:
        # Check if it exists in DB (to allow re-connecting for history/state)
        # For now, if it's not in active_streams, it's either done or invalid
        batch = BatchDB.get_batch(batch_id)
        if not batch:
            raise HTTPException(status_code=404, detail="Mission not found")
        
    async def event_generator():
        queue = active_streams.get(batch_id)
        if not queue:
            # Send final state if already done
            yield f"data: {json.dumps({'type': 'system', 'content': 'MISSION_ALREADY_COMPLETE'})}\n\n"
            return

        try:
            while True:
                if await request.is_disconnected():
                    break
                
                try:
                    # Give it a timeout so we can check for disconnects
                    data = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield f"data: {json.dumps(data)}\n\n"
                    if data.get("type") == "mission_complete":
                        break
                except asyncio.TimeoutError:
                    # Keep-alive
                    yield ": keep-alive\n\n"
                    continue
        finally:
            # We don't necessarily want to remove from active_streams here
            # because multiple clients might be watching the same mission.
            # But for this implementation, we'll keep it simple.
            pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")

async def orchestrate_mission(batch_id: str, req: MissionRequest):
    """The core orchestrator logic."""
    queue = active_streams.get(batch_id)
    if not queue: return

    try:
        # Load prompt
        prompt_content = ""
        prompt_path = Path(req.prompt_path)
        if prompt_path.exists():
            prompt_content = prompt_path.read_text(encoding="utf-8")
        else:
            await queue.put({"type": "error", "content": f"Prompt not found: {req.prompt_path}"})
            BatchDB.update_batch_status(batch_id, "ABORTED")
            return

        BatchDB.update_batch_status(batch_id, "RUNNING")
        await queue.put({"type": "system", "content": f"MISSION_IGNITION_{batch_id}"})

        model_config = next((m for m in MODEL_REGISTRY if m.id == req.model_id), None)
        if not model_config:
            await queue.put({"type": "error", "content": f"Unknown model: {req.model_id}"})
            BatchDB.update_batch_status(batch_id, "ABORTED")
            return

        # Fetch batch items from DB to get their IDs
        batch_data = BatchDB.get_batch(batch_id)
        items = batch_data['items']

        for item in items:
            item_id = item['id']
            file_path = item['file_path']
            
            await queue.put({"type": "item_start", "id": item_id, "file": file_path})
            BatchDB.update_item(item_id, "PROCESSING")

            # 1. Read file
            try:
                payload = Path(file_path).read_text(encoding="utf-8", errors="replace")
                final_prompt = prompt_content.replace("{{payload}}", payload) if "{{payload}}" in prompt_content else f"{prompt_content}\n\nPAYLOAD:\n{payload}"
            except Exception as e:
                await queue.put({"type": "error", "content": f"File read error: {file_path}"})
                BatchDB.update_item(item_id, "ERROR", error=str(e))
                continue

            # 2. Execute streaming strike
            full_response = ""
            start_strike_time = time.time()
            
            try:
                async for event in execute_streaming_strike(
                    gateway=model_config.gateway,
                    model_id=req.model_id,
                    prompt=final_prompt,
                    temperature=req.settings.temperature,
                    max_tokens=req.settings.max_tokens
                ):
                    if event["type"] == "content":
                        full_response += event["content"]
                        await queue.put({"type": "item_chunk", "id": item_id, "content": event["content"]})
                    elif event["type"] == "metadata":
                        # Strike complete
                        latency = (time.time() - start_strike_time)
                        
                        # Process output (YAML/JSON cleanup)
                        data = _parse_refinery_output(full_response)
                        
                        # Save to MissionVault
                        stem = Path(file_path).stem
                        result_path = MISSION_VAULT_DIR / f"{stem}.md"
                        with open(result_path, 'w') as f:
                            f.write("---\n")
                            f.write(yaml.dump(data))
                            f.write("---\n\n")
                            f.write(payload)

                        BatchDB.update_item(
                            item_id=item_id,
                            status="SUCCESS",
                            output_path=str(result_path),
                            tokens=event["usage"].get("total_tokens", 0),
                            latency=latency,
                            raw=full_response
                        )
                        
                        await queue.put({
                            "type": "item_done",
                            "id": item_id,
                            "metadata": event
                        })
                    elif event["type"] == "error":
                        await queue.put({"type": "item_error", "id": item_id, "content": event["content"]})
                        BatchDB.update_item(item_id, "ERROR", error=event["content"])

            except Exception as e:
                await queue.put({"type": "item_error", "id": item_id, "content": str(e)})
                BatchDB.update_item(item_id, "ERROR", error=str(e))

        BatchDB.update_batch_status(batch_id, "COMPLETED")
        await queue.put({"type": "mission_complete", "batch_id": batch_id})

    finally:
        # Cleanup active stream after a delay to allow final events to drain
        await asyncio.sleep(60)
        if batch_id in active_streams:
            del active_streams[batch_id]

def _parse_refinery_output(raw_content: str) -> Dict:
    """Helper to parse LLM output into metadata dict."""
    data = {}
    # Try JSON
    json_match = re.search(r'```json\n(.*?)\n```', raw_content, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group(1))
        except: pass
    
    if not data:
        # Try YAML
        clean_yaml = ""
        if "---" in raw_content:
            parts = raw_content.split("---")
            clean_yaml = parts[1] if len(parts) > 1 else raw_content
        else:
            clean_yaml = raw_content
        
        clean_yaml = re.sub(r'^```yaml\n', '', clean_yaml)
        clean_yaml = re.sub(r'\n```$', '', clean_yaml)
        try:
            data = yaml.safe_load(clean_yaml)
        except: pass
        
    if not isinstance(data, dict):
        data = {"summary": "Parsing failed", "raw_extracted": str(data)}
        
    return data
