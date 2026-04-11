# 🦚 PEACOCK ENGINE V3 - WORKFLOW VISUALS

> Complete user journey maps and workflow diagrams

---

## 1. User Onboarding Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           NEW USER JOURNEY                                  │
└─────────────────────────────────────────────────────────────────────────────┘

FIRST VISIT
     │
     ▼
┌──────────────────────────────┐
│  https://chat.save-aichats   │
│        .com                  │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│     Caddy (Port 443)         │
│  • HTTPS handshake           │
│  • Security headers          │
│  • gzip compression          │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│   React SPA Loads            │
│  • index.html                │
│  • Bundle JS/CSS             │
│  • Fonts & assets            │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐      NO     ┌──────────────────────────┐
│  API Health Check            │────────────►│  Show Error Screen       │
│  GET /health                 │             │  "Engine Offline"        │
└────────┬─────────────────────┘             └──────────────────────────┘
         │ YES
         ▼
┌──────────────────────────────┐
│  Fetch Model Registry        │
│  GET /v1/models              │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  Populate UI                 │
│  • Model dropdown            │
│  • Key usage stats           │
│  • Settings panel            │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│  DASHBOARD READY             │
│  ┌────────────────────────┐  │
│  │  [Select Model ▼]      │  │
│  │                        │  │
│  │  ┌──────────────────┐  │  │
│  │  │ Chat history...  │  │  │
│  │  │                  │  │  │
│  │  └──────────────────┘  │  │
│  │                        │  │
│  │  [Type message...] [►] │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
```

---

## 2. Chat Session Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CHAT SESSION LIFECYCLE                              │
└─────────────────────────────────────────────────────────────────────────────┘

USER ACTION                    SYSTEM RESPONSE
────────────────────────────────────────────────────────

┌──────────────────┐
│ Types message    │
│ "Explain quantum │
│  computing"      │
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────┐
│ User clicks SEND             │
│                              │
│ Frontend:                    │
│ • Capture input              │
│ • Show loading state         │
│ • Prepare WebSocket/REST     │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ REST API Call                │
│ POST /v1/chat                │
│                              │
│ Body: {                      │
│   model: "gemini-2.5-pro",   │
│   prompt: "Explain...",      │
│   temp: 0.7                  │
│ }                            │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ Backend Processing           │
│                              │
│ 1. Validate model exists     │
│ 2. Check rate limits         │
│ 3. Rotate to next key        │
│ 4. Count tokens (pre-flight) │
│ 5. Execute strike            │
│ 6. Log to vault              │
│ 7. Save to database          │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ LLM Provider API             │
│ Google/Groq/DeepSeek/...     │
│                              │
│ • Request sent               │
│ • Streaming response         │
│ • Content chunks received    │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ Response Processing          │
│                              │
│ • Parse chunks               │
│ • Calculate final tokens     │
│ • Compute cost               │
│ • Format response            │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ Return to Frontend           │
│                              │
│ {                            │
│   content: "Quantum...",     │
│   model: "gemini-2.5-pro",   │
│   usage: {                   │
│     prompt_tokens: 15,       │
│     completion_tokens: 234,  │
│     total_tokens: 249        │
│   },                         │
│   duration_ms: 2847          │
│ }                            │
└────────┬─────────────────────┘
         │
         ▼
┌──────────────────────────────┐
│ Frontend Display             │
│                              │
│ • Render Markdown            │
│ • Show token count           │
│ • Update usage stats         │
│ • Enable new input           │
└──────────────────────────────┘

[CONTINUE LOOP...]
```

---

## 3. Payload Striker Batch Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PAYLOAD STRIKER - BATCH PROCESSING                       │
└─────────────────────────────────────────────────────────────────────────────┘

PREPARATION PHASE
─────────────────

┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 1: SELECT PROMPT                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Available Prompts:                                               │   │
│  │  ○ analyze_code.md    "Analyze this code for bugs..."             │   │
│  │  ● document_api.md    "Generate API documentation..."  ◄── SELECTED│   │
│  │  ○ refactor.md        "Suggest refactoring..."                    │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 2: LOAD PAYLOADS                                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Ammo Pile (english/):                                          │   │
│  │  □ auth.py                                                      │   │
│  │  ☑ database.py           ◄── LOADED                             │   │
│  │  ☑ models.py             ◄── LOADED                             │   │
│  │  ☑ routes.py             ◄── LOADED                             │   │
│  │  □ utils.py                                                     │   │
│  │                                                                 │   │
│  │  Loaded: 3 files                                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 3: CONFIGURE STRIKE                                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  Settings:                                                      │   │
│  │  • Model: gemini-2.5-flash                                      │   │
│  │  • Temperature: 0.3                                             │   │
│  │  • Max Tokens: 2000                                             │   │
│  │  • Threads: 3                                                   │   │
│  │  • Mode: Batch (wait for all)                                   │   │
│  │  • Key Rotation: Aggressive                                     │   │
│  │                                                                 │   │
│  │  Sequence:                                                      │   │
│  │  [1] database.py ──► Key A ──► Delay 1000ms                     │   │
│  │  [2] models.py   ──► Key B ──► Delay 1000ms                     │   │
│  │  [3] routes.py   ──► Key C ──► Delay 1000ms                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
EXECUTION PHASE
───────────────

┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 4: INITIATE STRIKE                                                │
│                              ┌──────────────────────────────────────┐   │
│                              │  [  ▶  LAUNCH SEQUENCE  ]            │   │
│                              └──────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 5: EXECUTION MONITOR                                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                                                                 │   │
│  │  🟢 database.py    COMPLETE    2.3s    342 tokens    $0.002     │   │
│  │  🟡 models.py      RUNNING     1.8s    ---          ---         │   │
│  │  ⚪ routes.py      QUEUED      ---     ---          ---         │   │
│  │                                                                 │   │
│  │  Progress: [████████░░░░░░░░░░░░░░] 33%                         │   │
│  │                                                                 │   │
│  │  Live Log:                                                      │   │
│  │  [14:32:01] Strike #1 INIT  ──► Key A                           │   │
│  │  [14:32:03] Strike #1 OK    ──► 342 tokens                      │   │
│  │  [14:32:04] Strike #2 INIT  ──► Key B                           │   │
│  │                                                                 │   │
│  │  Gauges:                                                        │   │
│  │  TPS: 45.2    RPM: 28/60    Cost: $0.002    Queue: 1/3          │   │
│  │                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
COMPLETION PHASE
────────────────

┌─────────────────────────────────────────────────────────────────────────┐
│  STEP 6: BATCH COMPLETE                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  ✅ ALL STRIKES COMPLETE                                        │   │
│  │                                                                 │   │
│  │  Results:                                                       │   │
│  │  ├─ database.py-done.04-09-26-1432.md    ✓                      │   │
│  │  ├─ models.py-done.04-09-26-1433.md      ✓                      │   │
│  │  └─ routes.py-done.04-09-26-1434.md      ✓                      │   │
│  │                                                                 │   │
│  │  Summary:                                                       │   │
│  │  • Total Time: 4.2s                                             │   │
│  │  • Total Tokens: 1,247                                          │   │
│  │  • Total Cost: $0.008                                           │   │
│  │  • Keys Used: A, B, C                                           │   │
│  │                                                                 │   │
│  │  [View Results] [Download ZIP] [New Batch]                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. File System Integration Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      FILE SYSTEM INTEGRATION                                │
└─────────────────────────────────────────────────────────────────────────────┘

LOCAL MACHINE (Development)
───────────────────────────
    │
    │ Syncthing
    │ (Automatic sync)
    ▼
┌─────────────────────────────────────────────────────────────┐
│  ~/herbert/liquid-semiotic/                                  │
│  ├── english/         ◄── Your source files                 │
│  │   ├── project1/                                           │
│  │   └── project2/                                           │
│  ├── invariants/      ◄── LLM outputs (synced back)         │
│  ├── legos/           ◄── Tree-sitter outputs               │
│  └── semiotic-mold/   ◄── Prompts & templates               │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Encrypted TLS tunnel
                         │
                         ▼
VPS (Production)
────────────────
┌─────────────────────────────────────────────────────────────┐
│  /root/herbert/liquid-semiotic/                              │
│  ├── english/                                                │
│  ├── invariants/                                             │
│  ├── legos/                                                  │
│  └── semiotic-mold/                                          │
└────────┬────────────────────────────────────────────────────┘
         │
         │ Read/Write
         ▼
┌─────────────────────────────────────────────────────────────┐
│  PEACOCK ENGINE                                              │
│  • Payload Striker reads from english/                      │
│  • Outputs written to invariants/                           │
│  • Prompts loaded from semiotic-mold/                       │
└─────────────────────────────────────────────────────────────┘
         │
         │ (Results synced back)
         ▼
LOCAL MACHINE
─────────────
┌─────────────────────────────────────────────────────────────┐
│  ~/herbert/liquid-semiotic/invariants/                       │
│  ├── file1-done.04-09-26-1432.md                            │
│  ├── file2-done.04-09-26-1433.md                            │
│  └── ...                                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Error Handling & Recovery Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      ERROR HANDLING MATRIX                                  │
└─────────────────────────────────────────────────────────────────────────────┘

