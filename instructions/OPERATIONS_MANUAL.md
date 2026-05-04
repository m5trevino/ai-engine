# 🦚 PEACOCK ENGINE V3: THE COMPLETE OPERATIONS MANUAL

> **Version**: 3.0.0  
> **Last Updated**: 2026-04-11  
> **Classification**: OPERATIONAL - LEVEL 4 CLEARANCE  
> **Author**: FlintX AI Systems Architecture Division

---

## 📋 TABLE OF CONTENTS

1. [Executive Summary](#executive-summary)
2. [System Architecture Visual](#system-architecture)
3. [Deployment Workflows](#deployment-workflows)
4. [Implementation Checklists](#implementation-checklists)
5. [Vite + FastAPI Wiring](#vite--fastapi-wiring)
6. [VPS Infrastructure Setup](#vps-infrastructure)
7. [Syncthing Configuration](#syncthing-configuration)
8. [Token Counter System](#token-counter-system)
9. [UI Chat Wiring](#ui-chat-wiring)
10. [Payload Striker Architecture](#payload-striker-architecture)
11. [Troubleshooting Matrix](#troubleshooting-matrix)

---

## 🎯 EXECUTIVE SUMMARY

The PEACOCK ENGINE V3 is a **multi-gateway AI orchestration platform** providing unified access to Google (Gemini), Groq, DeepSeek, and Mistral APIs through a single, hardened interface.

### Core Capabilities

| Feature | Status | Gateway Support |
|---------|--------|-----------------|
| Real-time Chat | ✅ Operational | All |
| Streaming (SSE/WebSocket) | ✅ Operational | All |
| Payload Striker (Batch) | ✅ Operational | All |
| Token Counting | ✅ Operational | Google, Groq |
| Key Rotation | ✅ Operational | All |
| Rate Limit Protection | ✅ Operational | All |
| File Context Injection | ✅ Operational | All |

### Infrastructure Stack

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  React UI    │  │  CLI Tool    │  │  Syncthing (Files)   │   │
│  │  (Vite)      │  │  (ai-engine) │  │  (Bidirectional)     │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTPS/WSS
┌─────────────────────────────────────────────────────────────────┐
│                      GATEWAY LAYER (Caddy)                       │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  • chat.save-aichats.com  → localhost:3099             │     │
│  │  • engine.save-aichats.com → localhost:3099            │     │
│  │  • Auto HTTPS / gzip / security headers                │     │
│  └─────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    APPLICATION LAYER                             │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │           FastAPI (Port 3099) - Systemd Managed         │     │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────────────┐  │     │
│  │  │ /v1/chat   │ │ /v1/models │ │ /v1/payload-strike │  │     │
│  │  │ /v1/keys   │ │ /v1/fs     │ │ /v1/telemetry      │  │     │
│  │  └────────────┘ └────────────┘ └────────────────────┘  │     │
│  │                                                         │     │
│  │  ┌─────────────────────────────────────────────────┐   │     │
│  │  │  Static Files (Vite Build → app/static)         │   │     │
│  │  │  └── React SPA served at root /                 │   │     │
│  │  └─────────────────────────────────────────────────┘   │     │
│  └─────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CORE ENGINE LAYER                           │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │ Key Manager │  │   Striker    │  │ Token Counter          │  │
│  │ (Rotation)  │  │ (Execution)  │  │ (Gemini/Groq/Unified)  │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │   Logger    │  │  Throttle    │  │ Conversation DB        │  │
│  │ (Forensic)  │  │  Controller  │  │ (SQLite)               │  │
│  └─────────────┘  └──────────────┘  └────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PROVIDER LAYER                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ ┌──────────┐  │
│  │    Google    │  │     Groq     │  │ DeepSeek │ │  Mistral │  │
│  │   (Gemini)   │  │  (Llama/     │  │   (R1)   │ │  (Large) │  │
│  │              │  │   GPT-OSS)   │  │          │ │          │  │
│  └──────────────┘  └──────────────┘  └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🏗️ SYSTEM ARCHITECTURE

### Data Flow Diagram

```
┌──────────┐      ┌──────────────┐      ┌──────────────────┐      ┌──────────┐
│  Client  │─────▶│   Caddy RP   │─────▶│  FastAPI Engine  │─────▶│ Provider │
│ Request  │      │  (443→3099)  │      │   (Port 3099)    │      │  API     │
└──────────┘      └──────────────┘      └──────────────────┘      └──────────┘
                                              │
                                              │
                          ┌───────────────────┼───────────────────┐
                          │                   │                   │
                          ▼                   ▼                   ▼
                   ┌────────────┐     ┌─────────────┐    ┌──────────────┐
                   │ Key Pool   │     │ Token Count │    │ Rate Limit   │
                   │ (Rotation) │     │ (Pre-flight)│    │ (Throttle)   │
                   └────────────┘     └─────────────┘    └──────────────┘
```

### Component Interaction Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         REQUEST LIFECYCLE                                   │
└─────────────────────────────────────────────────────────────────────────────┘

[1] USER REQUEST
    │
    ▼
┌─────────────────────────────────────────────────────────────────┐
│  https://chat.save-aichats.com/v1/chat                          │
│  ├── DNS → 204.168.184.49                                       │
│  └── Caddy (443) → localhost:3099                               │
└─────────────────────────────────────────────────────────────────┘
    │
    ▼
[2] FASTAPI ROUTING
    │
    ├── API Route? (/v1/*) ──▶ Router Handler
    │                            ├── /v1/chat → chat.py
    │                            ├── /v1/models → models.py
    │                            └── /v1/fs → fs.py
    │
    └── Static Route? (/) ───▶ app/static/index.html
         └── React SPA takes over client-side routing
    │
    ▼
[3] STRIKER EXECUTION (for chat/payload)
    │
    ┌──────────────────────────────────────────────────────────┐
    │  a. ThrottleController.wait_if_needed()                  │
    │     └── Check RPM/TPM/RPD limits against MODEL_REGISTRY  │
    │                                                          │
    │  b. KeyPool.get_next()                                   │
    │     └── Rotate through GROQ_KEYS/GOOGLE_KEYS             │
    │                                                          │
    │  c. TokenCounter.count_prompt_tokens()                   │
    │     └── Gemini: google-genai API                         │
    │         Groq: tiktoken                                   │
    │                                                          │
    │  d. Pydantic AI Agent.run() / Agent.run_stream()         │
    │     └── Execute LLM call with timeout protection         │
    │                                                          │
    │  e. HighSignalLogger.log_strike()                        │
    │     └── vault/successful/PEA-XXXX.txt                    │
    │                                                          │
    │  f. KeyUsageDB.record_usage()                            │
    │     └── peacock.db (SQLite)                              │
    └──────────────────────────────────────────────────────────┘
    │
    ▼
[4] RESPONSE STREAMING
    │
    ├── HTTP Response (JSON) ──▶ REST API clients
    ├── SSE Stream ────────────▶ EventSource clients
    └── WebSocket ─────────────▶ Real-time bidirectional

```

---

## 🚀 DEPLOYMENT WORKFLOWS

### Workflow 1: Fresh VPS Installation (First-Time Setup)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW 1: FRESH VPS INSTALLATION                       │
└─────────────────────────────────────────────────────────────────────────────┘

START
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: SERVER PREPARATION                                      │
│ ─────────────────────────────────────────────────────────────── │
│ [ ] SSH into VPS: ssh -i ~/.ssh/hetzner root@204.168.184.49     │
│ [ ] Update system: apt update && apt upgrade -y                 │
│ [ ] Install dependencies:                                       │
│     - python3, python3-venv, python3-pip                        │
│     - git, curl, wget                                           │
│     - nodejs (v20+), npm                                        │
│ [ ] Install Caddy (web server):                                 │
│     curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/  │
│     setup.deb.sh' | sudo -E bash                                │
│     apt install caddy                                           │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: REPOSITORY SETUP                                        │
│ ─────────────────────────────────────────────────────────────── │
│ [ ] Clone repository:                                           │
│     git clone https://github.com/m5trevino/ai-engine.git        │
│     cd ai-engine                                                │
│ [ ] Create .env file: cp .env.example .env                      │
│ [ ] Edit .env and add API keys:                                 │
│     • GROQ_KEYS="LABEL1:key1,LABEL2:key2,..."                   │
│     • GOOGLE_KEYS="LABEL1:key1,..."                             │
│     • DEEPSEEK_KEYS="sk-xxx"                                    │
│     • MISTRAL_KEYS="sk-xxx"                                     │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: PYTHON ENVIRONMENT                                      │
│ ─────────────────────────────────────────────────────────────── │
│ [ ] Create virtual environment:                                 │
│     python3 -m venv .venv                                       │
│ [ ] Activate: source .venv/bin/activate                         │
│ [ ] Install dependencies:                                       │
│     pip install -r requirements.txt                             │
│ [ ] Verify imports:                                             │
│     python3 -c "from app.main import app; print('OK')"          │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: FRONTEND BUILD                                          │
│ ─────────────────────────────────────────────────────────────── │
│ [ ] Navigate to UI: cd ui                                       │
│ [ ] Install npm packages: npm install                           │
│ [ ] Build for production: npm run build                         │
│     └── Outputs to: ../app/static/                              │
│ [ ] Verify build: ls -la ../app/static/                         │
│     └── Should show: index.html, assets/                        │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: SYSTEMD SERVICE                                         │
│ ─────────────────────────────────────────────────────────────── │
│ [ ] Create service file:                                        │
│     /etc/systemd/system/peacock-engine.service                  │
│     (See full config in VPS Infrastructure section)             │
│ [ ] Enable service:                                             │
│     sudo systemctl daemon-reload                                │
│     sudo systemctl enable peacock-engine                        │
│ [ ] Start service:                                              │
│     sudo systemctl start peacock-engine                         │
│ [ ] Verify status:                                              │
│     sudo systemctl status peacock-engine                        │
│     (Should show: active (running))                             │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: CADDY REVERSE PROXY                                     │
│ ─────────────────────────────────────────────────────────────── │
│ [ ] Copy Caddyfile to /etc/caddy/Caddyfile                      │
│     OR use: /root/ai-engine/deploy/Caddyfile                    │
│ [ ] Run setup script:                                           │
│     sudo bash deploy/setup-caddy-infra.sh                       │
│ [ ] Reload Caddy:                                               │
│     sudo caddy reload --config /etc/caddy/Caddyfile             │
│ [ ] Verify Caddy status:                                        │
│     sudo systemctl status caddy                                 │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 7: SYNCTHING SETUP (Optional)                              │
│ ─────────────────────────────────────────────────────────────── │
│ [ ] Install Syncthing:                                          │
│     apt install syncthing                                       │
│ [ ] Enable service:                                             │
│     systemctl enable syncthing@root                             │
│     systemctl start syncthing@root                              │
│ [ ] Configure via web UI:                                       │
│     http://204.168.184.49:8384                                  │
│ [ ] Set VPS as Introducer                                       │
│ [ ] Add sync folders:                                           │
│     • /root/herbert/liquid-semiotic/english                     │
│     • /root/herbert/liquid-semiotic/invariants                  │
│     • /root/herbert/liquid-semiotic/legos                       │
│     • /root/herbert/liquid-semiotic/semiotic-mold               │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 8: VERIFICATION                                            │
│ ─────────────────────────────────────────────────────────────── │
│ [ ] Health check:                                               │
│     curl https://chat.save-aichats.com/health                   │
│ [ ] API test:                                                   │
│     curl https://engine.save-aichats.com/v1/chat/models         │
│ [ ] Frontend test:                                              │
│     Open https://chat.save-aichats.com in browser               │
│ [ ] WebSocket test:                                             │
│     Connect to wss://chat.save-aichats.com/v1/chat/ws/ws        │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
DEPLOYMENT COMPLETE ✅

```

### Workflow 2: Code Update & Redeployment

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    WORKFLOW 2: CODE UPDATE & REDEPLOY                       │
└─────────────────────────────────────────────────────────────────────────────┘

START (Local Development Machine)
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: LOCAL DEVELOPMENT                                       │
│ ─────────────────────────────────────────────────────────────── │
│ [ ] Make code changes in local repository                       │
│ [ ] Test locally:                                               │
│     cd ui && npm run dev  # (Port 3000)                         │
│     cd .. && python -m uvicorn app.main:app --reload           │
│ [ ] Build frontend:                                             │
│     cd ui && npm run build                                      │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: VERSION CONTROL                                         │
│ ─────────────────────────────────────────────────────────────── │
│ [ ] Stage changes: git add .                                    │
│ [ ] Commit with semantic message:                               │
│     git commit -m "FEAT: Add new payload striker UI"            │
│ [ ] Push to origin: git push origin main                        │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: VPS PULL & RESTART (On VPS)                             │
│ ─────────────────────────────────────────────────────────────── │
│ [ ] SSH to VPS:                                                 │
│     ssh -i ~/.ssh/hetzner root@204.168.184.49                   │
│ [ ] Navigate to project: cd ~/ai-engine                         │
│ [ ] Pull latest: git pull origin main                           │
│ [ ] Rebuild frontend (if UI changed):                           │
│     cd ui && npm run build && cd ..                             │
│ [ ] Restart service:                                            │
│     sudo systemctl restart peacock-engine                       │
│     OR use: ./launch.sh                                         │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: VERIFICATION                                            │
│ ─────────────────────────────────────────────────────────────── │
│ [ ] Check logs:                                                 │
│     sudo journalctl -u peacock-engine -f                        │
│ [ ] Verify health endpoint:                                     │
│     curl https://chat.save-aichats.com/health                   │
│ [ ] Test new functionality in browser                           │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
UPDATE COMPLETE ✅

```

---

## ✅ IMPLEMENTATION CHECKLISTS

### Pre-Deployment Checklist

- [ ] **Server Requirements Met**
  - [ ] Ubuntu 22.04 LTS or newer
  - [ ] Minimum 2GB RAM (4GB recommended)
  - [ ] 10GB free disk space
  - [ ] Python 3.11+ installed
  - [ ] Node.js 20+ installed
  - [ ] Ports 22, 80, 443, 3099 accessible

- [ ] **DNS Configuration**
  - [ ] `chat.save-aichats.com` → VPS IP
  - [ ] `engine.save-aichats.com` → VPS IP
  - [ ] SSL certificates will be auto-managed by Caddy

- [ ] **API Keys Secured**
  - [ ] GROQ_KEYS (minimum 1 key, recommend 3+)
  - [ ] GOOGLE_KEYS (minimum 1 key, recommend 2+)
  - [ ] DEEPSEEK_KEYS (optional)
  - [ ] MISTRAL_KEYS (optional)
  - [ ] All keys stored in `.env` (never committed)

- [ ] **File Structure Prepared**
  - [ ] `/root/herbert/liquid-semiotic/english` created
  - [ ] `/root/herbert/liquid-semiotic/invariants` created
  - [ ] `/root/herbert/liquid-semiotic/legos` created
  - [ ] `/root/herbert/liquid-semiotic/semiotic-mold` created

### Post-Deployment Verification Checklist

- [ ] **Service Health**
  - [ ] `systemctl status peacock-engine` shows "active (running)"
  - [ ] `systemctl status caddy` shows "active (running)"
  - [ ] Health endpoint returns 200: `curl https://chat.save-aichats.com/health`

- [ ] **API Functionality**
  - [ ] Model list loads: `curl https://engine.save-aichats.com/v1/models`
  - [ ] Chat endpoint responds: POST to `/v1/chat`
  - [ ] Streaming works: WebSocket connects to `/v1/chat/ws/ws`
  - [ ] File system API accessible: `/v1/fs/browse`

- [ ] **Frontend Verification**
  - [ ] Main page loads without 404s
  - [ ] Model dropdown populates
  - [ ] API key usage displays
  - [ ] WebSocket connection establishes
  - [ ] No console errors (F12 → Console)

- [ ] **Security Verification**
  - [ ] HTTPS certificates valid
  - [ ] Security headers present (HSTS, X-Frame-Options)
  - [ ] API keys not exposed in frontend
  - [ ] `.env` file has 600 permissions

### Daily Operations Checklist

- [ ] **Morning Health Check**
  - [ ] Review overnight logs: `journalctl -u peacock-engine --since "24 hours ago"`
  - [ ] Check key pool status: `curl https://engine.save-aichats.com/health`
  - [ ] Verify disk space: `df -h`
  - [ ] Check memory usage: `free -h`

- [ ] **Key Management**
  - [ ] Review key rotation logs
  - [ ] Check for 429 rate limit errors
  - [ ] Verify no keys are exhausted (RPD limits)

- [ ] **Backup Verification**
  - [ ] peacock.db backed up (if critical data)
  - [ ] Prompts directory synced (Syncthing status)
  - [ ] Git commits pushed to origin

---

## 🔌 VITE + FASTAPI WIRING

### The Build-to-Serve Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEVELOPMENT PHASE                             │
│                                                                  │
│   Local Machine                    VPS                          │
│   ┌──────────┐                     ┌──────────┐                 │
│   │  Vite    │  HMR on port 3000   │  FastAPI │  Port 3099      │
│   │  Dev     │◄───────────────────►│  Dev     │                 │
│   │  Server  │  API proxy config   │  Server  │                 │
│   └──────────┘                     └──────────┘                 │
│        │                                 │                       │
│        │ Proxy: /v1 → localhost:3099     │                       │
│        └─────────────────────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ npm run build
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   PRODUCTION PHASE                               │
│                                                                  │
│   cd ui && npm run build                                        │
│        │                                                         │
│        ▼                                                         │
│   ┌──────────────────────────────────────────┐                  │
│   │  Vite bundles React app                  │                  │
│   │  ├── index.html                          │                  │
│   │  ├── assets/index-[hash].js              │                  │
│   │  └── assets/index-[hash].css             │                  │
│   │                                          │                  │
│   │  Output: ../app/static/                  │                  │
│   └──────────────────────────────────────────┘                  │
│        │                                                         │
│        ▼                                                         │
│   FastAPI serves static files from app/static/                  │
│   ┌──────────────────────────────────────────┐                  │
│   │  app.mount("/", StaticFiles(...))        │                  │
│   │  └── index.html served at root           │                  │
│   └──────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

### Configuration Files

**Vite Config** (`ui/vite.config.ts`):
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  base: '/',                    // Root-relative paths
  plugins: [react(), tailwindcss()],
  build: {
    outDir: '../app/static',    // Critical: Build to FastAPI static folder
    emptyOutDir: true,          // Clean before build
  },
  server: {
    proxy: {
      '/v1': 'http://localhost:3099',  // Dev proxy to FastAPI
      '/health': 'http://localhost:3099'
    }
  }
});
```

**FastAPI Static Mount** (`app/main.py`):
```python
from fastapi.staticfiles import StaticFiles

# API routes FIRST (lines 65-89)
app.include_router(chat_router, prefix="/v1/chat")
app.include_router(models_router, prefix="/v1/models")
# ... all other API routes

# Static files LAST (line 124-126)
if os.path.exists("app/static"):
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    app.mount("/", StaticFiles(directory="app/static", html=True), name="root_ui")

# SPA Catch-all for React Router (lines 130-142)
@app.get("/{full_path:path}")
async def catch_all(full_path: str):
    if full_path.startswith("v1/") or full_path.startswith("static/"):
        return {"detail": "Not Found"}
    return FileResponse("app/static/index.html")
```

### Route Priority Order (CRITICAL)

```
Priority 1: API Routes (/v1/*)
    ├── /v1/chat/*
    ├── /v1/models/*
    ├── /v1/fs/*
    ├── /v1/keys/*
    └── ... all API endpoints

Priority 2: Static Files (/static/*)
    └── JS, CSS, images, fonts

Priority 3: SPA Root (/*)
    └── index.html (React Router handles client-side)
```

**Why this order matters**: If static files were mounted first, a request to `/v1/chat/models` would try to find a file at `app/static/v1/chat/models` and return 404, instead of hitting the API route.

---

## 🖥️ VPS INFRASTRUCTURE

### Systemd Service Deep Dive

**File**: `/etc/systemd/system/peacock-engine.service`

```ini
[Unit]
Description=PEACOCK ENGINE V3 - AI Orchestration Server
After=network.target                    # Start after network is ready

[Service]
Type=simple                             # Simple process (not forking)
User=root                               # Run as root (for /root/ access)
Group=root
WorkingDirectory=/root/ai-engine        # Critical: Sets CWD for relative paths

# Environment
Environment=PATH=/root/ai-engine/.venv/bin  # Python venv binaries
Environment=PYTHONPATH=/root/ai-engine      # Python import path
EnvironmentFile=/root/ai-engine/.env        # Load API keys from file

# Restart Policy - KEY FOR ALWAYS-ON
Restart=always                          # Restart on any exit
RestartSec=5                            # Wait 5 seconds before restart
StartLimitInterval=60s                  # Time window for start limits
StartLimitBurst=3                       # Max restarts in interval

# Security Hardening
NoNewPrivileges=false                   # Allow privilege escalation (for root)
PrivateTmp=true                         # Isolate /tmp
ProtectSystem=full                      # Read-only system dirs
ProtectHome=false                       # Allow access to /root
ReadWritePaths=/root/ai-engine/         # Explicit write permissions

# Resource Limits
LimitNOFILE=65535                       # Max open files
LimitNPROC=4096                         # Max processes

# Logging
StandardOutput=journal                  # Log to systemd journal
StandardError=journal
SyslogIdentifier=peacock-engine         # Tag for log filtering

# Command to execute
ExecStart=/root/ai-engine/.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \                  # Bind to localhost (Caddy proxies)
    --port 3099 \                       # Engine port
    --workers 2 \                       # Worker processes
    --access-log \                      # Log HTTP requests
    --proxy-headers                     # Trust X-Forwarded-* headers

[Install]
WantedBy=multi-user.target              # Start with system
```

### Essential Systemd Commands

```bash
# Start/stop/restart
sudo systemctl start peacock-engine
sudo systemctl stop peacock-engine
sudo systemctl restart peacock-engine

# Check status
sudo systemctl status peacock-engine

# Enable/disable auto-start
sudo systemctl enable peacock-engine
sudo systemctl disable peacock-engine

# View logs
sudo journalctl -u peacock-engine              # All logs
sudo journalctl -u peacock-engine -f           # Follow (tail -f)
sudo journalctl -u peacock-engine --since "1 hour ago"
sudo journalctl -u peacock-engine -n 100       # Last 100 lines

# Check for errors
sudo journalctl -u peacock-engine -p err
```

### Caddy Configuration Explained

**File**: `/root/ai-engine/deploy/Caddyfile`

```caddy
{
    admin off                           # Disable admin API (security)
}

# Security Headers Snippet
(security) {
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Referrer-Policy "strict-origin-when-cross-origin"
        -Server                         # Remove Server header
    }
}

# Chat UI Subdomain
chat.save-aichats.com {
    import security                     # Apply security headers
    encode gzip zstd                    # Enable compression
    reverse_proxy localhost:3099        # Forward to FastAPI
    
    log {
        output file /var/log/caddy/chat-access.log {
            roll_size 10MB              # Rotate at 10MB
            roll_keep 5                 # Keep 5 rotated files
        }
    }
}

# API Engine Subdomain  
engine.save-aichats.com {
    import security
    encode gzip
    reverse_proxy localhost:3099
}
```

**Why Caddy over Nginx?**
- Automatic HTTPS (Let's Encrypt)
- Simpler configuration
- HTTP/2 and HTTP/3 support out of box
- Dynamic configuration reloading

---

## 🔄 SYNCTHING CONFIGURATION

### The Sync Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     SYNCTHING TOPOLOGY                          │
│                                                                  │
│                        ┌──────────────┐                         │
│                        │  VPS (Shell) │  ◄── Introducer         │
│                        │  204.168.184 │                         │
│                        │     .49      │                         │
│                        └──────┬───────┘                         │
│                               │                                 │
│              ┌────────────────┼────────────────┐                │
│              │                │                │                │
│              ▼                ▼                ▼                │
│       ┌──────────┐     ┌──────────┐     ┌──────────┐           │
│       │  Local   │     │  Laptop  │     │  Backup  │           │
│       │   PC     │     │  (Work)  │     │  Server  │           │
│       └──────────┘     └──────────┘     └──────────┘           │
│                                                                  │
│   All devices sync bidirectionally through VPS hub              │
└─────────────────────────────────────────────────────────────────┘
```

### Folder Sync Mapping

| Folder ID | VPS Path | Local Path | Purpose |
|-----------|----------|------------|---------|
| `liquid-english` | `/root/herbert/liquid-semiotic/english` | `~/herbert/liquid-semiotic/english` | Input payloads (distilled repos) |
| `liquid-invariants` | `/root/herbert/liquid-semiotic/invariants` | `~/herbert/liquid-semiotic/invariants` | LLM outputs |
| `liquid-legos` | `/root/herbert/liquid-semiotic/legos` | `~/herbert/liquid-semiotic/legos` | Tree-sitter output |
| `liquid-mold` | `/root/herbert/liquid-semiotic/semiotic-mold` | `~/herbert/liquid-semiotic/semiotic-mold` | Prompts/templates |

### Setup Commands

```bash
# On VPS
sudo apt install syncthing
sudo systemctl enable syncthing@root
sudo systemctl start syncthing@root
# Access: http://204.168.184.49:8384

# On Local Machine
# Download from https://syncthing.net/downloads/
# Or: brew install syncthing (macOS)
# Or: apt install syncthing (Linux)

# Configure VPS as Introducer
# 1. Open VPS web UI: http://204.168.184.49:8384
# 2. Settings → Connections → Check "Introducer"
# 3. Add device (Local PC) → Share folders
```

---

## 🧮 TOKEN COUNTER SYSTEM

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  TOKEN COUNTING PIPELINE                        │
│                                                                  │
│  Request comes in with:                                         │
│  • model_id: "gemini-2.5-pro"                                   │
│  • prompt: "Explain quantum..."                                 │
│  • files: ["/path/to/context.py"]                               │
│                                                                  │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────┐                    │
│  │  PeacockTokenCounter.count_prompt_tokens│                    │
│  └─────────────────────────────────────────┘                    │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────┐                    │
│  │  Lookup ModelConfig in MODEL_REGISTRY   │                    │
│  │  └── gateway: "google"                  │                    │
│  └─────────────────────────────────────────┘                    │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────────────────────┐    ┌──────────────────────┐   │
│  │  Gateway: "google"           │    │  Gateway: "groq"     │   │
│  │                              │    │                      │   │
│  │  GeminiTokenCounter          │    │  GroqTokenCounter    │   │
│  │  ├── API Method (accurate)   │    │  ├── tiktoken        │   │
│  │  │   └── google-genai SDK     │    │  │   └── cl100k_base│   │
│  │  └── Estimation (fallback)   │    │  └── Fallback: char/4│   │
│  │      └── Regex tokenizer      │    │                      │   │
│  └──────────────────────────────┘    └──────────────────────┘   │
│                                                                  │
│  Special Handling:                                               │
│  • Images: 258 tokens (≤384px) or tiles                         │
│  • Video: 263 tokens/sec                                        │
│  • Audio: 32 tokens/sec                                         │
│  • PDFs: treated as images (pages)                              │
└─────────────────────────────────────────────────────────────────┘
```

### File Locations

| File | Path | Purpose |
|------|------|---------|
| Unified Counter | `app/utils/token_counter.py` | Main coordinator |
| Gemini Counter | `app/utils/gemini_token_counter.py` | Google API counting |
| Groq Counter | `app/utils/groq_token_counter.py` | tiktoken counting |
| Model Registry | `app/config.py` | Rates & pricing |

---

## 💬 UI CHAT WIRING

### Connection Methods

```
┌─────────────────────────────────────────────────────────────────┐
│                   CONNECTION OPTIONS                            │
│                                                                  │
│  1. REST API (Simple)                                           │
│     POST /v1/chat                                               │
│     └── JSON request/response                                   │
│                                                                  │
│  2. Server-Sent Events (Streaming)                              │
│     POST /v1/chat/stream                                        │
│     └── text/event-stream                                       │
│     └── Chunk-by-chunk delivery                                 │
│                                                                  │
│  3. WebSocket (Real-time Bidirectional)                         │
│     wss://chat.save-aichats.com/v1/chat/ws/ws                   │
│     └── Configurable session                                    │
│     └── Live typing effect                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### WebSocket Protocol

```javascript
// Connection
const ws = new WebSocket('wss://chat.save-aichats.com/v1/chat/ws/ws');

// Protocol Flow
┌──────────┐                                    ┌──────────┐
│  Client  │──────► CONNECT ───────────────────►│  Server  │
│          │◄────── ACCEPTED ◄──────────────────│          │
│          │                                    │          │
│          │──────► {                          │          │
│          │        type: "config",            │          │
│          │        model: "gemini-2.5-pro",   │          │
│          │        temp: 0.7,                 │          │
│          │        files: []                  │          │
│          │      } ─────────────────────────►│          │
│          │◄────── {                          │          │
│          │        type: "info",              │          │
│          │        content: "CONFIG_SYNC:..." │          │
│          │      } ◄─────────────────────────│          │
│          │                                    │          │
│          │──────► {                          │          │
│          │        type: "prompt",            │          │
│          │        content: "Hello AI"        │          │
│          │      } ─────────────────────────►│          │
│          │                                    │          │
│          │◄────── {                          │          │
│          │        type: "content",           │          │
│          │        content: "Hello!"          │          │
│      ┌───┘      } ◄─────────────────────────│          │
│      │   (stream continues...)               │          │
│      ▼                                        │          │
│          │◄────── {                          │          │
│          │        type: "metadata",          │          │
│          │        usage: {                   │          │
│          │          prompt_tokens: 10,       │          │
│          │          completion_tokens: 150,  │          │
│          │          total_tokens: 160        │          │
│          │        }                          │          │
│          │      } ◄─────────────────────────│          │
└──────────┘                                    └──────────┘
```

---

## 💥 PAYLOAD STRIKER ARCHITECTURE

### Dual-Mode System

```
┌─────────────────────────────────────────────────────────────────┐
│                    PAYLOAD STRIKER MODES                        │
│                                                                  │
│  ┌─────────────────────────┐  ┌─────────────────────────────┐  │
│  │    MONOLITHIC MODE      │  │      CAMPAIGN MODE          │  │
│  │                         │  │                             │  │
│  │  One Prompt + Many      │  │  Multiple Prompt Groups     │  │
│  │  Payloads → One Strike  │  │  Each with Own Payloads     │  │
│  │                         │  │                             │  │
│  │  ┌─────────────────┐   │  │  ┌───────────────────────┐  │  │
│  │  │  Prompt A       │   │  │  │ Group Alpha           │  │  │
│  │  │                 │   │  │  │ • Prompt: "Analyze X" │  │  │
│  │  │  Payloads:      │   │  │  │ • Payloads: [1,2,3]   │  │  │
│  │  │  • file1.py     │   │  │  └───────────────────────┘  │  │
│  │  │  • file2.py     │   │  │                             │  │
│  │  │  • file3.py     │   │  │  ┌───────────────────────┐  │  │
│  │  │  (100 files)    │   │  │  │ Group Beta            │  │  │
│  │  └─────────────────┘   │  │  │ • Prompt: "Fix bugs"  │  │  │
│  │                        │  │  │ • Payloads: [4,5,6]   │  │  │
│  │  All → One LLM Call    │  │  └───────────────────────┘  │  │
│  │  (if context fits)     │  │                             │  │
│  │                        │  │  Execute sequentially       │  │
│  └─────────────────────────┘  └─────────────────────────────┘  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              EXECUTION THREADING OPTIONS                │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ ULTRA MODE (Continuous) │ BATCH MODE (Wave)            │    │
│  │                         │                              │    │
│  │ Workers never idle      │ Fire N at once               │    │
│  │ As each completes,      │ Wait for all N               │    │
│  │ immediately start next  │ Then fire next batch         │    │
│  │                         │                              │    │
│  │ [1] [2] [3] [4] [5]     │ [1] [2] [3] ← Batch 1        │    │
│  │  ↓   ↓   ↓   ↓   ↓      │  ↓   ↓   ↓                   │    │
│  │ [6] [7] [8] ...         │ [4] [5] [6] ← Batch 2        │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔧 TROUBLESHOOTING MATRIX

### Common Issues & Solutions

| Symptom | Cause | Solution |
|---------|-------|----------|
| `404 Not Found` on API | Static files mounted before API | Ensure API routes registered before StaticFiles in main.py |
| `502 Bad Gateway` | FastAPI not running | Check `systemctl status peacock-engine` |
| Models not loading | CORS issue | Check `app.add_middleware(CORSMiddleware)` |
| WebSocket disconnects | Wrong URL format | Use `wss://` not `ws://` for HTTPS sites |
| Build fails | Missing dependencies | Run `npm install` in ui/ directory |
| Token count wrong | tiktoken not installed | `pip install tiktoken` in venv |
| Rate limit errors | Key exhausted | Add more keys to GROQ_KEYS/GOOGLE_KEYS |
| Syncthing conflicts | File permissions | Ensure both sides have write access |

### Emergency Recovery

```bash
# Complete service restart sequence
sudo systemctl stop peacock-engine
sudo systemctl stop caddy
cd ~/ai-engine
git pull origin main
cd ui && npm run build && cd ..
sudo systemctl start peacock-engine
sudo systemctl start caddy
sudo systemctl status peacock-engine
```

---

## 📚 APPENDIX

### A. URL Reference Quick Sheet

| Service | URL | Port |
|---------|-----|------|
| Chat UI (Prod) | https://chat.save-aichats.com | 443 |
| Engine API | https://engine.save-aichats.com | 443 |
| Health Check | https://chat.save-aichats.com/health | 443 |
| WebSocket | wss://chat.save-aichats.com/v1/chat/ws/ws | 443 |
| Local Dev UI | http://localhost:3000 | 3000 |
| Local Dev API | http://localhost:3099 | 3099 |
| Syncthing VPS | http://204.168.184.49:8384 | 8384 |
| Syncthing Local | http://localhost:8384 | 8384 |

### B. File Locations Reference

| Component | Path | Notes |
|-----------|------|-------|
| Main App | `/root/ai-engine/app/main.py` | FastAPI entry point |
| UI Source | `/root/ai-engine/ui/src/` | React + TypeScript |
| UI Build | `/root/ai-engine/app/static/` | Vite output |
| Config | `/root/ai-engine/app/config.py` | Model registry |
| Token Counters | `/root/ai-engine/app/utils/` | Gemini, Groq, Unified |
| Logs | `/var/log/caddy/` | Caddy access logs |
| System Logs | `journalctl -u peacock-engine` | Service logs |
| Database | `/root/ai-engine/peacock.db` | SQLite conversations |
| Vault | `/root/ai-engine/vault/` | Strike logs |
| Liquid Semiotic | `/root/herbert/liquid-semiotic/` | Syncthing sync |

### C. Performance Tuning

```ini
# /etc/systemd/system/peacock-engine.service additions for high load
[Service]
# Increase workers (CPU cores * 2 + 1)
ExecStart=/root/ai-engine/.venv/bin/uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 3099 \
    --workers 4 \                    # Increase for 4+ core VPS
    --loop uvloop \                  # Faster event loop
    --http httptools \               # Faster HTTP parser
    --access-log
```

---

## 🎯 END OF MANUAL

**Document Control**:
- Version: 3.0.0
- Classification: OPERATIONAL
- Last Updated: 2026-04-11
- Next Review: On major release

**Emergency Contacts**:
- System Status: `curl https://chat.save-aichats.com/health`
- Logs: `sudo journalctl -u peacock-engine -f`
- Restart: `sudo systemctl restart peacock-engine`

---

*"The peacock spreads its tail not for show, but to demonstrate that every feather is in its place."*
