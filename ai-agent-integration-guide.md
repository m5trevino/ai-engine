# PEACOCK ENGINE - AI Agent Integration Guide

> **Version**: 3.0.0  
> **Last Updated**: 2026-04-05  
> **Purpose**: Comprehensive guide for AI coding agents integrating with PEACOCK ENGINE

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Quick Start for AI Agents](#2-quick-start-for-ai-agents)
3. [Technology Stack](#3-technology-stack)
4. [Project Structure](#4-project-structure)
5. [Build and Run Commands](#5-build-and-run-commands)
6. [Code Organization](#6-code-organization)
7. [API Architecture](#7-api-architecture)
8. [Key Concepts](#8-key-concepts)
9. [Development Conventions](#9-development-conventions)
10. [Environment Configuration](#10-environment-configuration)
11. [Testing Strategy](#11-testing-strategy)
12. [Deployment](#12-deployment)
13. [Troubleshooting](#13-troubleshooting)

---

## 1. Project Overview

**PEACOCK ENGINE** is a production-grade, headless AI orchestration layer that provides:

- **Unified API**: Single interface for multiple AI providers (Groq, Google Gemini, DeepSeek, Mistral)
- **Key Rotation**: Automatic round-robin with shuffle across multiple API keys per provider
- **Rate Limit Tracking**: Built-in RPM/TPM/RPD tracking per model with real-time meters
- **Forensic Logging**: Dual-track logging with unique PEA-XXXX tags and verbatim vault storage
- **Usage Persistence**: SQLite database tracks key usage over time
- **Fancy CLI Output**: Gateway-specific decorative borders for logs

### Mission

To serve as the central nervous system for all FlintX AI operations, providing forensic logging, financial redlines, and universal integration for any application.

---

## 2. Quick Start for AI Agents

If you're an AI agent reading this, here's what you need to know immediately:

### 2.1 Essential Commands

```bash
# Start the engine (must be run from project root)
./run_engine.sh

# Check if engine is running
curl http://localhost:3099/health

# List available models
python ai-engine.py models

# Execute a test strike
python ai-engine.py strike "Hello, world!" --model gemini-2.5-flash-lite
```

### 2.2 Key Files to Understand

| File | Why It Matters |
|------|----------------|
| `app/config.py` | Model registry - all available AI models defined here |
| `app/core/striker.py` | Core execution logic - how strikes are processed |
| `app/core/key_manager.py` | API key rotation and pool management |
| `app/routes/chat.py` | Main API endpoint for all chat requests |
| `requirements.txt` | Python dependencies |

### 2.3 Adding a New Model

If you need to add a new AI model:

1. Open `app/config.py`
2. Add a new `ModelConfig` entry to `MODEL_REGISTRY`
3. Ensure you have API keys configured in `.env`
4. Test with: `python ai-engine.py audit --id <model-id>`

---

## 3. Technology Stack

| Category | Technology | Version |
|----------|------------|---------|
| **Runtime** | Python | 3.11+ |
| **Web Framework** | FastAPI | Latest |
| **Server** | Uvicorn | Latest |
| **AI Framework** | Pydantic AI | Latest |
| **HTTP Client** | httpx | Latest |
| **Database** | SQLite | Built-in |
| **CLI Output** | rich, questionary | Latest |
| **Environment** | python-dotenv | Latest |

### Supported AI Gateways

| Gateway | Provider | Key Env Var | Models |
|---------|----------|-------------|--------|
| `groq` | Groq | `GROQ_KEYS` | Llama, Qwen, Moonshot/Kimi, GPT-OSS |
| `google` | Google Gemini | `GOOGLE_KEYS` | Gemini 2.0/2.5/3.x series, Embeddings |
| `deepseek` | DeepSeek | `DEEPSEEK_KEYS` | DeepSeek V3, R1 |
| `mistral` | Mistral AI | `MISTRAL_KEYS` | Mistral Large |

---

## 4. Project Structure

```
/home/flintx/ai-handler/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI entry point
│   ├── config.py                 # Model registry & performance modes
│   ├── AGENT_ONBOARDING.md       # Agent onboarding guide
│   ├── TACTICAL_COMMAND.md       # Tactical command reference
│   ├── commands/                 # CLI subcommand implementations
│   │   ├── __init__.py
│   │   └── test_commands.py
│   ├── core/                     # Core business logic
│   │   ├── __init__.py
│   │   ├── key_manager.py        # API key rotation & management
│   │   └── striker.py            # AI execution engine
│   ├── client/                   # Client SDK
│   │   ├── __init__.py
│   │   └── sdk.py
│   ├── db/                       # Database layer
│   │   ├── __init__.py
│   │   └── database.py           # SQLite operations
│   ├── models/                   # Pydantic models
│   │   └── app_profile.py
│   ├── routes/                   # FastAPI route handlers
│   │   ├── chat.py               # Main chat endpoint (/v1/chat)
│   │   ├── chat_api.py           # WebUI chat API
│   │   ├── strike.py             # Legacy strike endpoint
│   │   ├── payload_strike.py     # Multi-file strikes
│   │   ├── striker.py            # Batch processing endpoints
│   │   ├── models.py             # Model registry endpoint
│   │   ├── models_api.py         # WebUI models API
│   │   ├── keys.py               # Key management endpoints
│   │   ├── keys_api.py           # WebUI keys API
│   │   ├── tokens.py             # Token counting endpoints
│   │   ├── fs.py                 # Filesystem bridge
│   │   ├── docs.py               # Documentation endpoints
│   │   ├── profile.py            # Profile/syndicate strikes
│   │   ├── proxy_control.py      # Proxy configuration
│   │   ├── chat_ui.py            # Chat UI API
│   │   ├── dashboard.py          # Dashboard endpoints
│   │   └── onboarding.py         # App onboarding
│   ├── static/                   # Static files for Chat UI
│   │   └── chat.html
│   └── utils/                    # Utility modules
│       ├── __init__.py
│       ├── formatter.py          # CLI formatting & colors
│       ├── logger.py             # High-signal logging
│       ├── gemini_token_counter.py   # Gemini token estimation
│       └── groq_token_counter.py     # Groq token estimation
├── deploy/                       # Production deployment files
│   ├── setup-server.sh           # Server preparation script
│   ├── install-app.sh            # Application installation
│   ├── quick-deploy.sh           # One-command deployment
│   ├── peacock-engine.service    # Systemd service definition
│   ├── Caddyfile                 # Reverse proxy config
│   ├── Dockerfile                # Container image
│   ├── docker-compose.yml        # Docker stack
│   └── DEPLOYMENT_GUIDE.md       # Full deployment docs
├── vault/                        # Forensic logging vault
│   ├── successful/               # Successful strike logs (PEA-XXXX.txt)
│   └── failed/                   # Failed strike logs
├── webui/                        # Web UI design files
│   ├── DESIGN.md
│   ├── MasterLayout.html
│   └── components/
├── requirements.txt              # Python dependencies
├── ai-engine.py                  # CLI entry point
├── ai-engine                     # CLI wrapper script
├── run_engine.sh                 # Production server launcher
├── launch.sh                     # Development server launcher
├── peacock.db                    # SQLite database
├── success_strikes.log           # Master success log
├── failed_strikes.log            # Master failure log
├── manual_strikes.log            # Manual strike log
├── frozen_models.json            # Frozen model registry
├── render.yaml                   # Render.com deployment config
├── Dockerfile                    # Docker build config
├── deploy.sh                     # VPS deployment script
└── MISSION_MANIFEST.md           # Project manifest
```

---

## 5. Build and Run Commands

### 5.1 Setup (First Time)

```bash
# Create virtual environment
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 5.2 Run the Server

```bash
# Production launch (recommended)
./run_engine.sh

# Development launch with options
./launch.sh --tunnel        # Enable SOCKS5 tunnel
./launch.sh --port=8080     # Custom port
./launch.sh --quiet         # Quiet mode (background)
./launch.sh --no-proxy      # Disable all proxies

# Direct Python execution
python -m app.main

# Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 3099
```

### 5.3 CLI Commands

```bash
# Make CLI executable and use it
chmod +x ai-engine
./ai-engine models                    # List available models
./ai-engine keys                      # List loaded API keys
./ai-engine strike "Your prompt"      # Execute a strike
./ai-engine strike --file prompt.txt  # Strike from file
./ai-engine audit                     # Audit model health
./ai-engine audit --gateway groq      # Audit specific gateway
./ai-engine onboard                   # Interactive onboarding
./ai-engine flyout-snippet            # Generate UI flyout snippet
./ai-engine mission-control           # Full system diagnostics
./ai-engine dossier                   # Show system dossier
./ai-engine agent-guide               # Interactive agent guide
./ai-engine ui                        # Boot engine and open Web UI
./ai-engine freeze <model-id>         # Decommission a model
./ai-engine unfreeze <model-id>       # Re-activate a model
```

---

## 6. Code Organization

### 6.1 Core Modules

| Module | Purpose | Key Classes/Functions |
|--------|---------|----------------------|
| `app/core/key_manager.py` | API key rotation & management | `KeyPool`, `KeyAsset`, `RotationStrategy`, `ShuffleStrategy`, `RoundRobinStrategy` |
| `app/core/striker.py` | AI execution engine | `execute_strike()`, `execute_streaming_strike()`, `execute_precision_strike()`, `ThrottleController`, `RateLimitMeter` |
| `app/config.py` | Model registry & config | `MODEL_REGISTRY`, `ModelConfig`, `PERFORMANCE_MODES`, `FROZEN_IDS` |
| `app/db/database.py` | Database operations | `KeyUsageDB`, `ConversationDB`, `init_db()` |
| `app/utils/formatter.py` | CLI output formatting | `CLIFormatter`, `Colors` |
| `app/utils/logger.py` | Forensic logging | `HighSignalLogger` |
| `app/utils/gemini_token_counter.py` | Gemini token counting | `GeminiTokenCounter` |
| `app/utils/groq_token_counter.py` | Groq token counting | `GroqTokenCounter` |

### 6.2 Route Modules

| Route | Endpoint Prefix | Purpose |
|-------|-----------------|---------|
| `chat.py` | `/v1/chat` | Main unified chat endpoint |
| `chat_api.py` | `/v1/webui/chat` | WebUI chat API |
| `models_api.py` | `/v1/webui/models` | WebUI models API |
| `keys_api.py` | `/v1/webui/keys` | WebUI keys API |
| `tokens.py` | `/v1/tokens` | Token counting endpoints |
| `strike.py` | `/v1/strike` | Legacy strike endpoint |
| `payload_strike.py` | `/v1/payload-strike` | Multi-file context strikes |
| `striker.py` | `/v1/striker/*` | Batch processing |
| `models.py` | `/v1/models` | Model registry |
| `keys.py` | `/v1/keys/*` | Key usage stats |
| `docs.py` | `/v1/docs/*` | API documentation |
| `proxy_control.py` | `/v1/proxy/*` | Proxy configuration |

---

## 7. API Architecture

### 7.1 Primary Endpoint: `/v1/chat` (RECOMMENDED)

**Method**: POST  
**Purpose**: Generic, unified endpoint for any model

```bash
curl -X POST http://localhost:3099/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash-lite",
    "prompt": "Hello, what can you do?",
    "format": "text"
  }'
```

**Request Fields**:
- `model` (required): Model ID from registry
- `prompt` (required): The prompt text
- `files` (optional): Array of file paths to include as context
- `format` (optional): 'text' | 'json' | 'pydantic', default: 'text'
- `schema` (optional): Schema definition for 'pydantic' format
- `temp` (optional): Temperature 0.0-2.0, default: 0.7
- `key` (optional): Specific key account to use (bypasses rotation)
- `timeout` (optional): Timeout in seconds
- `title` (optional): Conversation title for database

**Response**:
```json
{
  "content": "Response content",
  "model": "gemini-2.5-flash-lite",
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

### 7.2 Streaming Endpoint: `/v1/chat/stream`

**Method**: POST  
**Purpose**: Server-Sent Events (SSE) streaming responses

```bash
curl -X POST http://localhost:3099/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.5-flash-lite",
    "prompt": "Write a long story..."
  }'
```

### 7.3 Health Check

```bash
curl http://localhost:3099/health
```

Response:
```json
{
  "status": "ONLINE",
  "system": "PEACOCK_ENGINE_V3",
  "version": "3.0.0",
  "integrity": {
    "groq": 15,
    "google": 3,
    "deepseek": 1,
    "mistral": 1
  },
  "features": {
    "chat_ui": false,
    "key_tracking": true,
    "generic_endpoint": true
  }
}
```

### 7.4 List Models

```bash
curl http://localhost:3099/v1/chat/models
```

### 7.5 Key Usage Stats

```bash
curl http://localhost:3099/v1/keys/usage
```

### 7.6 Endpoint Discovery

```bash
curl http://localhost:3099/v1/docs/endpoints
```

---

## 8. Key Concepts

### 8.1 Key Pool System

- **KeyAsset**: A single API key with label/account tracking
- **KeyPool**: A collection of API keys for a gateway with rotation strategy
- **Rotation Strategies**: 
  - `ShuffleStrategy`: Random order (default)
  - `RoundRobinStrategy`: Sequential rotation

### 8.2 The Strike Lifecycle

1. **The Call**: Client sends a prompt to the Engine
2. **The Strategy**: `KeyPool` picks the optimal API key based on rotation strategy
3. **The Throttle**: `ThrottleController` applies rate limiting based on performance mode
4. **The Tunnel**: If enabled, traffic routes through SOCKS5 proxy (127.0.0.1:1081)
5. **The Strike**: `Pydantic AI` executes the prompt against the target model
6. **The Analysis**: Tokens counted, cost calculated, RPM/TPM meters updated
7. **The Vault**: `HighSignalLogger` generates PEA-XXXX tag, saves to vault
8. **The Return**: Response + Tag ID + Usage metrics returned to client

### 8.3 Performance Modes (Hellcat Protocol)

| Mode | Name | Multiplier | Use Case |
|------|------|------------|----------|
| `stealth` | BLACK KEY | 3.0x | Conservative rate limiting |
| `balanced` | BLUE KEY | 1.15x | Default balanced approach |
| `apex` | RED KEY | 1.02x | Aggressive, near-limit |

Set via environment variable: `PEACOCK_PERF_MODE=stealth`

### 8.4 Forensic Logging

Every strike generates:
- **Tag ID**: 8-character unique identifier (PEA-XXXX)
- **Master Log**: Appended to `success_strikes.log` or `failed_strikes.log`
- **Vault File**: Verbatim I/O stored in `vault/successful/` or `vault/failed/`
- **Manual Log**: Manual strikes also logged to `manual_strikes.log`

### 8.5 Model Tiers

| Tier | Description | Example Models |
|------|-------------|----------------|
| `free` | High volume, low cost | gemini-2.5-flash-lite, llama-3.1-8b-instant |
| `cheap` | Balanced cost/performance | gemini-2.5-flash, whisper-large-v3 |
| `expensive` | High quality, higher cost | gemini-3.1-pro, llama-3.3-70b-versatile |
| `custom` | Specialized models | canopylabs/orpheus-v1-english |
| `deprecated` | No longer recommended | Legacy models |

### 8.6 Model Status

| Status | Meaning | Action |
|--------|---------|--------|
| `active` | Available for use | None |
| `frozen` | Temporarily disabled | Use `./ai-engine unfreeze <id>` to re-enable |
| `deprecated` | Will be removed soon | Migrate to newer model |

---

## 9. Development Conventions

### 9.1 Code Style

- **Imports**: Group by standard library, third-party, local (separated by blank line)
- **Type Hints**: Use full type annotations for function signatures
- **Docstrings**: Google-style docstrings for all public functions
- **Line Length**: 100 characters max
- **Quotes**: Double quotes for strings, single quotes for dict keys where appropriate

### 9.2 Error Handling

```python
try:
    result = await execute_strike(...)
except Exception as e:
    # Log the error with tag
    tag = HighSignalLogger.log_strike(..., is_success=False, error=str(e))
    # Re-raise or handle gracefully
    raise HTTPException(status_code=500, detail=str(e))
```

### 9.3 Adding New Endpoints

1. Create route file in `app/routes/my_feature.py`:
```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class MyRequest(BaseModel):
    input: str

@router.post("")
async def my_endpoint(request: MyRequest):
    return {"result": f"Processed: {request.input}"}
```

2. Register in `app/main.py`:
```python
from app.routes.my_feature import router as my_feature_router
app.include_router(my_feature_router, prefix="/v1/my-feature", tags=["MY_FEATURE"])
```

3. Add to `app/routes/docs.py` ENDPOINTS list for documentation

### 9.4 Model Registration

Add new models to `app/config.py` MODEL_REGISTRY:

```python
ModelConfig(
    id="model-id",
    gateway="google",  # or groq, deepseek, mistral
    tier="cheap",      # free, cheap, expensive, custom, deprecated
    note="Description",
    rpm=100,           # Requests per minute
    tpm=100000,        # Tokens per minute
    rpd=1000,          # Requests per day
    input_price_1m=0.10,
    output_price_1m=0.30,
    context_window=1000000
)
```

---

## 10. Environment Configuration

Required environment variables (typically in `.env`):

| Variable | Description | Format |
|----------|-------------|--------|
| `GROQ_KEYS` | Comma-separated Groq API keys | `label1:key1,label2:key2` |
| `GOOGLE_KEYS` | Comma-separated Gemini API keys | `label1:key1,label2:key2` |
| `DEEPSEEK_KEYS` | DeepSeek API key | `key` or `label:key` |
| `MISTRAL_KEYS` | Mistral API key | `key` or `label:key` |
| `PROXY_ENABLED` | Enable proxy routing | `true` or `false` |
| `PROXY_URL` | Proxy URL | `http://proxy:port` |
| `PORT` | Server port | `3099` (default) |
| `CHAT_UI_ENABLED` | Enable web chat UI | `true` or `false` |
| `PEACOCK_DEBUG` | Debug logging | `true` or `false` |
| `PEACOCK_VERBOSE` | Verbose output | `true` or `false` |
| `PEACOCK_PERF_MODE` | Performance mode | `stealth`, `balanced`, `apex` |
| `PEACOCK_TUNNEL` | Enable tunnel mode (SOCKS5 127.0.0.1:1081) | `true` or `false` |
| `API_KEY` | Optional API key for client auth | `your-secret-key` |

---

## 11. Testing Strategy

### 11.1 Manual Testing

```bash
# Test health endpoint
curl http://localhost:3099/health

# Test model list
curl http://localhost:3099/v1/chat/models

# Test simple strike
curl -X POST http://localhost:3099/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-2.5-flash-lite", "prompt": "Hello"}'

# Test with file context
curl -X POST http://localhost:3099/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-2.5-flash-lite", "prompt": "Review this code", "files": ["/path/to/file.py"]}'

# Test streaming
curl -X POST http://localhost:3099/v1/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-2.5-flash-lite", "prompt": "Count to 10 slowly"}'
```

### 11.2 Model Audit

```bash
# Audit all active models
python ai-engine.py audit

# Audit specific gateway
python ai-engine.py audit --gateway google

# Audit specific model
python ai-engine.py audit --id gemini-2.5-flash-lite
```

### 11.3 Test Scripts

The project includes several test scripts:

```bash
# Test specific providers
python test_e2e_fix.py
python test_proxy.py
python verify_gemini_fix.py
python verify_precision_strike.py

# Test key validity
python check_groq_keys.py
python check_env_groq_keys.py
python syndicate_key_tester.py
```

---

## 12. Deployment

### 12.1 Local Deployment

```bash
# Using the run script
./run_engine.sh

# Using launch script with options
./launch.sh --port=8080 --no-proxy
```

### 12.2 VPS Deployment

```bash
# Run the deployment script as root
sudo bash deploy.sh

# Then configure environment
sudo nano /etc/peacock/env

# Start the service
sudo systemctl start peacock-engine
sudo systemctl enable peacock-engine

# Check status
sudo systemctl status peacock-engine
sudo journalctl -u peacock-engine -f
```

### 12.3 Render Deployment

The project includes `render.yaml` for Render.com:

```yaml
services:
  - type: web
    name: peacock-engine
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: python -m app.main
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      - key: PORT
        value: 10000
```

### 12.4 Docker Deployment

```bash
# Build Docker image
docker build -t peacock-engine .

# Run container
docker run -p 3099:3099 --env-file .env peacock-engine

# Or use docker-compose
docker-compose up -d
```

---

## 13. Troubleshooting

### 13.1 429 Rate Limit Errors

**Cause**: Provider rate limit hit  
**Solution**: PEACOCK automatically rotates keys. The `ThrottleController` proactively manages rate limits based on performance mode.

### 13.2 Key Exhaustion

**Check**: `GET /v1/keys/usage`  
**Solution**: Add more keys to the pool in `.env` file

### 13.3 Model Not Found

**Error**: `400 Unknown model '...'`  
**Solution**: Check available models with `GET /v1/chat/models`

### 13.4 Database Issues

**Check**: Verify `peacock.db` exists and is writable  
**Solution**: Delete `peacock.db` to reinitialize (loses usage history only)

### 13.5 Port Already in Use

The launch scripts automatically kill processes on port 3099. For manual cleanup:
```bash
kill -9 $(lsof -ti:3099)
```

### 13.6 Gemini Token Counting Issues

**Note**: Some Gemini responses may show 0 tokens. This is a known limitation of the Google API. The engine attempts to extract tokens from response metadata when available.

### 13.7 Tunnel Mode Not Working

**Check**: Ensure SOCKS5 proxy is running on 127.0.0.1:1081  
**Verify**: `curl --socks5 127.0.0.1:1081 http://httpbin.org/ip`

### 13.8 Virtual Environment Issues

```bash
# Recreate virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Start server | `./run_engine.sh` |
| List models | `./ai-engine models` |
| Execute strike | `./ai-engine strike "prompt" --model gemini-2.5-flash-lite` |
| Audit models | `./ai-engine audit` |
| Health check | `curl http://localhost:3099/health` |
| API docs | `curl http://localhost:3099/v1/docs/endpoints` |
| Deploy to VPS | `sudo bash deploy.sh` |
| Backup data | Copy `peacock.db` and `vault/` directory |
| View logs | `tail -f success_strikes.log` |
| Freeze model | `./ai-engine freeze <model-id>` |
| Unfreeze model | `./ai-engine unfreeze <model-id>` |

---

## Resources

- **Model Registry**: `app/config.py`
- **Tactical Commands**: `app/TACTICAL_COMMAND.md`
- **Agent Onboarding**: `app/AGENT_ONBOARDING.md`
- **Deployment Guide**: `deploy/DEPLOYMENT_GUIDE.md`

---

**END OF DOCUMENT**

For questions or issues, check `/v1/docs/endpoints` for the most up-to-date endpoint list.
