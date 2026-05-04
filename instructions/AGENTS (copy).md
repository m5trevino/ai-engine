# 🦚 PEACOCK ENGINE V3 - AGENT DOCUMENTATION

> **For AI Coding Agents**: This document provides essential context for working with the PEACOCK ENGINE codebase.
> **Last Updated**: 2026-04-10

---

## 1. PROJECT OVERVIEW

**PEACOCK ENGINE V3** is a headless, multi-gateway AI orchestration engine built with Python (FastAPI) and Pydantic AI. It serves as the central nervous system for FlintX AI operations, providing unified access to multiple LLM providers through a single API.

### Core Mission
- **Unified API**: Single endpoint for Google (Gemini), Groq, DeepSeek, and Mistral
- **High Availability**: Automatic key rotation and failover between multiple API keys
- **Rate Limit Management**: Proactive throttling with configurable performance modes
- **Forensic Logging**: Complete audit trail of all AI interactions

### Version Info
- **Engine Version**: 3.0.0
- **Python**: >= 3.11
- **FastAPI**: Latest with Pydantic AI integration
- **WebUI**: React 19 + Vite + Tailwind CSS 4.x

---

## 2. TECHNOLOGY STACK

### Backend
| Component | Technology | Purpose |
|-----------|------------|---------|
| Framework | FastAPI | Async HTTP API |
| AI Layer | Pydantic AI | Type-safe LLM integration |
| Database | SQLite (peacock.db) | Conversation & usage tracking |
| HTTP Client | httpx | Async requests with proxy support |
| CLI | argparse + rich + questionary | Interactive command line |

### Frontend
| Component | Technology |
|-----------|------------|
| Framework | React 19 |
| Build Tool | Vite 6 |
| Styling | Tailwind CSS 4.1 |
| Icons | Lucide React |
| Animation | Framer Motion |

### Supported Gateways
1. **Google** (Gemini models) - Via `GOOGLE_KEYS` env var
2. **Groq** (Llama, OpenAI OSS, Qwen, etc.) - Via `GROQ_KEYS` env var
3. **DeepSeek** - Via `DEEPSEEK_KEYS` env var
4. **Mistral** - Via `MISTRAL_KEYS` env var

---

## 3. PROJECT STRUCTURE

```
ai-engine/
├── app/                          # Main Python application
│   ├── main.py                   # FastAPI entry point, router registration
│   ├── config.py                 # MODEL_REGISTRY, ModelConfig, PERFORMANCE_MODES
│   ├── core/                     # Core business logic
│   │   ├── striker.py            # AI execution engine (execute_strike, streaming)
│   │   └── key_manager.py        # KeyPool, rotation strategies, cooldown
│   ├── routes/                   # API endpoints
│   │   ├── chat.py               # Main chat endpoints (/v1/chat)
│   │   ├── models.py             # Model listing endpoints
│   │   ├── keys.py               # Key management endpoints
│   │   ├── docs.py               # API documentation endpoints
│   │   └── ...                   # Other route modules
│   ├── db/                       # Database layer
│   │   └── database.py           # SQLite schema, KeyUsageDB, ConversationDB
│   ├── utils/                    # Utilities
│   │   ├── formatter.py          # CLI output formatting (rich colors)
│   │   ├── logger.py             # HighSignalLogger (forensic logging)
│   │   └── token_counter.py      # Unified token counting
│   └── commands/                 # CLI subcommands
│       └── test_commands.py      # Validation commands
├── vite/                         # Frontend source (React/Vite)
│   ├── src/App.tsx               # Main React application
│   ├── src/lib/gemini.ts         # Gemini API client
│   └── package.json              # Frontend dependencies
├── app/static/                   # Built frontend (served by FastAPI)
│   ├── index.html                # SPA entry point
│   └── assets/                   # Bundled JS/CSS
├── vault/                        # Forensic logs storage
│   ├── successful/               # Successful strike logs
│   └── failed/                   # Failed strike logs
├── scripts/                      # Validation scripts
├── ai-engine.py                  # CLI entry point (manual strikes, audits)
├── run_engine.sh                 # Production startup script
├── requirements.txt              # Python dependencies
├── pyproject.toml               # Project metadata
└── peacock.db                    # SQLite database (runtime)
```

---

## 4. KEY CONFIGURATION FILES

### `app/config.py`
**CRITICAL**: This file contains the `MODEL_REGISTRY` - the single source of truth for all available AI models.

```python
# Key structures you will encounter:
class ModelConfig(BaseModel):
    id: str                           # Model identifier (e.g., "gemini-2.0-flash")
    gateway: Literal['groq', 'google', 'deepseek', 'mistral']
    tier: Literal['free', 'cheap', 'expensive', 'custom', 'deprecated']
    note: str                         # Human-readable description
    status: Literal['active', 'frozen', 'deprecated']
    rpm: int                          # Requests per minute limit
    tpm: int                          # Tokens per minute limit
    rpd: int                          # Requests per day limit
    input_price_1m: float             # Price per 1M input tokens
    output_price_1m: float            # Price per 1M output tokens
```

