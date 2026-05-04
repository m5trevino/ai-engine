"""
AVIARY — The Bird Pipeline

Strictly compartmentalized 7-phase compiler:
  SPARK  → Distill chat log into specification
  FALCON → Mine invariants from specification
  EAGLE  → Create implementation plan from invariants
  CROW   → Design complete UI scaffold from plan
  OWL    → Generate code file by file
  RAVEN  → Audit code, route fixes back if needed
  HAWK   → Package for deployment

Compartmentalization rule: Each bird sees ONLY the output of the previous bird.
No bird sees the original chat log, the overall project, or any other bird's output
except its direct predecessor.

RAVEN can loop back to OWL (max 2 retries). If RAVEN routes to EAGLE or CROW,
the pipeline halts with a detailed fix report.

Every LLM call is logged verbosely. Every action is streamed in real-time.
Every file OWL generates rings a note: do-re-mi-fa-so-la-ti-do, climbing octaves.
"""

import os
import json
import time
import uuid
import asyncio
import re
from typing import List, Dict, Optional, Any, AsyncGenerator
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime

from app.core.key_manager import GroqPool, GooglePool
from app.core.memory_engine import query_memory
from app.utils.formatter import CLIFormatter
from openai import AsyncOpenAI


PROMPT_DIR = Path(__file__).parent.parent.parent.resolve() / "prompts" / "aviary"

# ─── Tone Scale: do re mi fa so la ti do ──────────────────────────────
SCALE = ["do", "re", "mi", "fa", "so", "la", "ti"]
BASE_FREQUENCIES = {
    "do": 261.63, "re": 293.66, "mi": 329.63, "fa": 349.23,
    "so": 392.00, "la": 440.00, "ti": 493.88,
}


def _tone_for_file_index(index: int) -> Dict[str, Any]:
    """Map file index to a musical tone, climbing octaves every 7 files."""
    octave = index // 7
    note_idx = index % 7
    note = SCALE[note_idx]
    base_freq = BASE_FREQUENCIES[note]
    freq = base_freq * (2 ** octave)
    return {
        "note": note,
        "octave": octave + 4,
        "frequency": round(freq, 2),
        "index": index,
    }


def _load_prompt(name: str) -> str:
    path = PROMPT_DIR / f"{name}.md"
    if path.exists():
        return path.read_text(encoding="utf-8")
    raise FileNotFoundError(f"Prompt not found: {name}")


def _log_event(run_id: str, bird: str, event_type: str, detail: Dict[str, Any]):
    """Verbose structured logging for every action."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    entry = {
        "timestamp": timestamp,
        "run_id": run_id,
        "bird": bird,
        "event": event_type,
        "detail": detail,
    }
    print(json.dumps(entry), flush=True)
    return entry


async def _call_llm(
    run_id: str,
    bird: str,
    system_prompt: str,
    user_prompt: str,
    model_id: str = "llama-3.3-70b-versatile",
    max_tokens: int = 4096,
    gateway: str = "groq",
) -> str:
    """Fire a single LLM call via key pool with full verbose logging."""
    if gateway == "google":
        asset = GooglePool.get_next()
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
    else:
        asset = GroqPool.get_next()
        base_url = "https://api.groq.com/openai/v1"
    
    client = AsyncOpenAI(base_url=base_url, api_key=asset.key)
    
    _log_event(run_id, bird, "llm_request", {
        "model": model_id,
        "gateway": gateway,
        "max_tokens": max_tokens,
        "system_length": len(system_prompt),
        "user_length": len(user_prompt),
        "key_mask": asset.key[:8] + "..." if asset.key else "none",
    })
    
    start = time.time()
    try:
        resp = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.0,
            max_tokens=max_tokens,
        )
        output = resp.choices[0].message.content or ""
        latency_ms = int((time.time() - start) * 1000)
        usage = resp.usage
        
        _log_event(run_id, bird, "llm_response", {
            "model": model_id,
            "gateway": gateway,
            "latency_ms": latency_ms,
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
            "output_length": len(output),
            "finish_reason": resp.choices[0].finish_reason,
        })
        return output
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        _log_event(run_id, bird, "llm_error", {
            "model": model_id,
            "gateway": gateway,
            "latency_ms": latency_ms,
            "error": str(e),
            "error_type": type(e).__name__,
        })
        raise
    finally:
        await client.close()


# ─── Event Streaming ────────────────────────────────────────────────────

@dataclass
class AviaryEvent:
    run_id: str
    bird: str
    event_type: str
    message: str
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_sse(self) -> str:
        return f"data: {json.dumps({'run_id': self.run_id, 'bird': self.bird, 'event': self.event_type, 'message': self.message, 'payload': self.payload, 'timestamp': self.timestamp})}\n\n"


@dataclass
class AviaryPhase:
    name: str
    status: str = "pending"
    input_preview: str = ""
    output_text: str = ""
    tokens_used: int = 0
    latency_ms: int = 0
    error: str = ""
    retry_count: int = 0


@dataclass
class AviaryResult:
    run_id: str
    conversation_id: str
    source_path: str
    phases: List[AviaryPhase] = field(default_factory=list)
    files: List[Dict[str, str]] = field(default_factory=list)
    deploy_script: str = ""
    readme: str = ""
    manifest: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    total_tokens: int = 0
    total_duration_ms: int = 0
    errors: List[str] = field(default_factory=list)
    raven_audit_log: List[Dict[str, Any]] = field(default_factory=list)
    raven_approved: bool = False
    event_log: List[Dict[str, Any]] = field(default_factory=list)


async def _emit(
    queue: asyncio.Queue,
    run_id: str,
    bird: str,
    event_type: str,
    message: str,
    payload: Optional[Dict[str, Any]] = None,
):
    event = AviaryEvent(
        run_id=run_id,
        bird=bird,
        event_type=event_type,
        message=message,
        payload=payload or {},
    )
    await queue.put(event.to_sse())


# ─── PHASE 1: SPARK ─────────────────────────────────────────────────────

def _count_tokens(text: str) -> int:
    """Count tokens using Google's Vertex AI tokenizer (accurate for Gemini)."""
    try:
        from vertexai.preview import tokenization
        tokenizer = tokenization.get_tokenizer_for_model("gemini-1.5-flash")
        return tokenizer.count_tokens(text).total_tokens
    except Exception:
        # Fallback: rough estimate (4 chars per token)
        return len(text) // 4