ERROR DETECTED
      │
      ▼
┌──────────────────────────┐
│ Classify Error Type      │
└────────┬─────────────────┘
         │
    ┌────┴────┬────────────┬────────────┬────────────┐
    │         │            │            │            │
    ▼         ▼            ▼            ▼            ▼
┌───────┐ ┌───────┐   ┌───────┐   ┌───────┐   ┌───────┐
│ 429   │ │ 500   │   │ 502   │   │ Timeout│   │ Other │
│ Rate  │ │ Server│   │ Bad   │   │        │   │ Error │
│ Limit │ │ Error │   │ Gateway│   │        │   │       │
└───┬───┘ └───┬───┘   └───┬───┘   └───┬───┘   └───┬───┘
    │         │           │           │           │
    ▼         ▼           ▼           ▼           ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ACTION: │ │ACTION: │ │ACTION: │ │ACTION: │ │ACTION: │
│• Mark  │ │• Log   │ │• Check │ │• Retry │ │• Log   │
│  key   │ │  error  │ │  if    │ │  with  │ │  &     │
│  HOT   │ │• Notify │ │  FastAPI│ │  delay │ │  notify│
│• Cool  │ │  admin  │ │  is    │ │• Mark  │ │  admin │
│  down  │ │         │ │  running│ │  failed│ │         │
│  60s   │ │         │ │• Restart│ │  after │ │         │
│• Retry │ │         │ │  if not│ │  3x    │ │         │
│  with  │ │         │ │         │ │         │ │         │
│  next  │ │         │ │         │ │         │ │         │
│  key   │ │         │ │         │ │         │ │         │
└────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘ └────┬───┘
     │          │          │          │          │
     └──────────┴──────────┴──────────┴──────────┘
                         │
                         ▼
            ┌────────────────────────┐
            │ Log to Vault           │
            │ /vault/failed/PEA-XXX  │
            │ with full context      │
            └────────────────────────┘
                         │
            ┌────────────┴────────────┐
            │                         │
            ▼                         ▼
    ┌───────────────┐        ┌───────────────┐
    │ Auto-Retry?   │        │ Give up       │
    │ [Bulldoze ON] │        │ Mark RED      │
    └───────┬───────┘        │ Leave in queue│
            │ YES            │ for manual fix│
            ▼                └───────────────┘
    ┌───────────────┐
    │ Continue to   │
    │ next payload  │
    └───────────────┘