**Performance Modes** (HELLCAT PROTOCOL):
- `stealth` (Black Key): 3.0x multiplier - safest, slowest
- `balanced` (Blue Key): 1.15x multiplier - default
- `apex` (Red Key): 1.02x multiplier - maximum throughput

### Environment Variables (`.env`)
The engine expects these environment variables:

```bash
# API Keys (comma-separated, supports LABEL:KEY format)
GROQ_KEYS="ACCOUNT1:gsk_xxx,ACCOUNT2:gsk_yyy"
GOOGLE_KEYS="ACCOUNT1:AIxxx,ACCOUNT2:AIyyy"
DEEPSEEK_KEYS="sk-xxx,sk-yyy"
MISTRAL_KEYS="sk-xxx,sk-yyy"

# Proxy Configuration (optional)
PROXY_ENABLED="true"
PROXY_URL="socks5://127.0.0.1:1081"

# Feature Flags
PEACOCK_PERF_MODE="balanced"      # stealth | balanced | apex
PEACOCK_TUNNEL="false"            # Enable SOCKS5 tunnel
PEACOCK_VERBOSE="false"           # Debug output
PEACOCK_QUIET="false"             # Minimal output

# Logging
LOG_SUCCESS="true"
LOG_FAILED="true"
```

---

## 5. BUILD & RUN COMMANDS

### Development Setup
```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run development server
python -m uvicorn app.main:app --host 0.0.0.0 --port 3099 --reload
```

### Production Startup
```bash
# Use the provided startup script
./run_engine.sh

# Or with options:
./run_engine.sh --no-proxy                    # Disable proxy
./run_engine.sh --proxy=socks5://host:port    # Custom proxy
```

### Frontend Development
```bash
cd vite/
npm install
npm run dev        # Dev server on :3000
npm run build      # Build to app/static/
```

### CLI Commands
```bash
# List all models
./ai-engine.py models

# Execute a manual strike
./ai-engine.py strike "Your prompt here" --model gemini-2.0-flash

# Audit model health
./ai-engine.py audit

# Show system status (diagnostics)
./ai-engine.py mission-control

# Interactive onboarding
./ai-engine.py onboard
```

---

## 6. API ENDPOINTS

### Primary Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat` | POST | Main chat endpoint - works with any model |
| `/v1/chat/stream` | POST | Streaming response (SSE) |
| `/v1/chat/ws/ws` | WebSocket | Real-time bidirectional chat |
| `/v1/chat/models` | GET | List all models grouped by gateway |
| `/v1/models` | GET | Raw model registry |
| `/v1/keys` | GET | List available keys (names only) |
| `/v1/keys/usage` | GET | Detailed key usage statistics |
| `/health` | GET | Health check with pool status |

### Chat Request Format
```json
{
  "model": "gemini-2.0-flash-lite",
  "prompt": "Your prompt here",
  "format": "text",
  "temp": 0.7,
  "files": ["/path/to/context/file.py"],
  "timeout": 60,
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 4096
}
```

### Chat Response Format
```json
{
  "content": "Response text",
  "model": "gemini-2.0-flash-lite",
  "gateway": "google",
  "key_used": "PEACOCK_MAIN",
  "format": "text",
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 50,
    "total_tokens": 60
  },
  "duration_ms": 1240
}
```

---

## 7. CODE STYLE & CONVENTIONS

### Python
- **Type hints**: Use `typing` module extensively (List, Dict, Optional, etc.)
- **Pydantic models**: For all request/response schemas
- **Async/await**: All I/O operations are async
- **Error handling**: Try/except with specific error types, log with HighSignalLogger

### Naming Conventions
- **Files**: lowercase with underscores (`key_manager.py`)
- **Classes**: PascalCase (`KeyPool`, `ModelConfig`)
- **Functions**: snake_case (`execute_strike`, `get_next`)
- **Constants**: UPPER_SNAKE_CASE (`MODEL_REGISTRY`, `FROZEN_FILE`)
- **Private**: Leading underscore (`_build_dynamic_schema`)

### Gateway Colors (for CLI output)
```python
# Used in formatter.py for consistent visual identity
groq    -> Cyan/Bright Cyan
google  -> Blue/Bright Blue
deepseek -> Green/Bright Green
mistral -> Magenta/Bright Magenta
```

### Log Tags
All strikes get a unique 8-character tag: `PEA-XXXX` (e.g., `PEA-A3F2`)

---

## 8. TESTING & VALIDATION

### Model Testing
```bash
# Test specific gateway
./ai-engine.py test google
./ai-engine.py test groq

# Test all gateways
./ai-engine.py test all

# Test with options
./ai-engine.py test google --key PEACOCK_MAIN --model gemini-2.0-flash
```