async def _phase_spark(
    run_id: str,
    queue: asyncio.Queue,
    chat_log_text: str,
    memory_context: str = "",
    bucket_metadata: List[Dict[str, Any]] = None,
    model_id: Optional[str] = None,
    gateway: Optional[str] = None,
) -> AviaryPhase:
    phase = AviaryPhase(name="spark")
    phase.status = "running"
    phase.input_preview = chat_log_text[:200] + "..."
    
    await _emit(queue, run_id, "spark", "phase_start", "🔥 SPARK igniting... reading full payload and building ontology", {
        "input_length": len(chat_log_text),
        "memory_enabled": bool(memory_context),
        "bucket_items": len(bucket_metadata) if bucket_metadata else 0,
    })
    CLIFormatter.info(f"[PEACOCK {run_id}] 🔥 SPARK igniting...")
    
    start = time.time()
    system = _load_prompt("spark")
    
    # Build metadata block from bucket items
    metadata_block = ""
    if bucket_metadata:
        for idx, item in enumerate(bucket_metadata[:20]):
            meta = item.get("metadata", {})
            metadata_block += f"\n- ITEM {idx+1}: collection={item.get('collection','unknown')}, doc_id={item.get('doc_id','unknown')}"
            if meta.get("project"):
                metadata_block += f", project={meta['project']}"
            if meta.get("technologies"):
                metadata_block += f", technologies={meta['technologies']}"
            if meta.get("entities"):
                metadata_block += f", entities={meta['entities']}"
            if meta.get("topics"):
                metadata_block += f", topics={meta['topics']}"
            if meta.get("decisions"):
                metadata_block += f", decisions={meta['decisions']}"
            if meta.get("action_items"):
                metadata_block += f", action_items={meta['action_items']}"
    else:
        metadata_block = "- No structured metadata available"
    
    # Few-shot examples create the statistical groove
    examples = """=== EXAMPLE 1 ===
[[[CHAT_LOG]]]
Project: RMS App Setup
Vault: chatgpt
Topics: specific app, Runtime Mobile Security, app identification, installation, setup
Technologies: Runtime Mobile Security (RMS)
Entities: RMS app
Sentiment: curious
Complexity: simple
Conversation role: learning
Idea maturity: embryonic

Content:
║  USER MSG 002 ║
its a specific app
║  CHATGPT MSG 002 ║
Got it! If you're referring to a specific app...
[[[METADATA]]]
- No prior decisions
- No existing codebase
[[[ONTOLOGY]]]
### PROJECT: RMS App Setup
### STAGE: start
### GOALS:
- Identify and set up Runtime Mobile Security app
- Understand app identification and installation process
### TECH_STACK: Runtime Mobile Security (RMS)
### ENTITIES: RMS app
### DECISIONS:
- DEC-01: RMS chosen as target platform for mobile security analysis
### RISKS:
- ID-01: App not yet identified - need specific name
### ACTION_ITEMS:
- Provide specific app name for RMS analysis
=== END ===

=== EXAMPLE 2 ===
[[[CHAT_LOG]]]
Project: Android SDK package management
Vault: chatgpt
Topics: Android SDK, package management, build tools, system images, NDK, Google APIs
Technologies: Android, Android SDK, Google APIs, CMake, NDK
Entities: Google, Android
Sentiment: neutral
Complexity: moderate
Conversation role: creating
Idea maturity: mature
Contains heredoc (text)

Content:
Available Packages:
  Path | Version | Description
  build-tools;34.0.0 | 34.0.0 | Android SDK Build-Tools
  platform-tools | 35.0.0 | Android SDK Platform-Tools
  ndk;26.1.10909125 | 26.1.10909125 | NDK
[[[METADATA]]]
- Prior context: user setting up Android dev environment
- Existing codebase: none yet
[[[ONTOLOGY]]]
### PROJECT: Android SDK Package Manager
### STAGE: middle
### GOALS:
- Manage Android SDK packages (build tools, platform tools, NDK)
- Install correct versions for target platform
### TECH_STACK: Android SDK, CMake, NDK, Google APIs
### ENTITIES: Google, Android, BuildTools, PlatformTools, NDK
### DECISIONS:
- DEC-01: Android SDK build-tools 34.0.0 selected
- DEC-02: NDK 26.1.10909125 selected for native compilation
### RISKS:
- VER-01: Version mismatch between SDK components
- NDK-01: CMake compatibility with selected NDK version
### ACTION_ITEMS:
- Verify installed SDK component versions
- Test NDK build with CMake
=== END ===

=== EXAMPLE 3 ===
[[[CHAT_LOG]]]
Project: Restaurant Phone AI
Vault: claude
Topics: AI phone system, POS integration, webhook, restaurant automation
Technologies: OpenAI API, REST API, Webhooks, Square API
Entities: Restaurant, POS, PhoneAgent, Order, MenuItem
Sentiment: excited
Complexity: moderate
Conversation role: planning
Idea maturity: developing

Content:
USER: I want to build a restaurant phone system that uses AI to take orders
CLAUDE: For production you'd use enterprise APIs like OpenAI or Anthropic
USER: How do I connect it to my existing POS?
CLAUDE: You'll need a webhook endpoint that forwards order data to your POS API
[[[METADATA]]]
- Prior context: exploring AI automation for restaurant
- Existing codebase: none
- Constraints: must integrate with existing POS (Square/Toast/Clover)
[[[ONTOLOGY]]]
### PROJECT: AI Restaurant Phone System
### STAGE: start
### GOALS:
- Build AI phone agent for restaurant order taking
- Integrate with existing POS system via webhooks
- Support Square, Toast, and Clover APIs
### TECH_STACK: OpenAI API, REST API, Webhooks, Square API, Toast API, Clover API
### ENTITIES: Restaurant, POS, PhoneAgent, Order, MenuItem, Webhook
### DECISIONS:
- DEC-01: Enterprise API chosen over self-hosted for reliability
- DEC-02: Webhook pattern chosen for POS integration
- DEC-03: Multi-POS support (Square, Toast, Clover) required
### RISKS:
- POS-01: POS API rate limits may throttle orders
- REL-01: Phone system downtime = lost revenue
- INT-01: POS API schema differences between vendors
### ACTION_ITEMS:
- Research Square/Toast/Clover API docs
- Set up webhook endpoint
- Test voice latency with chosen API
- Design failover for POS API unavailability
=== END ==="""
    
    user = f"""{examples}

=== INPUT ===
[[[CHAT_LOG]]]
{chat_log_text[:80000]}
[[[METADATA]]]
{metadata_block}
[[[ONTOLOGY]]]
### PROJECT:"""
    
    if memory_context:
        user += f"\n\n=== MEMORY CONTEXT ===\n{memory_context[:3000]}\n=== END MEMORY ==="
    
    try:
        # Count tokens for accurate gateway routing
        total_tokens = _count_tokens(user)
        await _emit(queue, run_id, "spark", "token_count", f"📊 Total tokens: {total_tokens:,}", {
            "total_tokens": total_tokens,
            "payload_tokens": _count_tokens(chat_log_text),
        })
        
        # Route based on token count if not explicitly provided
        if not gateway or not model_id:
            if total_tokens > 900000:
                raise Exception(f"Payload too large: {total_tokens:,} tokens exceeds Gemini 2.5 Pro limit (~1M)")
            elif total_tokens > 100000:
                gateway = "google"
                model_id = "models/gemini-2.5-pro"
                await _emit(queue, run_id, "spark", "gateway_switch", f"🔄 {total_tokens:,} tokens → Gemini 2.5 Pro (1M context)")
            else:
                gateway = "groq"
                model_id = "llama-3.3-70b-versatile"
        else:
            await _emit(queue, run_id, "spark", "gateway_switch", f"🔄 Using selected model: {model_id} ({gateway})")
        
        output = await _call_llm(run_id, "spark", system, user, model_id=model_id, max_tokens=4096, gateway=gateway)
        phase.output_text = output
        phase.status = "complete"
        phase.latency_ms = int((time.time() - start) * 1000)
        
        await _emit(queue, run_id, "spark", "phase_complete", "✨ SPARK complete — ontology built", {
            "output_length": len(output),
            "latency_ms": phase.latency_ms,
            "gateway": gateway,
        })
        CLIFormatter.success(f"[PEACOCK {run_id}] ✨ SPARK complete ({phase.latency_ms}ms)")
        
    except Exception as e:
        phase.status = "failed"
        phase.error = str(e)
        phase.latency_ms = int((time.time() - start) * 1000)
        await _emit(queue, run_id, "spark", "error", f"💥 SPARK failed: {e}", {"error": str(e)})
        CLIFormatter.error(f"[PEACOCK {run_id}] 💥 SPARK failed: {e}")
    
    return phase


