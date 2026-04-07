import os
import re
import json
import yaml
import time
import asyncio
import hashlib
import logging
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from collections import defaultdict
from app.core.striker import execute_strike
from app.config import MODEL_REGISTRY

router = APIRouter()

# --- CONFIG ---
# Dynamically find project root (3 levels up from this file)
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
BASE_DIR = PROJECT_ROOT / "chat_logs"
WASHED_DIR = BASE_DIR / "washed"
MISSION_VAULT_DIR = PROJECT_ROOT / "MissionVault"
MISFIRE_DIR = BASE_DIR / "misfires"
STATUS_FILE = PROJECT_ROOT / "striker_status.json"

# Ensure dirs exist
MISSION_VAULT_DIR.mkdir(parents=True, exist_ok=True)
MISFIRE_DIR.mkdir(parents=True, exist_ok=True)

# --- TYPES ---
class GenesisIntel(BaseModel):
    completeness: int
    contextType: str
    buildStatus: str
    logicUsed: str
    troublesSolved: str
    realWorldPainPoint: str
    marketPotential: str
    sellable: bool
    portfolioWorthy: bool
    isAppSeed: bool

class StrikerFile(BaseModel):
    name: str
    path: str
    size: int
    status: str = "pending"
    signalIntensity: int = 0

class StrikerResult(BaseModel):
    file: str
    title: str
    summary: str
    category: str
    priority: str
    keywords: List[str]
    raw: Optional[dict] = None
    genesis: Optional[GenesisIntel] = None

class StrikerTelemetry(BaseModel):
    currentFile: Optional[str] = None
    lastResult: Optional[StrikerResult] = None
    nextFile: Optional[str] = None
    processedCount: int = 0
    totalCount: int = 0
    isPaused: bool = False
    isRunning: bool = False
    proxyIP: str = "127.0.0.1"
    logs: List[str] = []
    totalPromptTokens: int = 0
    totalCompletionTokens: int = 0
    totalTokens: int = 0
    rpm: float = 0.0
    tpm: float = 0.0
    rpd: int = 0

class StrikerRequest(BaseModel):
    files: List[str]
    prompt: str
    modelId: str
    delay: int = 5
    throttle: float = 1.0

# --- STATE (GLOBAL) ---
class StrikerState:
    def __init__(self):
        self.telemetry = StrikerTelemetry(logs=[])
        self.is_running = False
        self.is_paused = False
        self.load_initial_status()

    def load_initial_status(self):
        try:
            if STATUS_FILE.exists():
                with open(STATUS_FILE, 'r') as f:
                    data = json.load(f)
                    self.telemetry = StrikerTelemetry(**data)
                    # Reset run state on boot for safety
                    self.telemetry.isRunning = False
                    self.telemetry.isPaused = False
        except Exception as e:
            print(f"Error loading status: {e}")

state = StrikerState()

def add_log(text: str):
    state.telemetry.logs.append(text)
    if len(state.telemetry.logs) > 500:
        state.telemetry.logs.pop(0)

def save_status():
    with open(STATUS_FILE, 'w') as f:
        json.dump(state.telemetry.dict(), f, indent=2)

def normalize_name(filename):
    name = filename.lower()
    name = re.sub(r'^(branch_of_|copy_of_|copy\.of\.)+', '', name)
    name = re.sub(r'^\d{8}\.', '', name)
    name = Path(name).stem
    return name.strip()

def get_short_hash(content: str):
    return hashlib.sha256(content.encode()).hexdigest()[:8]

# --- ENDPOINTS ---

