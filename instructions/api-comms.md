# API Communications System - Deep Dive Documentation

> **Version:** 1.0  
> **Created:** 2026-04-10  
> **Status:** Production Ready  
> **Engine Version:** PEACOCK ENGINE V3.0.0

---

## 1. The Problem

The API Communications system solves the fundamental challenge of **unified AI model access** across multiple providers (Google/Gemini, Groq, DeepSeek, Mistral) through a single, consistent interface.

### Key Problems Addressed:

- **Multi-gateway complexity** - Each AI provider has different SDKs, authentication, and response formats
- **Real-time streaming needs** - Applications need token-by-token streaming, not just blocking responses
- **Bidirectional communication** - Chat interfaces need persistent connections with configuration updates
- **File context injection** - Code analysis and document review require local file content in prompts
- **Structured output requirements** - Applications need JSON, Pydantic models, not just raw text
- **API discoverability** - New developers need to understand available endpoints without reading source code

---

## 2. User Requirements (with quotes from evolution documents)

### From Evolution Document: Feature 04 - API & Comms

> **"Standard request-response cycle. UI freezes while waiting for the full AI response."**

The original problem - blocking HTTP requests create poor user experience.

> **"Implemented a Server-Sent Events endpoint (/v1/chat/stream) for one-way real-time streaming. This allowed the UI to hydrate chat bubbles as tokens arrived."**

Critical requirement: Real-time streaming via SSE to enable live UI updates.

> **"Pivoted to a more robust, bidirectional WebSocket protocol (/ws/ws). This fixed 'Connection Lost' errors and enabled more complex real-time communication, like sending configuration updates from the client."**

Evolution requirement: WebSocket for bidirectional control (config updates, not just streaming).

> **"Expanded the API contract to include advanced generation controls (Temp, TopP, etc.). Added a filesystem bridge (/v1/lim/*) to give the UI secure, direct access to the local OS for the Payload Striker."**

Advanced requirements: Fine-grained parameter control and filesystem integration.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    API COMMUNICATIONS ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │   CLIENTS       │
                              │  (UI / CLI /    │
                              │   External Apps)│
                              └────────┬────────┘
                                       │
              ┌────────────────────────┼────────────────────────┐
              │                        │                        │
              ▼                        ▼                        ▼
    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
    │  REST API       │    │  SSE Streaming  │    │  WebSocket      │
    │  /v1/chat       │    │  /v1/chat/stream│    │  /v1/chat/ws/ws │
    │  (Blocking)     │    │  (Server-Sent   │    │  (Bidirectional)│
    │                 │    │   Events)       │    │                 │
    └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
             │                      │                      │
             └──────────────────────┼──────────────────────┘
                                    │
                                    ▼
                       ┌─────────────────────────┐
                       │   FASTAPI ROUTER        │
                       │   (app/routes/chat.py)  │
                       └───────────┬─────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
         ▼                         ▼                         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  REQUEST        │    │  STREAMING      │    │  WEBSOCKET      │
│  HANDLER        │    │  GENERATOR      │    │  PROTOCOL       │
│                 │    │                 │    │                 │
│ - Validation    │    │ - Async gen     │    │ - Config sync   │
│ - File inject   │    │ - SSE format    │    │ - Chunk stream  │
│ - Strike exec   │    │ - Error handling│    │ - Metadata end  │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │
         └──────────────────────┼──────────────────────┘
                                │
                                ▼
                   ┌───────────────────────┐
                   │   CORE STRIKER        │
                   │   (app/core/          │
                   │    striker.py)        │
                   │                       │
                   │ - Gateway routing     │
                   │ - Key rotation        │
                   │ - Throttle control    │
                   │ - Token counting      │
                   └───────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
    ┌─────────────────┐ ┌─────────┐ ┌─────────────────┐
    │  Google/Gemini  │ │  Groq   │ │  DeepSeek/      │
    │  (GoogleModel)  │ │ (Groq)  │ │  Mistral        │
    │                 │ │         │ │  (OpenAI-compat)│
    └─────────────────┘ └─────────┘ └─────────────────┘