# ─── PHASE 2: FALCON ────────────────────────────────────────────────────

async def _phase_falcon(
    run_id: str,
    queue: asyncio.Queue,
    spark_output: str,
) -> AviaryPhase:
    phase = AviaryPhase(name="falcon")
    phase.status = "running"
    phase.input_preview = spark_output[:200] + "..."
    
    await _emit(queue, run_id, "falcon", "phase_start", "🦅 FALCON diving... mining invariants from specification", {
        "input_length": len(spark_output),
    })
    CLIFormatter.info(f"[PEACOCK {run_id}] 🦅 FALCON diving...")
    
    start = time.time()
    system = _load_prompt("falcon")
    
    # Few-shot examples: ontology → invariants
    falcon_examples = """=== EXAMPLE 1 ===
[[[ONTOLOGY]]]
### PROJECT: RMS App Setup
### STAGE: start
### GOALS:
- Identify and set up Runtime Mobile Security app
### TECH_STACK: Runtime Mobile Security (RMS)
### ENTITIES: RMS app
### DECISIONS:
- DEC-01: RMS chosen as target platform for mobile security analysis
### RISKS:
- ID-01: App not yet identified - need specific name
[[[INVARIANTS]]]
### STRUCTURAL INVARIANTS
- INV-S01 [CRITICAL]: All mobile security analysis must use RMS as the target platform | Evidence: DEC-01
### BEHAVIORAL INVARIANTS
- INV-B01 [STANDARD]: App identification must be completed before installation analysis begins | Evidence: ID-01
### INTEGRATION INVARIANTS
- None
### SECURITY INVARIANTS
- INV-SEC01 [CRITICAL]: RMS runtime permissions must be validated before dynamic analysis | Evidence: DEC-01
=== END ===

=== EXAMPLE 2 ===
[[[ONTOLOGY]]]
### PROJECT: Android SDK Package Manager
### STAGE: middle
### GOALS:
- Manage Android SDK packages
### TECH_STACK: Android SDK, CMake, NDK, Google APIs
### ENTITIES: Google, Android, BuildTools, PlatformTools, NDK
### DECISIONS:
- DEC-01: Android SDK build-tools 34.0.0 selected
- DEC-02: NDK 26.1.10909125 selected for native compilation
### RISKS:
- VER-01: Version mismatch between SDK components
- NDK-01: CMake compatibility with selected NDK version
[[[INVARIANTS]]]
### STRUCTURAL INVARIANTS
- INV-S01 [CRITICAL]: NDK version must match CMake compatibility matrix | Evidence: NDK-01
### BEHAVIORAL INVARIANTS
- INV-B01 [STANDARD]: SDK component versions must be validated before build | Evidence: VER-01
### INTEGRATION INVARIANTS
- INV-I01 [CRITICAL]: All POS integrations must support webhook fallback | Evidence: DEC-02
### SECURITY INVARIANTS
- None
=== END ==="""
    
    user = f"""{falcon_examples}

=== INPUT ===
[[[ONTOLOGY]]]
{spark_output[:12000]}
[[[INVARIANTS]]]
### STRUCTURAL INVARIANTS"""
    
    try:
        output = await _call_llm(run_id, "falcon", system, user, max_tokens=4096)
        phase.output_text = output
        phase.status = "complete"
        phase.latency_ms = int((time.time() - start) * 1000)
        
        await _emit(queue, run_id, "falcon", "phase_complete", "🎯 FALCON complete — invariants mined", {
            "output_length": len(output),
            "latency_ms": phase.latency_ms,
        })
        CLIFormatter.success(f"[PEACOCK {run_id}] 🎯 FALCON complete ({phase.latency_ms}ms)")
        
    except Exception as e:
        phase.status = "failed"
        phase.error = str(e)
        phase.latency_ms = int((time.time() - start) * 1000)
        await _emit(queue, run_id, "falcon", "error", f"💥 FALCON failed: {e}", {"error": str(e)})
        CLIFormatter.error(f"[PEACOCK {run_id}] 💥 FALCON failed: {e}")
    
    return phase