```

---

## 6. Key Rotation Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      KEY ROTATION STRATEGY                                  │
└─────────────────────────────────────────────────────────────────────────────┘

SINGLE REQUEST (Normal Mode)
────────────────────────────

Request comes in
      │
      ▼
┌────────────────────────┐
│ KeyPool.get_next()     │
│                        │
│ Strategy: Shuffle      │
│ (Random selection)     │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ Select next key        │
│ from available pool    │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ Execute strike         │
│ with selected key      │
└────────┬───────────────┘
         │
    ┌────┴────┐
    │         │
  Success   429 Error
    │         │
    ▼         ▼
┌───────┐ ┌──────────────┐
│ Log   │ │ Mark key HOT │
│ usage │ │ (60s cooldown)│
└───────┘ └──────┬───────┘
                 │
                 ▼
          ┌──────────────┐
          │ Retry with   │
          │ next key     │
          └──────────────┘


PAYLOAD STRIKER (Aggressive Mode)
─────────────────────────────────

Batch of 10 payloads
         │
         ▼
┌────────────────────────┐
│ Pre-assign keys:       │
│                        │
│ Payload 1 → Key 1      │
│ Payload 2 → Key 2      │
│ Payload 3 → Key 3      │
│ ...                    │
│ Payload 10 → Key 10    │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ Execute in parallel    │
│ (up to thread limit)   │
└────────┬───────────────┘
         │
         ▼
┌────────────────────────┐
│ As each completes:     │
│ • Mark key used        │
│ • Calculate cooldown   │
│ • Select next available│
└────────────────────────┘


KEY HEALTH MONITORING
─────────────────────

┌─────────────────────────────────────────────────────────────┐
│                    KEY POOL HEALTH                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Key 1:  🟢 HEALTHY    (0% error rate)                      │
│  Key 2:  🟢 HEALTHY    (0% error rate)                      │
│  Key 3:  🟡 WARNING    (10% error rate, 2x 429s)           │
│  Key 4:  🟢 HEALTHY    (0% error rate)                      │
│  Key 5:  🔴 EXHAUSTED  (RPD limit reached, cooldown 4h)    │
│                                                             │
│  Pool Status: 4/5 keys available                            │
│  Rotation Speed: Normal                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. Deployment Decision Tree

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT DECISION TREE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

START
  │
  ├──► FIRST TIME SETUP?
  │       │
  │       ├──► YES ──► Go to WORKFLOW 1
  │       │             (Fresh Install)
  │       │
  │       └──► NO ───► CODE UPDATE NEEDED?
  │                     │
  │                     ├──► YES ──► Go to WORKFLOW 2
  │                     │             (Git Pull & Restart)
  │                     │
  │                     └──► NO ───► EMERGENCY?
  │                                   │
  │                                   ├──► YES ──► Go to WORKFLOW 3
  ��                                   │             (Recovery Mode)
  │                                   │
  │                                   └──► NO ───► MONITORING?
  │                                                 │
  │                                                 ├──► YES ──► Check logs
  │                                                 │
  │                                                 └──► NO ───► END
  │
  ▼
WORKFLOW 1: FRESH INSTALL
─────────────────────────
┌─────────────────────────────────────────────────────────────┐
│ 1. Server prep (OS updates, firewall)                       │
│ 2. Install dependencies (Python, Node, Caddy)               │
│ 3. Clone repo                                               │
│ 4. Create .env with API keys                                │
│ 5. Setup Python venv                                        │
│ 6. Build frontend                                           │
│ 7. Create systemd service                                   │
│ 8. Configure Caddy                                          │
│ 9. Setup Syncthing                                          │
│ 10. Verify everything works                                 │
└─────────────────────────────────────────────────────────────┘

WORKFLOW 2: CODE UPDATE
───────────────────────
┌─────────────────────────────────────────────────────────────┐
│ 1. Local: Make changes                                      │
│ 2. Local: Build and test                                    │
│ 3. Local: git add, commit, push                             │
│ 4. VPS: git pull origin main                                │
│ 5. VPS: Rebuild if UI changed (npm run build)               │
│ 6. VPS: sudo systemctl restart peacock-engine               │
│ 7. VPS: Verify restart successful                           │
│ 8. Test in browser                                          │
└─────────────────────────────────────────────────────────────┘

WORKFLOW 3: EMERGENCY RECOVERY
──────────────────────────────
┌─────────────────────────────────────────────────────────────┐
│ 1. SSH to VPS                                               │
│ 2. Check logs: journalctl -u peacock-engine -n 50           │
│ 3. Identify error type                                      │
│ 4. If service stuck: sudo pkill -f uvicorn                  │
│ 5. Restart: sudo systemctl restart peacock-engine           │
│ 6. If DB corrupt: Restore from backup or recreate           │
│ 7. If code broken: git reset --hard origin/main             │
│ 8. Full restart sequence                                    │
│ 9. Verify health endpoint                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Multi-User Scenario (Future)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MULTI-USER ARCHITECTURE (Future)                         │
└─────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────┐
                    │      LOAD BALANCER      │
                    │    (Caddy or HAProxy)   │
                    └───────────┬─────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            │                   │                   │
            ▼                   ▼                   ▼
    ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
    │   VPS #1      │   │   VPS #2      │   │   VPS #3      │
    │  (Primary)    │   │  (Secondary)  │   │  (Worker)     │
    │               │   │               │   │               │
    │ • FastAPI     │   │ • FastAPI     │   │ • FastAPI     │
    │ • UI Static   │   │ • UI Static   │   │ • Striker     │
    │ • Database    │   │ • DB Replica  │   │   only        │
    │ • Key Pool A  │   │ • Key Pool B  │   │ • Key Pool C  │
    └───────────────┘   └───────────────┘   └───────────────┘
            │                   │                   │
            └───────────────────┼───────────────────┘
                                │
                                ▼
                    ┌─────────────────────────┐
                    │    SHARED RESOURCES     │
                    │                         │
                    │ • Redis (Rate limits)   │
                    │ • S3 / NFS (Files)      │
                    │ • Vault (Logs)          │
                    │ • PostgreSQL (Optional) │
                    └─────────────────────────┘

USER A ──► Hits Load Balancer ──► Routed to VPS #1 ──► Uses Key Pool A
USER B ──► Hits Load Balancer ──► Routed to VPS #2 ──► Uses Key Pool B
USER C ──► Hits Load Balancer ──► Routed to VPS #3 ──► Uses Key Pool C

Benefits:
• Horizontal scaling
• Geographic distribution
• Key pool isolation per user group
• High availability (failover)

Current Status: Single VPS (204.168.184.49)
Migration Path: Docker + Kubernetes or Docker Compose Swarm
```

---

*"Visualize the flow, then execute with precision."*