```

### Communication Patterns

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMMUNICATION PATTERNS                        │
└─────────────────────────────────────────────────────────────────┘

PATTERN 1: REST (Blocking)
┌─────────┐                ┌─────────┐                ┌─────────┐
│ Client  │──POST /v1/chat─▶│ FastAPI │───AI Strike───▶│ Model   │
│         │◀───────────────│         │◀───────────────│         │
│         │   JSON Response│         │   Full response│         │
└─────────┘                └─────────┘                └─────────┘

PATTERN 2: SSE (One-way Streaming)
┌─────────┐                ┌─────────┐                ┌─────────┐
│ Client  │─POST /v1/chat/─▶│ FastAPI │───AI Stream───▶│ Model   │
│ (Event  │   stream       │ (Async  │◀───tokens───────│         │
│  Source)│◀─data: {"type": │  Generator)               │         │
│         │    "content":..│         │                │         │
│         │◀─data: {"type": │         │                │         │
│         │    "metadata"..│         │                │         │
└─────────┘                └─────────┘                └─────────┘

PATTERN 3: WebSocket (Bidirectional)
┌─────────┐                ┌─────────┐                ┌─────────┐
│ Client  │────WS /ws/ws───▶│ FastAPI │───AI Stream───▶│ Model   │
│         │◀──{"type":      │ (Maintains│◀──tokens─────│         │
│         │   "info"}       │  session  │                │         │
│         │──▶{"type":      │  config)  │                │         │
│         │   "config"}────▶│         │                │         │
│         │──▶{"type":      │         │                │         │
│         │   "prompt"}────▶│         │                │         │
│         │◀──{"type":      │         │                │         │
│         │   "content"}... │         │                │         │
│         │◀──{"type":      │         │                │         │
│         │   "metadata"}   │         │                │         │
└─────────┘                └─────────┘                └─────────┘
```

---

## 4. Technical Implementation

### 4.1 Core Components

| Component | File | Purpose |
|-----------|------|---------|
| Chat Router | `app/routes/chat.py` | Main API endpoints (REST, SSE, WebSocket) |
| Docs Router | `app/routes/docs.py` | Endpoint discovery and integration guides |
| Core Striker | `app/core/striker.py` | AI execution with streaming support |
| Key Manager | `app/core/key_manager.py` | Multi-gateway key pools |
| Formatter | `app/utils/formatter.py` | CLI output styling |
| Conversation DB | `app/db/database.py` | Chat history persistence |

### 4.2 API Endpoint Reference

| Endpoint | Method | Type | Description |
|----------|--------|------|-------------|
| `/v1/chat` | POST | REST | Blocking chat request |
| `/v1/chat/stream` | POST | SSE | Server-sent events streaming |
| `/v1/chat/ws/ws` | WS | WebSocket | Bidirectional streaming |
| `/v1/chat/models` | GET | REST | List models by gateway |
| `/v1/chat/models/{gateway}` | GET | REST | Gateway-specific models |
| `/v1/docs/endpoints` | GET | REST | Endpoint discovery |
| `/v1/docs/integration-guide` | GET | REST | Quick start guide |
| `/health` | GET | REST | System health check |

### 4.3 Request/Response Models

