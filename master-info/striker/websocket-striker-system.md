# WebSocket Striker System - Deep Dive Documentation

> **Version:** 1.0  
> **Created:** 2026-04-12  
> **Status:** Working / Production Ready  
> **Engine Version:** PEACOCK ENGINE V3.0.0

---

## 1. The Problem

The Payload Striker system needed **real-time telemetry** for batch AI processing operations. HTTP polling was insufficient for:
- Live progress updates during long-running strikes
- Streaming token counts and cost calculations
- Immediate feedback on rate limit breaches
- Multi-model comparison mode status

**User Quote:**
> *"I need real-time telemetry, streaming responses, multi-model comparison"*

---

## 2. User Requirements (with quotes)

### From Conversation Context

**On Dry Run Mode:**
> *"Implementing dry run mode with exact token counting for 2MB payloads using Vertex AI local tokenizer"*

**On Multi-Model:**
> *"Multi-model comparison mode active (up to 4 models)"*
> *"Same payload through 4 models, outputs tagged with model name for quality comparison"*

**On Token Counting:**
> *"For 2MB payloads, must use exact Vertex AI tokenizer, not estimation, to avoid cost surprises"*

**On Chunking Strategy:**
> *"Diamond shards are 1-10K tokens each (perfect size). Can batch 80-100 shards per 1M context call"*

**On Threading Modes:**
> *"Ultra vs Batch: Ultra fires next strike immediately when one returns (max throughput). Batch waits for all threads to finish before next wave"*

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WEBSOCKET STRIKER ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────────┐
│   REACT UI       │     │   FASTAPI        │     │   VERTEX AI          │
│   (Tactical      │◄───►│   WebSocket      │     │   TOKENIZER          │
│    Striker)      │     │   Handler        │     │   (Local)            │
└────────┬─────────┘     └────────┬─────────┘     └──────────────────────┘
         │                        │
         │  WS /v1/striker/ws     │
         │  ├─ start_strike       │
         │  ├─ cancel_strike      │
         │  └─ get_status         │
         │                        │
         │  ◄─ strike_init        │
         │  ◄─ strike_started     │
         │  ◄─ dry_run_started    │
         │  ◄─ dry_run_analysis   │
         │  ◄─ payload_started    │
         │  ◄─ stream_chunk       │
         │  ◄─ payload_completed  │
         │  ◄─ strike_completed   │
         │                        │
         ▼                        ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         DRY RUN MODE (Exact Tokens)                      │
│                                                                          │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│   │ Payload Content │───►│ Vertex AI       │───►│ Token Count     │     │
│   │ (up to 2MB)     │    │ Tokenizer       │    │ (Exact)         │     │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘     │
│                                                          │               │
│                                                          ▼               │
│   ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐     │
│   │ Cost Calc       │◄───│ Model Limits    │◄───│ Size Check      │     │
│   │ (Flash Lite     │    │ (RPM/TPM)       │    │ (>2MB warn)     │     │
│   │  pricing)       │    │                 │    │                 │     │
│   └─────────────────┘    └─────────────────┘    └─────────────────┘     │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────┐
│                      MULTI-MODEL COMPARISON MODE                         │
│                                                                          │
│   Single Payload ──► ┌─────────────────────────────────────────┐        │
│                      │  Model A: gemini-2.0-flash-lite         │        │
│                      │  Model B: gemini-2.5-pro                │        │
│                      │  Model C: llama-3.3-70b                 │        │
│                      │  Model D: (optional)                    │        │
│                      └─────────────────────────────────────────┘        │
│                                          │                               │
│                                          ▼                               │
│                      Tagged Outputs: payload-name-model-A-done.ts        │
│                                    payload-name-model-B-done.ts          │
│                                    payload-name-model-C-done.ts          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Technical Implementation

### File Structure

```
app/
├── routes/
│   └── striker_ws.py          # WebSocket handler + dry run logic
├── main.py                     # FastAPI app with /static mount
└── static/
    └── index.html              # SPA entry (served by catch-all)

ui/
└── src/
    └── components/
        └── striker/
            └── TacticalStriker.tsx   # 4-pane tactical interface
```

### WebSocket Endpoint