# ─── PHASE 3: EAGLE ─────────────────────────────────────────────────────

async def _phase_eagle(
    run_id: str,
    queue: asyncio.Queue,
    falcon_output: str,
) -> AviaryPhase:
    phase = AviaryPhase(name="eagle")
    phase.status = "running"
    phase.input_preview = falcon_output[:200] + "..."
    
    await _emit(queue, run_id, "eagle", "phase_start", "🦅 EAGLE soaring... crafting implementation plan", {
        "input_length": len(falcon_output),
    })
    CLIFormatter.info(f"[PEACOCK {run_id}] 🦅 EAGLE soaring...")
    
    start = time.time()
    system = _load_prompt("eagle")
    user = f"=== INPUT INVARIANTS ===\n{falcon_output[:12000]}\n\n=== END INPUT ==="
    
    try:
        output = await _call_llm(run_id, "eagle", system, user, max_tokens=4096)
        phase.output_text = output
        phase.status = "complete"
        phase.latency_ms = int((time.time() - start) * 1000)
        
        await _emit(queue, run_id, "eagle", "phase_complete", "📐 EAGLE complete — implementation plan ready", {
            "output_length": len(output),
            "latency_ms": phase.latency_ms,
        })
        CLIFormatter.success(f"[PEACOCK {run_id}] 📐 EAGLE complete ({phase.latency_ms}ms)")
        
    except Exception as e:
        phase.status = "failed"
        phase.error = str(e)
        phase.latency_ms = int((time.time() - start) * 1000)
        await _emit(queue, run_id, "eagle", "error", f"💥 EAGLE failed: {e}", {"error": str(e)})
        CLIFormatter.error(f"[PEACOCK {run_id}] 💥 EAGLE failed: {e}")
    
    return phase


# ─── PHASE 4: CROW — UI Scaffold Architect ──────────────────────────────

async def _phase_crow(
    run_id: str,
    queue: asyncio.Queue,
    eagle_output: str,
) -> AviaryPhase:
    phase = AviaryPhase(name="crow")
    phase.status = "running"
    phase.input_preview = eagle_output[:200] + "..."
    
    await _emit(queue, run_id, "crow", "phase_start", "🐦‍⬛ CROW cawing... designing complete UI scaffold", {
        "input_length": len(eagle_output),
    })
    CLIFormatter.info(f"[PEACOCK {run_id}] 🐦‍⬛ CROW cawing...")
    
    start = time.time()
    system = _load_prompt("crow")
    user = f"=== IMPLEMENTATION PLAN ===\n{eagle_output[:12000]}\n\n=== END PLAN ==="
    
    try:
        output = await _call_llm(run_id, "crow", system, user, max_tokens=4096)
        phase.output_text = output
        phase.status = "complete"
        phase.latency_ms = int((time.time() - start) * 1000)
        
        # Parse UI element count for display
        element_count = len(re.findall(r'^Element:', output, re.MULTILINE))
        page_count = len(re.findall(r'^=== PAGE:', output, re.MULTILINE))
        
        await _emit(queue, run_id, "crow", "phase_complete", f"🎨 CROW complete — {page_count} pages, {element_count} UI elements specified", {
            "output_length": len(output),
            "latency_ms": phase.latency_ms,
            "pages": page_count,
            "elements": element_count,
        })
        CLIFormatter.success(f"[PEACOCK {run_id}] 🎨 CROW complete — {page_count} pages, {element_count} elements ({phase.latency_ms}ms)")
        
    except Exception as e:
        phase.status = "failed"
        phase.error = str(e)
        phase.latency_ms = int((time.time() - start) * 1000)
        await _emit(queue, run_id, "crow", "error", f"💥 CROW failed: {e}", {"error": str(e)})
        CLIFormatter.error(f"[PEACOCK {run_id}] 💥 CROW failed: {e}")
    
    return phase


# ─── PHASE 5: OWL — Code Generator (file by file, with tones) ───────────