### Token Counting
```bash
# Count tokens for text
./ai-engine.py tokens count --text "Hello world" --model gemini-2.0-flash

# Count tokens in file
./ai-engine.py tokens count --file /path/to/file.txt --model llama-3.3-70b
```

### Validation Scripts
Located in `scripts/` directory:
- `validate_google.py` - Google API key validation
- `validate_groq.py` - Groq API key validation

---

## 9. SECURITY CONSIDERATIONS

### API Key Management
- Keys are NEVER logged in full (only first 8 chars shown)
- Keys rotate automatically via `KeyPool` with shuffle strategy
- Rate-limited keys enter "cooldown" automatically
- Failed keys can be auto-frozen via audit commands

### Proxy/Tunnel Support
- Supports SOCKS5 proxies for all outbound connections
- `PEACOCK_TUNNEL` mode routes all traffic through `socks5://127.0.0.1:1081`
- Proxy can be disabled per-request with `--no-proxy` flag

### File Access
- File injection reads only first 100KB to prevent memory spikes
- Path validation prevents directory traversal attacks
- File context is clearly delimited in prompts

### Database
- SQLite database is local-only
- No sensitive data stored (only key account names, not keys themselves)
- Conversation history is stored for UI features

---

## 10. COMMON DEVELOPMENT TASKS

### Adding a New Model
1. Edit `app/config.py`
2. Add `ModelConfig()` to `MODEL_REGISTRY` list
3. Include: id, gateway, tier, note, rpm, tpm, rpd
4. Run `./ai-engine.py models` to verify

### Adding a New Gateway
1. Create pool in `app/core/key_manager.py`
2. Add gateway logic in `app/core/striker.py` (in `execute_strike`)
3. Add formatter styles in `app/utils/formatter.py`
4. Update `app/config.py` ModelConfig gateway Literal

### Debugging
```python
# Enable verbose logging
import os
os.environ["PEACOCK_VERBOSE"] = "true"

# Check key pool status
./ai-engine.py keys

# View mission control (full diagnostics)
./ai-engine.py mission-control
```

### Forensic Log Analysis
Success logs: `vault/successful/PEA-XXXX.txt`
Failure logs: `vault/failed/PEA-XXXX.txt`
Master logs: `success_strikes.log`, `failed_strikes.log`

---

## 11. DEPLOYMENT

### Docker
```dockerfile
# See Dockerfile in project root
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 10000
CMD ["python", "-m", "app.main"]
```

### Render.com
See `render.yaml` for configuration.

### Environment Requirements
- Python 3.11+
- At least one API key configured
- SQLite write permissions (for `peacock.db`)
- Optional: Node.js 20+ (for frontend builds)

---

## 12. ARCHITECTURE PATTERNS

### Key Pool Rotation
```
KeyPool (abstract)
  ├── ShuffleStrategy (default)
  └── RoundRobinStrategy

GroqPool, GooglePool, DeepSeekPool, MistralPool
  - deck: List[KeyAsset]
  - pointer: int
  - get_next(): Returns next available key
  - mark_cooldown(): Temporarily disable key
```

### Strike Execution Flow
```
1. ThrottleController.wait_if_needed()  # Rate limit check
2. KeyPool.get_next()                   # Get API key
3. Pydantic AI Agent.run()              # Execute LLM call
4. HighSignalLogger.log_strike()        # Log result
5. KeyUsageDB.record_usage()            # Track usage
```

### Response Types
- `text` (default): Plain text response
- `json`: Parsed JSON response
- `pydantic`: Dynamic Pydantic model validation
- `eagle_scaffold`: Structured file scaffold output

---

## 13. TROUBLESHOOTING

### Common Issues

| Issue | Solution |
|-------|----------|
| `NO AMMUNITION FOR groq` | Check GROQ_KEYS env var is set |
| Model returns 429 | Keys on cooldown, wait 60s or add more keys |
| Web UI not loading | Ensure `vite/build` exists or run `npm run build` |
| Database locked | Stop all engine instances, delete `peacock.db` if needed |
| Timeout errors | Increase timeout with `--timeout 120` or `timeout` param |

### Log Locations
- Application logs: stdout/stderr
- Strike logs: `vault/{successful,failed}/PEA-XXXX.txt`
- Summary logs: `success_strikes.log`, `failed_strikes.log`

---

## 14. FILES TO NEVER MODIFY MANUALLY

- `frozen_models.json` - Managed by freeze/unfreeze commands
- `peacock.db` - Managed by application
- `vault/*` - Managed by HighSignalLogger
- `app/static/assets/*` - Generated by Vite build

---

**End of Documentation**

For questions or updates to this file, ensure you're following the patterns established in the codebase. When in doubt, run `./ai-engine.py mission-control` for current system state.