@router.get("/files")
async def list_striker_files(base_dir: Optional[str] = "/home/flintx/chat_logs"):
    target_path = Path(base_dir)
    if not target_path.exists():
        return []
        
    intel_pool = defaultdict(list)
    extensions = {'.md', '.json', '.txt'}
    
    for root, dirs, files in os.walk(target_path):
        for file in files:
            path = Path(root) / file
            if path.suffix.lower() in extensions:
                root_name = normalize_name(file)
                intel_pool[root_name].append({
                    'path': str(path),
                    'size': path.stat().st_size,
                    'name': file
                })

    final = []
    for root_name, versions in intel_pool.items():
        winner = max(versions, key=lambda x: x['size'])
        
        # Check if already processed
        washed_path = WASHED_DIR / winner['name']
        vault_path = MISSION_VAULT_DIR / winner['name']
        is_cleansed = washed_path.exists() or vault_path.exists()
        
        # Calculate signal intensity (count of code blocks)
        signal = 0
        try:
            with open(winner['path'], 'r', errors='ignore') as f:
                content = f.read()
                signal = content.count('```') // 2
        except:
            pass
            
        final.append({
            "name": winner['name'],
            "path": winner['path'],
            "size": winner['size'],
            "status": "success" if is_cleansed else "pending",
            "signalIntensity": signal
        })
    return final

@router.get("/status")
async def get_striker_status():
    return state.telemetry

@router.post("/execute")
async def execute_striker(req: StrikerRequest, background_tasks: BackgroundTasks):
    if state.is_running:
        raise HTTPException(status_code=400, detail="Strike already in progress")
    
    state.is_running = True
    state.is_paused = False
    state.telemetry.isRunning = True
    state.telemetry.isPaused = False
    state.telemetry.totalCount = len(req.files)
    state.telemetry.processedCount = 0
    state.telemetry.logs = []
    
    background_tasks.add_task(run_striker_batch, req)
    return {"status": "STRIKE_INITIATED", "target_count": len(req.files)}

@router.post("/pause")
async def pause_striker():
    state.is_paused = True
    state.telemetry.isPaused = True
    add_log("[SYS] :: MISSION_PAUSED_BY_USER")
    save_status()
    return {"status": "paused"}

@router.post("/resume")
async def resume_striker():
    state.is_paused = False
    state.telemetry.isPaused = False
    add_log("[SYS] :: MISSION_RESUMED")
    save_status()
    return {"status": "resumed"}

@router.post("/abort")
async def abort_striker():
    state.is_running = False
    state.is_paused = False
    state.telemetry.isRunning = False
    state.telemetry.isPaused = False
    return {"status": "ABORTED"}

@router.get("/target/{filename}")
async def get_target_intel(filename: str):
    path = MISSION_VAULT_DIR / filename
    if not path.exists():
        # Try with .md if it doesn't have it
        if not path.suffix:
            path = path.with_suffix(".md")
        
    if not path.exists():
        raise HTTPException(status_code=404, detail="Target not found in vault")
        
    try:
        with open(path, 'r') as f:
            content = f.read()
            
        if content.startswith("---"):
            parts = content.split("---")
            if len(parts) >= 3:
                metadata = yaml.safe_load(parts[1])
                # Return a partial StrikerResult
                return {
                    "file": filename,
                    "title": metadata.get("title", filename),
                    "summary": metadata.get("summary", ""),
                    "category": metadata.get("primary_category", metadata.get("stage", "Uncategorized")),
                    "priority": metadata.get("priority", "Normal"),
                    "keywords": metadata.get("search_keywords", []),
                    "genesis": metadata # The metadata contains the genesis fields
                }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading vault asset: {str(e)}")
        
    return {"status": "error", "message": "Failed to parse vault metadata"}

# --- ENGINE ---