```python
# Chat Request - supports all three communication patterns
class ChatRequest(BaseModel):
    model: str                    # Model ID from registry
    prompt: str                   # The input text
    timeout: Optional[int]        # Request timeout (seconds)
    title: Optional[str]          # Conversation title
    files: Optional[List[str]]    # Local file paths for context
    format: Literal["text", "json", "pydantic"]  # Output format
    schema_definition: Optional[Dict]  # For pydantic format
    # Generation parameters
    temp: float = 0.7             # Shorthand for temperature
    temperature: Optional[float]  # Full parameter name
    top_p: Optional[float]        # Nucleus sampling
    top_k: Optional[int]          # Top-k sampling
    max_tokens: Optional[int]     # Max output length
    seed: Optional[int]           # Deterministic seed
    presence_penalty: Optional[float]
    frequency_penalty: Optional[float]
    stop: Optional[List[str]]     # Stop sequences
    key: Optional[str]            # Specific key account

# Chat Response - REST only
class ChatResponse(BaseModel):
    content: Any                  # Response (str, dict, or model)
    model: str                    # Model used
    gateway: str                  # Gateway (google, groq, etc.)
    key_used: str                 # Account name (not secret)
    format: str                   # Response format
    usage: Dict[str, int]         # Token counts
    duration_ms: int              # Response time
```

### 4.4 Critical Code Snippets

**File Context Injection:**
```python
# From app/routes/chat.py:113-129
final_prompt = request.prompt
if request.files:
    file_contexts = []
    for file_path in request.files:
        path = Path(file_path)
        if path.exists():
            content = path.read_text(encoding='utf-8', errors='ignore')
            file_contexts.append(f"\n\n--- FILE: {file_path} ---\n{content}")
    if file_contexts:
        final_prompt = f"{request.prompt}\n\nCONTEXT:{''.join(file_contexts)}"
```

**SSE Streaming Generator:**
```python
# From app/routes/chat.py:255-276
async def event_generator():
    try:
        async for chunk in execute_streaming_strike(
            gateway=model_config.gateway,
            model_id=request.model,
            prompt=request.prompt,
            # ... generation parameters
        ):
            yield f"data: {json.dumps(chunk)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**WebSocket Protocol Handler:**
```python
# From app/routes/chat.py:318-407
@router.websocket("/ws/ws")
async def chat_ws(websocket: WebSocket):
    await websocket.accept()
    
    # Session state maintained per connection
    config = {"model": "gemini-2.0-flash-lite", "temp": 0.7, "files": []}
    
    try:
        while True:
            raw_data = await websocket.receive_text()
            data = json.loads(raw_data)
            msg_type = data.get("type")
            
            if msg_type == "config":
                # Update session configuration
                config.update({...})
                await websocket.send_json({"type": "info", ...})
                
            elif msg_type == "prompt":
                # Stream response
                async for chunk in execute_streaming_strike(...):
                    await websocket.send_json({"type": "content", ...})
                # Send completion metadata
                await websocket.send_json({"type": "metadata", ...})
                
    except WebSocketDisconnect:
        CLIFormatter.info("Neural Link Severed (Websocket)")
```

**Precision Strike (Specific Key):**
```python
# From app/routes/chat.py:151-162
if request.key:
    from app.core.striker import execute_precision_strike
    result = await execute_precision_strike(
        gateway=model_config.gateway,
        model_id=request.model,
        prompt=final_prompt,
        target_account=request.key,  # Force specific key
        is_manual=False,
        timeout=request.timeout,
        **gen_params
    )
```

---

## 5. File Structure

```
ai-engine/
├── app/
│   ├── routes/
│   │   ├── chat.py              # Main chat endpoints (REST/SSE/WS)
│   │   ├── chat_api.py          # Additional chat API utilities
│   │   ├── chat_ui.py           # UI-specific chat routes
│   │   ├── docs.py              # Endpoint discovery (/v1/docs/*)
│   │   ├── fs.py                # Filesystem bridge (/v1/fs/*)
│   │   ├── keys.py              # Key management (/v1/keys/*)
│   │   ├── models.py            # Model listing (/v1/models/*)
│   │   └── ...
│   ├── core/
│   │   └── striker.py           # Core execution with streaming
│   ├── utils/
│   │   ├── formatter.py         # CLI output formatting
│   │   └── logger.py            # High-signal logging
│   └── main.py                  # FastAPI app initialization
│
└── docs/deep-dives/
    └── api-comms.md             # This document