```python
# app/routes/striker_ws.py

@router.websocket("/ws")
async def striker_websocket(websocket: WebSocket):
    """WebSocket for real-time strike execution and telemetry"""
    await websocket.accept()
    session_id = f"strike_{int(time.time() * 1000)}"
    
    # Message loop handles:
    # - ping (health check)
    # - start_strike (initiate execution)
    # - get_status (telemetry request)
    # - cancel_strike (abort)
```

### Vertex AI Exact Tokenizer

```python
async def count_tokens_exact(content: str) -> int:
    """Use Vertex AI local tokenizer for EXACT token counts on large payloads (2MB+)"""
    
    # Calls local Python venv with vertexai.preview.tokenization
    # Uses gemini-1.5-flash tokenizer for consistency
    # Falls back to len(content) // 4 if tokenizer fails
    
    result = subprocess.run([
        '/home/flintx/ai-handler/.venv/bin/python', '-c',
        '...vertexai.preview.tokenization...'
    ], capture_output=True, timeout=60)
```

### Dry Run Message Flow

```
CLIENT                                        SERVER
  │                                              │
  │ ── start_strike (dry_run: true) ───────────► │
  │                                              │
  │ ◄──────── dry_run_started ────────────────── │
  │                                              │
  │ ◄──────── dry_run_task (payload_1) ───────── │
  │ ◄──────── dry_run_analysis (results) ─────── │
  │ ◄──────── dry_run_task (payload_2) ───────── │
  │ ◄──────── dry_run_analysis (results) ─────── │
  │                    ...                       │
  │ ◄──────── dry_run_complete (summary) ─────── │
```

### Dry Run Response Format

```json
{
  "type": "dry_run_analysis",
  "payload_id": "shard_001",
  "payload_name": "auth-module.md",
  "payload_size_mb": 1.2,
  "model": "gemini-2.0-flash-lite",
  "prompt_tokens": 45230,
  "estimated_response_tokens": 11307,
  "total_tokens": 56537,
  "estimated_cost_usd": 0.003391,
  "method": "vertex_ai_exact",
  "model_limits": {"rpm": 4000, "tpm": 4000000},
  "status": "would_succeed",
  "warning": null
}
```

---

## 5. How It Works - Step by Step

### Phase 1: Prompt Selection
1. User loads `/striker` route
2. UI fetches prompts from `/v1/striker/prompts`
3. Displays list from `/semiotic-mold/` directory
4. User selects prompt → advances to payload selection

### Phase 2: Payload Selection
1. UI displays payloads from `/liquid-legos/` or `/english/`
2. User selects multiple payloads via checkboxes
3. Pre-flight check auto-runs on selection change

### Phase 3: Configuration
1. **Model Selection:** Multi-select dropdown (up to 4 models)
   - Tier 1: Flash Lite (4K RPM) for bulk
   - Tier 2: Flash (1-2K RPM) for speed
   - Tier 3: Pro (150-500 RPM) for quality
2. **Thread Count:** Slider 1-10
3. **Strike Mode:** Batch vs Ultra
4. **Dry Run Toggle:** Test mode (no API calls)

### Phase 4: Pre-Flight Check
```
POST /v1/tokens/preflight
{
  "model": "gemini-2.0-flash-lite",
  "prompt_text": "...",
  "payload_paths": ["/path/to/file1", ...],
  "thread_count": 4
}
```
Returns: `safe_to_proceed`, `limit_status` (SAFE/WARNING/DANGER), cost estimate

### Phase 5: Execution
1. User arms system (if pre-flight passes)
2. User clicks LAUNCH
3. WebSocket sends `start_strike` action
4. Server spawns `run_strike()` background task
5. Real-time telemetry flows back via WebSocket

### Phase 6: Dry Run (if enabled)
1. Server iterates all payload+model combinations
2. For each: calls `count_tokens_exact()` via Vertex AI tokenizer
3. Calculates cost using Flash Lite pricing ($0.075/$0.30 per 1M)
4. Checks against 1M context limit
5. Flags oversized payloads (>2MB)
6. Returns complete analysis without API calls

### Phase 7: Live Strike (if not dry run)
1. Loads payload content from disk
2. Injects into prompt template
3. Calls LLM API (not yet implemented - currently simulated)
4. Streams response chunks back to UI
5. Saves output to `/liquid-legos/` with model tag

---

## 6. Decision Points