async def _phase_owl(
    run_id: str,
    queue: asyncio.Queue,
    eagle_output: str,
    crow_output: str,
    fix_instructions: Optional[str] = None,
    file_index_offset: int = 0,
) -> List[Dict[str, str]]:
    await _emit(queue, run_id, "owl", "phase_start", "🦉 OWL awakening... reading plans", {
        "input_length": len(eagle_output),
        "has_ui_scaffold": bool(crow_output),
        "has_fix_instructions": bool(fix_instructions),
    })
    CLIFormatter.info(f"[PEACOCK {run_id}] 🦉 OWL awakening...")
    
    system = _load_prompt("owl")
    
    # Step 1: Ask OWL to list all files needed
    await _emit(queue, run_id, "owl", "llm_call", "📝 OWL listing files...")
    plan_prompt = f"""{system}

=== IMPLEMENTATION PLAN ===
{eagle_output[:8000]}

=== UI SCAFFOLD ===
{crow_output[:4000]}

=== END INPUTS ==="""
    
    if fix_instructions:
        plan_prompt += f"\n\n=== FIX INSTRUCTIONS ===\n{fix_instructions[:2000]}\n=== END FIXES ==="
        await _emit(queue, run_id, "owl", "fix_input", "🔧 OWL received fix instructions from RAVEN", {
            "fix_length": len(fix_instructions),
        })
    
    plan_prompt += """\n\nYour first task: List ALL files that need to be created, one per line, in format:
FILE: path/to/file.py
FILE: path/to/file2.py

Only list files. No code yet."""
    
    file_list_raw = await _call_llm(run_id, "owl", system, plan_prompt, max_tokens=2048)
    
    # Extract file paths
    files_to_generate = []
    for line in file_list_raw.split("\n"):
        if line.strip().startswith("FILE:"):
            path = line.split("FILE:", 1)[1].strip()
            files_to_generate.append(path)
    
    if not files_to_generate:
        files_to_generate = re.findall(r'[\w/]+\.(py|js|ts|go|rs|java|md|txt|json|yaml|yml|toml|sh|html|css|jsx|tsx)', file_list_raw)
    
    await _emit(queue, run_id, "owl", "file_list", f"📋 OWL found {len(files_to_generate)} files to generate", {
        "files": files_to_generate,
    })
    CLIFormatter.info(f"[PEACOCK {run_id}] 📋 OWL will generate {len(files_to_generate)} files")
    
    generated_files = []
    for idx, fpath in enumerate(files_to_generate[:12]):
        tone = _tone_for_file_index(file_index_offset + idx)
        
        await _emit(queue, run_id, "owl", "file_start", f"🔨 OWL carving {fpath}...", {
            "file": fpath,
            "index": file_index_offset + idx,
        })
        
        gen_prompt = f"""{system}

=== IMPLEMENTATION PLAN ===
{eagle_output[:6000]}

=== UI SCAFFOLD ===
{crow_output[:3000]}

Generate ONLY this file: {fpath}

Output EXACTLY:
```{_lang_from_path(fpath)}
# {fpath}
[full file content]
```

NO EXPLANATION. ONLY CODE."""
        
        if fix_instructions:
            gen_prompt += f"\n\n=== FIX INSTRUCTIONS (APPLY TO THIS FILE IF RELEVANT) ===\n{fix_instructions[:1500]}\n=== END FIXES ==="
        
        try:
            code_raw = await _call_llm(run_id, "owl", system, gen_prompt, max_tokens=4096)
            match = re.search(r'```(?:\w+)?\n(.*?)\n```', code_raw, re.DOTALL)
            if match:
                content = match.group(1)
            else:
                content = code_raw
            
            generated_files.append({"path": fpath, "content": content})
            
            await _emit(queue, run_id, "owl", "file_complete", f"🎵 {fpath} complete — {tone['note'].upper()}-{tone['octave']} ({tone['frequency']}Hz)", {
                "file": fpath,
                "tone": tone,
                "content_length": len(content),
            })
            await _emit(queue, run_id, "owl", "tone_played", f"🎶 {tone['note'].upper()}-{tone['octave']}", {
                "tone": tone,
                "file": fpath,
            })
            CLIFormatter.success(f"[PEACOCK {run_id}] 🎵 {fpath} ({tone['note'].upper()}-{tone['octave']})")
            
        except Exception as e:
            generated_files.append({"path": fpath, "content": f"# ERROR generating {fpath}: {e}"})
            await _emit(queue, run_id, "owl", "file_error", f"💥 {fpath} failed: {e}", {
                "file": fpath,
                "error": str(e),
            })
            CLIFormatter.error(f"[PEACOCK {run_id}] 💥 {fpath} failed: {e}")
    
    await _emit(queue, run_id, "owl", "phase_complete", f"✅ OWL complete — {len(generated_files)} files generated", {
        "file_count": len(generated_files),
    })
    CLIFormatter.success(f"[PEACOCK {run_id}] ✅ OWL complete — {len(generated_files)} files")
    
    return generated_files


def _lang_from_path(path: str) -> str:
    ext = path.split(".")[-1].lower() if "." in path else ""
    mapping = {
        "py": "python", "js": "javascript", "ts": "typescript",
        "jsx": "jsx", "tsx": "tsx", "html": "html", "css": "css",
        "go": "go", "rs": "rust", "java": "java", "sh": "bash",
        "json": "json", "yaml": "yaml", "yml": "yaml", "toml": "toml",
        "md": "markdown", "txt": "text",
    }
    return mapping.get(ext, "")


# ─── PHASE 6: RAVEN — Code Auditor & Fix Router ─────────────────────────