```

---

## 6. How It Works - Step by Step

### 6.1 REST API Flow (Blocking)

1. **Client sends POST to /v1/chat**
   ```json
   {
     "model": "gemini-2.5-flash",
     "prompt": "Explain quantum computing",
     "files": ["/path/to/notes.txt"],
     "format": "json"
   }
   ```

2. **FastAPI validates request** using Pydantic `ChatRequest` model

3. **Model lookup** - Find gateway from `MODEL_REGISTRY`

4. **File injection** - Read files, append to prompt with `--- FILE: ---` headers

5. **Execute strike** via `execute_strike()` or `execute_precision_strike()`

6. **Gateway routing** - Core striker selects provider (Google, Groq, etc.)

7. **AI execution** - Pydantic AI Agent runs with retry logic

8. **Response formatting** - Parse JSON if requested format is "json"

9. **Database persistence** - Save conversation to SQLite

10. **Return response**
    ```json
    {
      "content": {"explanation": "Quantum computing uses..."},
      "model": "gemini-2.5-flash",
      "gateway": "google",
      "key_used": "PEACOCK_MAIN",
      "format": "json",
      "usage": {"prompt_tokens": 15, "completion_tokens": 150, "total_tokens": 165},
      "duration_ms": 2340
    }
    ```

### 6.2 SSE Streaming Flow

1. **Client sends POST to /v1/chat/stream**

2. **FastAPI returns StreamingResponse** with `media_type="text/event-stream"`

3. **Async generator starts** `event_generator()` coroutine

4. **Core striker streams** via `execute_streaming_strike()`

5. **For each token chunk:**
   - Receive chunk from AI provider
   - Format as SSE: `data: {"type": "content", "content": "..."}\n\n`
   - Yield to client

6. **Final metadata chunk:**
   ```
   data: {"type": "metadata", "model": "...", "usage": {...}}\n\n
   ```

7. **Connection closes** automatically after final chunk

### 6.3 WebSocket Flow

1. **Client connects** to `ws://localhost:3099/v1/chat/ws/ws`

2. **Server accepts** and initializes session config

3. **Client sends config** (optional):
   ```json
   {"type": "config", "model": "llama-3.3-70b", "temp": 0.5}
   ```
   Server responds: `{"type": "info", "content": "CONFIG_SYNC: llama-3.3-70b"}`

4. **Client sends prompt**:
   ```json
   {"type": "prompt", "content": "Write a haiku about AI"}
   ```

5. **Server streams chunks**:
   ```json
   {"type": "content", "content": "Silicon"}
   {"type": "content", "content": " dreams"}
   {"type": "content", "content": " dance"}
   ...
   ```

6. **Server sends metadata** on completion:
   ```json
   {"type": "metadata", "usage": {"prompt_tokens": 10, "completion_tokens": 15}}
   ```

7. **Connection remains open** for next prompt (step 4)

8. **Disconnect** - Client closes or error triggers cleanup

---

## 7. Decision Points

### Decision: Three Communication Patterns

**Context:** User needed blocking, streaming, and bidirectional options.

**Decision:** **IMPLEMENT ALL THREE**
- REST for simple integrations (`/v1/chat`)
- SSE for one-way streaming (`/v1/chat/stream`)
- WebSocket for bidirectional control (`/v1/chat/ws/ws`)

**Trade-off:** More code to maintain, but maximum flexibility for clients.

---

### Decision: Single Unified Endpoint

**Context:** Could have separate endpoints per gateway (Google, Groq, etc.).

**Decision:** **UNIFIED `/v1/chat` WITH MODEL ID**
- Model ID determines gateway (e.g., "gemini-*" → google, "llama-*" → groq)
- Central registry in `config.py` maps IDs to gateways

**Trade-off:** Simpler API surface, but requires maintaining registry.

---

### Decision: Pydantic for Request/Response Models

**Context:** Need validation and documentation.

**Decision:** **PYDANTIC MODELS WITH FIELD DESCRIPTIONS**
- `ChatRequest` with `Field(..., description="...")`
- `ChatResponse` with consistent structure
- Supports multiple output formats via `format` field