async def run_striker_batch(req: StrikerRequest):
    add_log(f"[SYS] :: INITIATING_IMPERIAL_STRIKE... TARGETS: {len(req.files)}")
    start_time = time.time()
    
    for i, file_path in enumerate(req.files):
        if not state.is_running: break
        while state.is_paused:
            await asyncio.sleep(1)
            if not state.is_running: break
        
        path = Path(file_path)
        state.telemetry.currentFile = path.name
        state.telemetry.nextFile = req.files[i+1] if i+1 < len(req.files) else "NONE"
        
        try:
            with open(path, 'r', errors='ignore') as f:
                content = f.read()
            
            # --- THE STRIKE ---
            add_log(f"[API] :: STRIKING_{path.name}...")
            
            # Prepare payload with {{payload}} injection
            final_prompt = req.prompt.replace("{{payload}}", content) if "{{payload}}" in req.prompt else f"{req.prompt}\n\nPAYLOAD:\n{content}"
            
            # Direct internal call
            model_config = next((m for m in MODEL_REGISTRY if m.id == req.modelId), None)
            if not model_config:
                raise Exception(f"Unknown Model ID: {req.modelId}")
            
            add_log(f"STRIKE_REQ | {path.name[:20].ljust(20)} | {req.modelId[:12]}")
            
            start_req_time = time.time()
            result_data = await execute_strike(
                gateway=model_config.gateway,
                model_id=req.modelId,
                prompt=final_prompt,
                temp=0.3
            )
            latency = round(time.time() - start_req_time, 2)
            
            raw_content = result_data.get("content", "")
            state.telemetry.proxyIP = result_data.get("ipUsed", "ROTATING_PROXY")
            usage = result_data.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            asset = result_data.get("keyUsed", "UNKNOWN")
            
            try:
                data = {}
                # Try parsing JSON first (Genesis Scout Format)
                json_match = re.search(r'```json\n(.*?)\n```', raw_content, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                    except: pass
                
                # If no JSON or parsing failed, try YAML (Legacy Refractor Format)
                if not data:
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

                if not isinstance(data, dict): raise Exception("Invalid response structure")
                
                # --- WELD & PREPEND ---
                short_hash = get_short_hash(content)
                data['id'] = short_hash
                
                # Prepend to original and save as .md
                result_path = MISSION_VAULT_DIR / f"{path.stem}.md"
                with open(result_path, 'w') as f:
                    f.write("---\n")
                    f.write(yaml.dump(data))
                    f.write("---\n\n")
                    f.write(content)
                
                # Genesis mapping
                genesis_data = None
                if 'completeness' in data:
                    try:
                        genesis_data = GenesisIntel(**data)
                    except:
                        # Fallback if structure is slightly off
                        pass

                # Update telemetry
                result = StrikerResult(
                    file=path.name,
                    title=data.get('title', 'UNTITLED'),
                    summary=data.get('summary', 'No summary.'),
                    category=data.get('primary_category', data.get('stage', 'Uncategorized')),
                    priority=data.get('priority', 'Winner' if data.get('isAppSeed') else 'Normal'),
                    keywords=data.get('search_keywords', []),
                    raw=data,
                    genesis=genesis_data
                )
                state.telemetry.lastResult = result
                state.telemetry.processedCount += 1
                add_log(f"[HIT] {path.name} // {latency}s // {tokens}T // ASSET:{asset}")
                
            except Exception as e:
                # MISFIRE BIN
                error_msg = str(e)
                add_log(f"[ERR] :: MISFIRE_{path.name}... {error_msg}")
                misfire_path = MISFIRE_DIR / f"{path.name}.failed.txt"
                with open(misfire_path, 'w') as f:
                    f.write(f"ERROR: {error_msg}\n\n")
                    f.write("RAW_OUTPUT:\n")
                    f.write(raw_content)
                
            # Update telemetry usage
            usage = result_data.get("usage", {})
            state.telemetry.totalPromptTokens += usage.get("prompt_tokens", 0)
            state.telemetry.totalCompletionTokens += usage.get("completion_tokens", 0)
            state.telemetry.totalTokens += usage.get("total_tokens", 0)
            
            # Simple average rate calculation (Requests/Min and Tokens/Min)
            # We can use the start time of the batch to calculate these
            elapsed_mins = (time.time() - start_time) / 60
            if elapsed_mins > 0:
                state.telemetry.rpm = round(state.telemetry.processedCount / elapsed_mins, 1)
                state.telemetry.tpm = round(state.telemetry.totalTokens / elapsed_mins, 0)
                state.telemetry.rpd = state.telemetry.processedCount # Simplified session-based count
            
        except Exception as e:
            add_log(f"[ERR] :: CRITICAL_FAILURE_{path.name}... {str(e)}")
            
        save_status()
        
        # Calculate effective delay: delay * (1 / throttle)
        # throttle = 2.0 (200%) means delay is halved (2x faster)
        # throttle = 0.5 (50%) means delay is doubled (2x slower)
        effective_delay = req.delay / max(req.throttle, 0.01)
        await asyncio.sleep(effective_delay)
    
    state.is_running = False
    state.telemetry.isRunning = False
    add_log("[SYS] :: BATCH_STRIKE_MISSION_COMPLETE")
    save_status()