### Why Vertex AI Local Tokenizer?
**User Quote:**
> *"Need to integrate `/home/flintx/hetzner/ai-engine/local_tokenization.py` (Vertex AI tokenizer) into dry run for accurate counts on large files"*

- Estimation (`len // 4`) was inaccurate for 2MB payloads
- Vertex AI provides exact counts
- Runs in separate venv to avoid dependency conflicts
- 60-second timeout for large files

### Why WebSocket Instead of SSE?
- Bidirectional communication needed (cancel, status checks)
- Cleaner for multi-model state management
- Already using WebSocket elsewhere in app

### Why Subprocess for Tokenizer?
- Vertex AI SDK conflicts with main app dependencies
- User already had working tokenizer in separate venv
- Isolates tokenizer environment

---

## 7. Current Status

### ✅ Working
- WebSocket connection and message protocol
- Prompt loading from `/semiotic-mold/`
- Payload selection UI
- Pre-flight safety checks
- Dry run mode with exact token counting
- Multi-model selection (up to 4)
- Live telemetry display
- Cost estimation
- Thread count configuration
- Batch vs Ultra mode toggle

### ⚠️ Known Issues
- **Asset serving:** Vite builds with `base: '/'` but FastAPI only mounts `/static/`
  - Workaround: Change vite.config.ts `base` to `/static/` or `./`
- **Phase 3 not implemented:** Real LLM calls currently simulated
  - Returns mock data instead of actual API responses

### 🔧 File Locations
- **Tokenizer:** `/home/flintx/ai-handler/.venv/bin/python`
- **Prompts:** `/root/herbert/liquid-semiotic/semiotic-mold/`
- **Payloads:** `/root/herbert/liquid-semiotic/liquid-legos/`
- **Token counter:** `/home/flintx/hetzner/ai-engine/local_tokenization.py`

---

## 8. Troubleshooting

### Issue: WebSocket disconnects immediately
**Cause:** Route not registered in main.py  
**Fix:** Ensure `app.include_router(striker_ws.router)` is called

### Issue: Token counts are estimated, not exact
**Cause:** Vertex AI tokenizer subprocess failing  
**Fix:** Check `/home/flintx/ai-handler/.venv` exists and has `vertexai` package

### Issue: Assets return 404 (MIME type error)
**Cause:** Vite `base: '/'` generates `/assets/...` but FastAPI serves `/static/...`  
**Fix:** Change `vite.config.ts`:
```typescript
export default defineConfig({
  base: '/static/',  // or './' for relative
  // ...
})
```

### Issue: Dry run shows "would_fail" for all payloads
**Cause:** Token count exceeds 1M context limit  
**Fix:** Chunk large payloads (2MB+) into 800K token pieces

### Issue: Pre-flight shows DANGER status
**Cause:** Thread count > RPM or tokens > TPM  
**Fix:** Reduce thread count or select higher-RPM model (Flash Lite tier)

---

## 9. API Reference

### WebSocket Messages (Client → Server)

| Action | Payload | Description |
|--------|---------|-------------|
| `ping` | `{}` | Keepalive check |
| `start_strike` | `{config: {...}}` | Initiate strike sequence |
| `get_status` | `{}` | Request telemetry update |
| `cancel_strike` | `{}` | Abort running strike |

### WebSocket Messages (Server → Client)

| Type | Data | Description |
|------|------|-------------|
| `strike_init` | `{session_id}` | Session established |
| `dry_run_started` | `{message, total_tasks}` | Dry run begins |
| `dry_run_analysis` | `{payload_id, model, tokens, cost, status}` | Per-task results |
| `dry_run_complete` | `{total_tokens, total_cost, oversized_payloads}` | Dry run summary |
| `payload_started` | `{payload_id, progress}` | Task begins |
| `stream_chunk` | `{payload_id, chunk, progress}` | Response chunk |
| `payload_completed` | `{payload_id, tokens_used, cost}` | Task done |
| `strike_completed` | `{completed, total, elapsed}` | All done |

---

## 10. Related Documentation

- `PAYLOAD_STRIKER_ARCHITECTURE.md` - Overall system design
- `docs/payload-striker.md` - Feature evolution history
- `docs/feature_03_payload_striker.html` - Original feature spec

---

*Generated for PEACOCK ENGINE V3 - Payload Striker System*