**Trade-off:** Strict validation helps catch errors early, but less flexible than raw dicts.

---

### Decision: File Context via Local Paths

**Context:** Need to inject file content into prompts.

**Decision:** **SERVER-SIDE FILE READING**
- Client sends file paths (not content)
- Server reads from local filesystem
- Content injected with `--- FILE: {path} ---` headers

**Trade-off:** Requires server access to files, but reduces network transfer.

---

### Decision: WebSocket Protocol Design

**Context:** Need bidirectional control beyond just streaming.

**Decision:** **MESSAGE TYPE PROTOCOL**
```json
{"type": "config", ...}   // Update session settings
{"type": "prompt", ...}   // Send prompt, triggers streaming
{"type": "content", ...}  // Response chunk (server→client)
{"type": "metadata", ...} // Final usage stats
{"type": "error", ...}    // Error notification
{"type": "info", ...}     // Status updates
```

**Trade-off:** Simple protocol, but not as feature-rich as GraphQL subscriptions.

---

## 8. Current Status

### ✅ Working

| Feature | Status | Notes |
|---------|--------|-------|
| REST endpoint | ✅ | `/v1/chat` with full parameter support |
| SSE streaming | ✅ | `/v1/chat/stream` with event generator |
| WebSocket | ✅ | `/v1/chat/ws/ws` with session state |
| File injection | ✅ | Local file paths → content injection |
| JSON format | ✅ | Automatic parsing of JSON responses |
| Pydantic format | ✅ | Dynamic schema validation |
| Precision strike | ✅ | Force specific API key account |
| Model discovery | ✅ | `/v1/chat/models` grouped by gateway |
| Endpoint docs | ✅ | `/v1/docs/endpoints` with examples |
| Integration guide | ✅ | `/v1/docs/integration-guide` |
| Health check | ✅ | `/health` with pool status |

### ⚠️ Partial / Considerations

| Feature | Status | Notes |
|---------|--------|-------|
| Token usage in WebSocket | ⚠️ | Estimated from word count, not actual provider counts |
| Database persistence | ⚠️ | REST only, WebSocket/SSE not saved |
| Filesystem bridge | ✅ | `/v1/fs/*` but limited scope (specific directories) |

### ❌ Known Limitations

| Feature | Status | Notes |
|---------|--------|-------|
| WebSocket auth | ❌ | No authentication on WebSocket connections |
| Rate limit headers | ❌ | No X-RateLimit-* headers in responses |
| Request ID propagation | ❌ | No X-Request-ID header support |
| OpenAPI schema | ⚠️ | Partial - some endpoints lack full examples |

### 🐛 Known Issues

1. **WebSocket token estimation** - Uses `len(text.split())` instead of actual tokenizer
2. **No request timeout on streaming** - Client must handle timeouts
3. **File path traversal** - Limited validation of file paths
4. **No connection pooling metrics** - Can't monitor httpx client health
5. **Database failures silent** - Conversation save errors don't fail request

---

## 9. Troubleshooting

### Issue: Streaming stops mid-response

**Symptoms:** SSE or WebSocket connection drops during streaming

**Check:**
```bash
# Check if model is frozen
./ai-engine.py models | grep FROZEN

# Check key cooldown status
./ai-engine.py keys
```

**Causes:**
- Model frozen in registry
- All API keys on cooldown (rate limited)
- Network timeout (reverse proxy/nginx)

**Fix:**
- Unfreeze model: `./ai-engine.py unfreeze {model_id}`
- Wait 60 seconds for cooldown
- Increase proxy timeout settings

---

### Issue: "Unknown model" error

**Symptoms:** 400 error with "Unknown model 'model-name'"

**Check available models:**
```bash
curl http://localhost:3099/v1/chat/models | jq
```

**Causes:**
- Typo in model ID
- Model frozen or deprecated
- Wrong gateway prefix

**Fix:**
- Use exact ID from `/v1/chat/models`
- Check model status in registry

---