async def _phase_raven(
    run_id: str,
    queue: asyncio.Queue,
    eagle_output: str,
    crow_output: str,
    files: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    RAVEN audits all files. Returns:
    - approved: bool
    - fix_instructions: str (if routing to OWL)
    - route_to: "owl" | "eagle" | "crow" | None
    - audit_log: list of issues
    """
    await _emit(queue, run_id, "raven", "phase_start", "🐦‍⬛ RAVEN inspecting... auditing every line of code", {
        "file_count": len(files),
        "total_lines": sum(len(f["content"].split("\n")) for f in files),
    })
    CLIFormatter.info(f"[PEACOCK {run_id}] 🐦‍⬛ RAVEN inspecting {len(files)} files...")
    
    system = _load_prompt("raven")
    
    # Build file contents block
    files_block = ""
    for f in files:
        files_block += f"\n=== FILE: {f['path']} ===\n{f['content'][:3000]}\n"
    
    user = f"""=== IMPLEMENTATION PLAN ===
{eagle_output[:4000]}

=== UI SCAFFOLD ===
{crow_output[:3000]}

=== GENERATED FILES ===
{files_block}

=== END INPUTS ===

Audit every file. Report every issue. Route fixes to the correct bird."""
    
    start = time.time()
    try:
        output = await _call_llm(run_id, "raven", system, user, max_tokens=4096)
        latency_ms = int((time.time() - start) * 1000)
        
        # Parse result
        approved = "RAVEN_APPROVED" in output
        
        # Count issues
        issue_count = len(re.findall(r'^=== ISSUE:', output, re.MULTILINE))
        critical_count = len(re.findall(r'Severity: critical', output))
        
        # Extract fix routing
        route_to = None
        fix_instructions = ""
        if not approved:
            if "Target bird: owl" in output.lower():
                route_to = "owl"
                # Extract fix instructions for owl
                fix_match = re.search(r'=== FIX INSTRUCTION ===.*?Instructions:\s*(.*?)(?=\n===|$)', output, re.DOTALL)
                if fix_match:
                    fix_instructions = fix_match.group(1).strip()
            elif "Target bird: eagle" in output.lower():
                route_to = "eagle"
            elif "Target bird: crow" in output.lower():
                route_to = "crow"
        
        result = {
            "approved": approved,
            "route_to": route_to,
            "fix_instructions": fix_instructions,
            "output": output,
            "issue_count": issue_count,
            "critical_count": critical_count,
            "latency_ms": latency_ms,
        }
        
        if approved:
            await _emit(queue, run_id, "raven", "phase_complete", f"✅ RAVEN APPROVED — {len(files)} files clean ({latency_ms}ms)", {
                "latency_ms": latency_ms,
                "files_audited": len(files),
                "issues": 0,
            })
            CLIFormatter.success(f"[PEACOCK {run_id}] ✅ RAVEN APPROVED ({latency_ms}ms)")
        else:
            await _emit(queue, run_id, "raven", "audit_fail", f"⚠️ RAVEN found {issue_count} issues ({critical_count} critical) → routing to {route_to}", {
                "issues": issue_count,
                "critical": critical_count,
                "route_to": route_to,
                "latency_ms": latency_ms,
            })
            CLIFormatter.warning(f"[PEACOCK {run_id}] ⚠️ RAVEN found {issue_count} issues → {route_to}")
        
        return result
        
    except Exception as e:
        latency_ms = int((time.time() - start) * 1000)
        await _emit(queue, run_id, "raven", "error", f"💥 RAVEN audit failed: {e}", {"error": str(e)})
        CLIFormatter.error(f"[PEACOCK {run_id}] 💥 RAVEN failed: {e}")
        return {
            "approved": False,
            "route_to": None,
            "fix_instructions": "",
            "output": f"Audit failed: {e}",
            "issue_count": 0,
            "critical_count": 0,
            "latency_ms": latency_ms,
            "error": str(e),
        }


# ─── PHASE 7: HAWK — Deployment Packager ────────────────────────────────

async def _phase_hawk(
    run_id: str,
    queue: asyncio.Queue,
    files: List[Dict[str, str]],
) -> Dict[str, str]:
    await _emit(queue, run_id, "hawk", "phase_start", "🦅 HAWK descending... packaging for deployment", {
        "file_count": len(files),
    })
    CLIFormatter.info(f"[PEACOCK {run_id}] 🦅 HAWK descending...")
    
    system = _load_prompt("hawk")
    files_desc = "\n".join([f"- {f['path']}" for f in files])
    user = f"=== CODE FILES ===\n{files_desc}\n\nGenerate deploy script and README."
    
    try:
        output = await _call_llm(run_id, "hawk", system, user, max_tokens=4096)
    except Exception as e:
        output = f"# Deploy script generation failed: {e}"
        await _emit(queue, run_id, "hawk", "error", f"💥 HAWK LLM call failed: {e}", {"error": str(e)})
    
    deploy = output
    readme = "# Generated Project\n\nSee deploy script for setup instructions."
    
    await _emit(queue, run_id, "hawk", "phase_complete", "📦 HAWK complete — deploy package ready", {
        "deploy_length": len(deploy),
        "readme_length": len(readme),
    })
    CLIFormatter.success(f"[PEACOCK {run_id}] 📦 HAWK complete")
    
    return {"deploy_script": deploy, "readme": readme, "raw": output}


# ─── MAIN ORCHESTRATOR ──────────────────────────────────────────────────

async def run_aviary_pipeline(
    chat_log_text: str,
    conversation_id: str = "",
    source_path: str = "",
    enable_memory: bool = True,
    memory_collections: Optional[List[str]] = None,
    bucket_metadata: Optional[List[Dict[str, Any]]] = None,
    model_id: Optional[str] = None,
    gateway: Optional[str] = None,
) -> AviaryResult:
    """Run the full Aviary pipeline. Returns final result (no streaming)."""
    run_id = f"aviary_{uuid.uuid4().hex[:12]}"
    result = AviaryResult(
        run_id=run_id,
        conversation_id=conversation_id,
        source_path=source_path,
    )
    start_time = time.time()
    queue = asyncio.Queue()
    
    # Gather memory context if enabled — feeds ONLY SPARK
    memory_context = ""
    if enable_memory:
        try:
            mem_result = await query_memory(
                query=chat_log_text[:500],
                collections=memory_collections or ["app_invariants", "agent_invariants", "tech_vault"],
                n=3,
            )
            memory_context = mem_result.get("context", "")
            _log_event(run_id, "aviary", "memory_loaded", {"context_length": len(memory_context)})
        except Exception as e:
            _log_event(run_id, "aviary", "memory_failed", {"error": str(e)})
    
    # === PHASE 1: SPARK ===
    spark = await _phase_spark(run_id, queue, chat_log_text, memory_context, bucket_metadata)
    result.phases.append(spark)
    if spark.status == "failed":
        result.status = "failed"
        result.errors.append(f"SPARK failed: {spark.error}")
        return result
    
    # === PHASE 2: FALCON ===
    falcon = await _phase_falcon(run_id, queue, spark.output_text)
    result.phases.append(falcon)
    if falcon.status == "failed":
        result.status = "failed"
        result.errors.append(f"FALCON failed: {falcon.error}")
        return result
    
    # === PHASE 3: EAGLE ===
    eagle = await _phase_eagle(run_id, queue, falcon.output_text)
    result.phases.append(eagle)
    if eagle.status == "failed":
        result.status = "failed"
        result.errors.append(f"EAGLE failed: {eagle.error}")
        return result
    
    # === PHASE 4: CROW ===
    crow = await _phase_crow(run_id, queue, eagle.output_text)
    result.phases.append(crow)
    if crow.status == "failed":
        result.status = "failed"
        result.errors.append(f"CROW failed: {crow.error}")
        return result
    
    # === PHASE 5: OWL ===
    try:
        files = await _phase_owl(run_id, queue, eagle.output_text, crow.output_text)
        result.files = files
    except Exception as e:
        result.status = "failed"
        result.errors.append(f"OWL failed: {e}")
        return result
    
    # === PHASE 6: RAVEN (with loopback) ===
    raven_retries = 0
    max_raven_retries = 2
    while raven_retries <= max_raven_retries:
        raven = await _phase_raven(run_id, queue, eagle.output_text, crow.output_text, result.files)
        result.raven_audit_log.append({
            "attempt": raven_retries + 1,
            "approved": raven["approved"],
            "route_to": raven["route_to"],
            "issues": raven["issue_count"],
            "critical": raven["critical_count"],
        })
        
        if raven["approved"]:
            result.raven_approved = True
            break
        
        if raven["route_to"] == "owl" and raven_retries < max_raven_retries:
            raven_retries += 1
            await _emit(queue, run_id, "aviary", "loopback", f"🔄 RAVEN → OWL (retry {raven_retries}/{max_raven_retries})", {
                "retry": raven_retries,
                "max_retries": max_raven_retries,
            })
            CLIFormatter.info(f"[PEACOCK {run_id}] 🔄 RAVEN → OWL retry {raven_retries}")
            
            # Regenerate files with fix instructions
            try:
                files = await _phase_owl(
                    run_id, queue, eagle.output_text, crow.output_text,
                    fix_instructions=raven["fix_instructions"],
                    file_index_offset=len(result.files),
                )
                result.files = files
            except Exception as e:
                result.status = "failed"
                result.errors.append(f"OWL retry failed: {e}")
                return result
        else:
            # Cannot auto-fix, halt pipeline
            result.status = "failed"
            result.errors.append(f"RAVEN audit failed. Route to: {raven['route_to']}. Issues: {raven['issue_count']}")
            if raven["route_to"] in ("eagle", "crow"):
                result.errors.append("Architectural fixes required. Manual intervention needed.")
            return result
    
    # === PHASE 7: HAWK ===
    try:
        package = await _phase_hawk(run_id, queue, result.files)
        result.deploy_script = package["deploy_script"]
        result.readme = package["readme"]
    except Exception as e:
        result.errors.append(f"HAWK failed: {e}")
    
    result.status = "complete"
    result.total_duration_ms = int((time.time() - start_time) * 1000)
    result.total_tokens = sum(p.tokens_used for p in result.phases)
    
    CLIFormatter.success(f"[PEACOCK {run_id}] 🏁 Pipeline complete. {len(result.files)} files. {result.total_duration_ms}ms.")
    return result


async def run_aviary_pipeline_streamed(
    chat_log_text: str,
    conversation_id: str = "",
    source_path: str = "",
    enable_memory: bool = True,
    memory_collections: Optional[List[str]] = None,
    bucket_metadata: Optional[List[Dict[str, Any]]] = None,
    model_id: Optional[str] = None,
    gateway: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """Run the full Aviary pipeline with real-time SSE streaming."""
    run_id = f"aviary_{uuid.uuid4().hex[:12]}"
    queue: asyncio.Queue = asyncio.Queue()
    result = AviaryResult(
        run_id=run_id,
        conversation_id=conversation_id,
        source_path=source_path,
    )
    
    async def _orchestrator():
        start_time = time.time()
        
        # Gather memory context if enabled — feeds ONLY SPARK
        memory_context = ""
        if enable_memory:
            try:
                mem_result = await query_memory(
                    query=chat_log_text[:500],
                    collections=memory_collections or ["app_invariants", "agent_invariants", "tech_vault"],
                    n=3,
                )
                memory_context = mem_result.get("context", "")
                await _emit(queue, run_id, "aviary", "memory_loaded", "🧠 Memory context loaded", {
                    "context_length": len(memory_context),
                })
            except Exception as e:
                await _emit(queue, run_id, "aviary", "memory_failed", f"🧠 Memory load failed: {e}", {"error": str(e)})
        
        await _emit(queue, run_id, "aviary", "pipeline_start", "🚀 PEACOCK LAUNCHED — SPARK → FALCON → EAGLE → CROW → OWL → RAVEN → HAWK", {
            "run_id": run_id,
            "input_length": len(chat_log_text),
        })
        
        # === PHASE 1: SPARK ===
        spark = await _phase_spark(run_id, queue, chat_log_text, memory_context, bucket_metadata, model_id, gateway)
        result.phases.append(spark)
        if spark.status == "failed":
            result.status = "failed"
            result.errors.append(f"SPARK failed: {spark.error}")
            await _emit(queue, run_id, "aviary", "pipeline_failed", "💥 PEACOCK aborted — SPARK failed", {"error": spark.error})
            return
        
        # === PHASE 2: FALCON ===
        falcon = await _phase_falcon(run_id, queue, spark.output_text)
        result.phases.append(falcon)
        if falcon.status == "failed":
            result.status = "failed"
            result.errors.append(f"FALCON failed: {falcon.error}")
            await _emit(queue, run_id, "aviary", "pipeline_failed", "💥 PEACOCK aborted — FALCON failed", {"error": falcon.error})
            return
        
        # === PHASE 3: EAGLE ===
        eagle = await _phase_eagle(run_id, queue, falcon.output_text)
        result.phases.append(eagle)
        if eagle.status == "failed":
            result.status = "failed"
            result.errors.append(f"EAGLE failed: {eagle.error}")
            await _emit(queue, run_id, "aviary", "pipeline_failed", "💥 PEACOCK aborted — EAGLE failed", {"error": eagle.error})
            return
        
        # === PHASE 4: CROW ===
        crow = await _phase_crow(run_id, queue, eagle.output_text)
        result.phases.append(crow)
        if crow.status == "failed":
            result.status = "failed"
            result.errors.append(f"CROW failed: {crow.error}")
            await _emit(queue, run_id, "aviary", "pipeline_failed", "💥 PEACOCK aborted — CROW failed", {"error": crow.error})
            return
        
        # === PHASE 5: OWL ===
        try:
            files = await _phase_owl(run_id, queue, eagle.output_text, crow.output_text)
            result.files = files
        except Exception as e:
            result.status = "failed"
            result.errors.append(f"OWL failed: {e}")
            await _emit(queue, run_id, "aviary", "pipeline_failed", "💥 PEACOCK aborted — OWL failed", {"error": str(e)})
            return
        
        # === PHASE 6: RAVEN (with loopback) ===
        raven_retries = 0
        max_raven_retries = 2
        while raven_retries <= max_raven_retries:
            raven = await _phase_raven(run_id, queue, eagle.output_text, crow.output_text, result.files)
            result.raven_audit_log.append({
                "attempt": raven_retries + 1,
                "approved": raven["approved"],
                "route_to": raven["route_to"],
                "issues": raven["issue_count"],
                "critical": raven["critical_count"],
            })
            
            if raven["approved"]:
                result.raven_approved = True
                await _emit(queue, run_id, "raven", "audit_passed", "✅ RAVEN approved after audit", {
                    "attempts": raven_retries + 1,
                })
                break
            
            if raven["route_to"] == "owl" and raven_retries < max_raven_retries:
                raven_retries += 1
                await _emit(queue, run_id, "aviary", "loopback", f"🔄 RAVEN → OWL (retry {raven_retries}/{max_raven_retries})", {
                    "retry": raven_retries,
                    "max_retries": max_raven_retries,
                })
                try:
                    files = await _phase_owl(
                        run_id, queue, eagle.output_text, crow.output_text,
                        fix_instructions=raven["fix_instructions"],
                        file_index_offset=len(result.files),
                    )
                    result.files = files
                except Exception as e:
                    result.status = "failed"
                    result.errors.append(f"OWL retry failed: {e}")
                    await _emit(queue, run_id, "aviary", "pipeline_failed", "💥 PEACOCK aborted — OWL retry failed", {"error": str(e)})
                    return
            else:
                result.status = "failed"
                result.errors.append(f"RAVEN audit failed. Route to: {raven['route_to']}. Issues: {raven['issue_count']}")
                await _emit(queue, run_id, "aviary", "pipeline_failed", f"💥 PEACOCK aborted — RAVEN routed to {raven['route_to']}", {
                    "route_to": raven["route_to"],
                    "issues": raven["issue_count"],
                    "critical": raven["critical_count"],
                })
                return
        
        # === PHASE 7: HAWK ===
        try:
            package = await _phase_hawk(run_id, queue, result.files)
            result.deploy_script = package["deploy_script"]
            result.readme = package["readme"]
        except Exception as e:
            result.errors.append(f"HAWK failed: {e}")
        
        result.status = "complete"
        result.total_duration_ms = int((time.time() - start_time) * 1000)
        result.total_tokens = sum(p.tokens_used for p in result.phases)
        
        await _emit(queue, run_id, "aviary", "pipeline_complete", f"🏁 PEACOCK LANDED — {len(result.files)} files in {result.total_duration_ms}ms", {
            "file_count": len(result.files),
            "duration_ms": result.total_duration_ms,
            "total_tokens": result.total_tokens,
            "raven_approved": result.raven_approved,
            "raven_attempts": len(result.raven_audit_log),
        })
        
        _AVIARY_JOBS[run_id] = result
    
    task = asyncio.create_task(_orchestrator())
    
    done = False
    while not done:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=0.5)
            yield event
        except asyncio.TimeoutError:
            if task.done():
                while not queue.empty():
                    yield await queue.get()
                done = True
    
    yield f"data: {json.dumps({'run_id': run_id, 'bird': 'aviary', 'event': 'stream_end', 'message': 'Stream closed', 'payload': {'status': result.status, 'file_count': len(result.files), 'raven_approved': result.raven_approved}})}\n\n"


# ─── In-memory store for completed runs ─────────────────────────────────
_AVIARY_JOBS: Dict[str, AviaryResult] = {}


def get_aviary_result(run_id: str) -> Optional[AviaryResult]:
    return _AVIARY_JOBS.get(run_id)


def result_to_json(result: AviaryResult) -> Dict[str, Any]:
    return {
        "run_id": result.run_id,
        "status": result.status,
        "conversation_id": result.conversation_id,
        "source_path": result.source_path,
        "phases": [
            {
                "name": p.name,
                "status": p.status,
                "latency_ms": p.latency_ms,
                "error": p.error,
                "output_preview": p.output_text[:500] + "..." if len(p.output_text) > 500 else p.output_text,
            }
            for p in result.phases
        ],
        "files": result.files,
        "deploy_script": result.deploy_script,
        "readme": result.readme,
        "raven_approved": result.raven_approved,
        "raven_audit_log": result.raven_audit_log,
        "manifest": {
            "file_count": len(result.files),
            "total_duration_ms": result.total_duration_ms,
            "total_tokens": result.total_tokens,
            "errors": result.errors,
            "raven_approved": result.raven_approved,
            "raven_attempts": len(result.raven_audit_log),
        },
        "errors": result.errors,
    }