### Issue: WebSocket "Connection Lost"

**Symptoms:** Client disconnects unexpectedly

**Check server logs:**
```bash
./run_engine.sh  # Watch for WebSocket error messages
```

**Causes:**
- Invalid JSON in message
- Model not found after config update
- Server restart

**Fix:**
- Validate JSON before sending
- Verify model ID in config message
- Implement reconnection logic in client

---

### Issue: File injection not working

**Symptoms:** AI responds as if file content not present

**Check:**
```bash
# Verify file exists and readable
cat /path/to/file.txt

# Check file size (100KB limit)
ls -la /path/to/file.txt
```

**Causes:**
- File doesn't exist on server
- File too large (first 100KB only)
- Encoding issues

**Fix:**
- Use absolute paths
- Check server filesystem permissions
- Verify UTF-8 encoding

---

### Issue: High latency on first request

**Symptoms:** First request slow, subsequent requests fast

**Cause:** Key pool initialization, model registry loading

**Fix:**
- Pre-warm with health check: `curl /health`
- Use keep-alive connections

---

## 10. Usage Examples

### REST API (cURL)

```bash
# Basic chat
curl -X POST http://localhost:3099/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "prompt": "Hello, world!"
  }'

# With file context
curl -X POST http://localhost:3099/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama-3.3-70b-versatile",
    "prompt": "Review this code",
    "files": ["/home/flintx/project/main.py"],
    "format": "json"
  }'

# Advanced parameters
curl -X POST http://localhost:3099/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash",
    "prompt": "Write a story",
    "temperature": 0.9,
    "max_tokens": 500,
    "top_p": 0.95
  }'
```

### SSE Streaming (JavaScript)

```javascript
const eventSource = new EventSource('/v1/chat/stream', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    model: 'gemini-2.5-flash',
    prompt: 'Tell me a story'
  })
});

eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'content') {
    console.log('Token:', data.content);
  } else if (data.type === 'metadata') {
    console.log('Done:', data.usage);
    eventSource.close();
  }
};
```

### WebSocket (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:3099/v1/chat/ws/ws');

ws.onopen = () => {
  // Configure session
  ws.send(JSON.stringify({
    type: 'config',
    model: 'gemini-2.5-flash',
    temp: 0.7
  }));
  
  // Send prompt
  ws.send(JSON.stringify({
    type: 'prompt',
    content: 'What is the capital of France?'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  switch (data.type) {
    case 'content':
      console.log('Chunk:', data.content);
      break;
    case 'metadata':
      console.log('Usage:', data.usage);
      break;
    case 'error':
      console.error('Error:', data.content);
      break;
  }
};
```

---

## 11. Integration with Other Systems

### Key Manager Integration
- All endpoints use `KeyPool.get_next()` for key rotation
- Precision strike (`request.key`) bypasses rotation
- Cooldown handling on 429 errors

### HighSignal Logger Integration
- Every strike generates `PEA-XXXX` tag
- Logs saved to `vault/successful/` or `vault/failed/`
- Master logs updated for quick auditing

### Database Integration
- `ConversationDB` saves REST chat history
- WebSocket and SSE not persisted (stateless streaming)
- `KeyUsageDB` tracks per-key consumption

### Model Registry Integration
- `MODEL_REGISTRY` in `config.py` single source of truth
- Gateway auto-detection from model ID prefix
- Frozen/deprecated status respected

---

## 12. Future Enhancements

Based on the evolution and current limitations:

1. **Authentication Layer** - Bearer token validation on WebSocket
2. **Rate Limit Headers** - X-RateLimit-Remaining in responses
3. **Request ID Tracing** - Propagate correlation IDs through system
4. **GraphQL Support** - Alternative to REST for complex queries
5. **Webhook Callbacks** - Async notification on completion
6. **Batch REST API** - Multiple prompts in single request
7. **Response Caching** - Cache frequent prompts
8. **A/B Testing** - Route percentage of traffic to different models

---

**END OF DOCUMENTATION**
