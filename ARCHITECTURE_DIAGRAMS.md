# 🦚 PEACOCK ENGINE V3 - ARCHITECTURE DIAGRAMS

> Visual reference diagrams for system understanding

---

## 1. Network Topology

```
                              INTERNET
                                 │
                    ┌────────────┴────────────┐
                    │                         │
              ┌─────▼─────┐             ┌────▼────┐
              │   USER    │             │  USER   │
              │  (Local)  │             │ (Mobile)│
              └─────┬─────┘             └────┬────┘
                    │                        │
                    └──────────┬─────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   DNS Resolution    │
                    │ chat.save-aichats.com
                    │ engine.save-aichats.com
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
┌─────────────────────────────────────────────────────────────┐
│              HETZNER VPS (204.168.184.49)                   │
│  Ubuntu 22.04 LTS / 8GB RAM / 4 vCPU / 160GB SSD            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │           CADDY REVERSE PROXY (Port 443)              │   │
│  │  • Automatic HTTPS (Let's Encrypt)                    │   │
│  │  • HTTP/2 & HTTP/3 support                            │   │
│  │  • gzip/zstd compression                              │   │
│  │  • Security headers (HSTS, CSP, etc.)                 │   │
│  └───────────────────────┬───────────────────────────────┘   │
│                          │                                    │
│                          ▼ Port 3099                          │
│  ┌───────────────────────────────────────────────────────┐   │
│  │              PEACOCK ENGINE (FastAPI)                 │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐  │   │
│  │  │  API Layer  │  │ StaticFiles │  │   WebSocket  │  │   │
│  │  │  /v1/*      │  │    /*       │  │   /ws/*      │  │   │
│  │  └─────────────┘  └─────────────┘  └──────────────┘  │   │
│  └───────────────────────┬───────────────────────────────┘   │
│                          │                                    │
│          ┌───────────────┼───────────────┐                    │
│          │               │               │                    │
│          ▼               ▼               ▼                    │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Key Pools │  │   Striker    │  │   Database   │           │
│  │ (Memory)  │  │   Engine     │  │  (SQLite)    │           │
│  │           │  │              │  │              │           │
│  │ • Groq    │  │ • Execute    │  │ • Conversations│         │
│  │ • Google  │  │ • Stream     │  │ • Usage Stats  │         │
│  │ • DeepSeek│  │ • Batch      │  │ • Key Tracking │         │
│  │ • Mistral │  │ • Precision  │  │ • Vault Logs   │         │
│  └───────────┘  └──────────────┘  └──────────────┘           │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │              FILE SYSTEM INTEGRATION                  │   │
│  │  • /root/herbert/liquid-semiotic/english (payloads)   │   │
│  │  • /root/herbert/liquid-semiotic/invariants (outputs) │   │
│  │  • /root/ai-engine/vault/ (forensic logs)             │   │
│  │  • /root/ai-engine/peacock.db (SQLite)                │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
              │
              │ HTTPS API Calls
              ▼
┌─────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                         │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ ┌─────────┐ │
│  │   GOOGLE    │  │    GROQ     │  │ DEEPSEEK │ │ MISTRAL │ │
│  │   Gemini    │  │   (LLMs)    │  │    AI    │ │   AI    │ │
│  │  (3 keys)   │  │  (16 keys)  │  │  (1 key) │ │ (1 key) │ │
│  └─────────────┘  └─────────────┘  └──────────┘ └─────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Request Lifecycle Flowchart

```
┌─────────┐
│  START  │
└────┬────┘
     │
     ▼
┌──────────────────┐
│  DNS Resolution  │
│  chat.save-...   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Caddy (443)    │
│  • TLS Handshake │
│  • Check cache   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐     NO     ┌──────────────┐
│ Is it /v1/* or   │───────────►│ StaticFiles  │
│ /health ?        │            │ Serve index  │
└────────┬─────────┘            └──────────────┘
         │ YES
         ▼
┌──────────────────┐
│   FastAPI Router │
│   Match Route    │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ CORS Middleware  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Throttle Check   │
│ RPM/TPM/RPD OK?  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ KeyPool.get_next │
│ Rotate Keys      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Token Count      │
│ Pre-flight check │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Pydantic AI      │
│ Execute Strike   │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ HighSignalLogger │
│ Log to Vault     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Database       │
│ Record Usage     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ Return Response  │
│ JSON / Stream    │
└────────┬─────────┘
         │
         ▼
┌─────────┐
│   END   │
└─────────┘
```

---

## 3. Key Pool Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    KEY POOL SYSTEM                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │                GROQ KEY POOL                          │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │   │
│  │  │ KEY1 │ │ KEY2 │ │ KEY3 │ │ KEY4 │ │ KEY5 │ ...   │   │
│  │  │(cool)│ │(cool)│ │(hot) │ │(cool)│ │(cool)│       │   │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘       │   │
│  │                                                      │   │
│  │  Rotation Strategy: Shuffle + Cooldown               │   │
│  │  - Mark hot keys after 429 error                     │   │
│  │  - Cooldown period: 60 seconds                       │   │
│  │  - Auto-retry with next key                          │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │               GOOGLE KEY POOL                         │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐              │   │
│  │  │PEACOCK_1 │ │PEACOCK_2 │ │PEACOCK_3 │              │   │
│  │  │ (Tier 3) │ │ (Tier 3) │ │ (Tier 2) │              │   │
│  │  └──────────┘ └──────────┘ └──────────┘              │   │
│  │                                                      │   │
│  │  Rotation: Round-robin per request                   │   │
│  │  Fallback: Tier 3 (highest limits) first             │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │            DEEPSEEK & MISTRAL                         │   │
│  │  ┌──────────┐ ┌──────────┐                           │   │
│  │  │DeepSeek  │ │ Mistral  │                           │   │
│  │  │ (1 key)  │ │ (1 key)  │                           │   │
│  │  └──────────┘ └──────────┘                           │   │
│  │                                                      │   │
│  │  Single key - no rotation needed                     │   │
│  │  Automatic retry on failure                          │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │              COOLDOWN MECHANISM                       │   │
│  │                                                      │   │
│  │  ┌────────────┐     ┌────────────┐                  │   │
│  │  │ 429 Error  │────►│ Mark HOT   │                  │   │
│  │  │ Received   │     │ 60s timer  │                  │   │
│  │  └────────────┘     └─────┬──────┘                  │   │
│  │                           │                        │   │
│  │                           ▼                        │   │
│  │                    ┌────────────┐                  │   │
│  │                    │ Skip in    │                  │   │
│  │                    │ Rotation   │                  │   │
│  │                    └─────┬──────┘                  │   │
│  │                          │                        │   │
│  │                          ▼ (after 60s)            │   │
│  │                    ┌────────────┐                  │   │
│  │                    │ Mark COOL  │                  │   │
│  │                    │ Re-enable  │                  │   │
│  │                    └────────────┘                  │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Token Counter Data Flow

```
                    ┌─────────────────┐
                    │  Input Request  │
                    │  model + prompt │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │  PeacockTokenCounter         │
              │  ┌────────────────────────┐  │
              │  │ 1. Lookup ModelConfig  │  │
              │  │    in MODEL_REGISTRY   │  │
              │  └────────────────────────┘  │
              │               │              │
              │               ▼              │
              │  ┌────────────────────────┐  │
              │  │ 2. Identify Gateway    │  │
              │  │    (google/groq/etc)   │  │
              │  └────────────────────────┘  │
              └───────────────┬──────────────┘
                              │
              ┌───────────────┴───────────────┐
              │                               │
    ┌─────────▼──────────┐        ┌──────────▼──────────┐
    │   GOOGLE/GEMINI    │        │      GROQ           │
    │                    │        │                     │
    │ ┌────────────────┐ │        │ ┌─────────────────┐ │
    │ │ Option 1: API  │ │        │ │ tiktoken        │ │
    │ │ count_tokens() │ │        │ │                 │ │
    │ │ (Most accurate)│ │        │ │ • cl100k_base   │ │
    │ └────────────────┘ │        │ │ • o200k_base    │ │
    │                    │        │ │ • p50k_base     │ │
    │ ┌────────────────┐ │        │ └─────────────────┘ │
    │ │ Option 2:      │ │        │                     │
    │ │ Estimate       │ │        │ ┌─────────────────┐ │
    │ │ • Text: char/4 │ │        │ │ Fallback:       │ │
    │ │ • Images: 258  │ │        │ │ len(text) // 4  │ │
    │ │ • Video: 263/s │ │        │ └─────────────────┘ │
    │ │ • Audio: 32/s  │ │        │                     │
    │ └────────────────┘ │        └─────────────────────┘
    │                    │
    └─────────┬──────────┘
              │
              ▼
    ┌─────────────────┐
    │  Token Count    │
    │  (Integer)      │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │ Cost Calculator │
    │                 │
    │ input_cost =    │
    │   (tokens/1M) * │
    │   input_price   │
    │                 │
    │ output_cost =   │
    │   (tokens/1M) * │
    │   output_price  │
    │                 │
    │ total = input + │
    │   output        │
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  Return:        │
    │  {              │
    │    tokens: 150, │
    │    cost: 0.002  │
    │  }              │
    └─────────────────┘
```

---

## 5. Payload Striker UI Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           PAYLOAD STRIKER UI                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  TOP NAVIGATION BAR                                                  │   │
│  │  [Dashboard] [Payload Striker] [Model Garden] [Keys] [Settings]     │   │
│  │                                                                      │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────┐  │   │
│  │  │ MONOLITHIC  │  │  CAMPAIGN   │  │  Mode Toggle                │  │   │
│  │  │    MODE     │  │    MODE     │  │  [Ultra ▼] [Batch ▼]        │  │   │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐   │
│  │    ZONE 1: PROMPTS   │  │   ZONE 2: PAYLOADS   │  │  ZONE 3: COMMAND │   │
│  │                      │  │                      │  │                  │   │
│  │  📋 AVAILABLE        │  │  📦 AMMO PILE        │  │  ⚙️ SETTINGS     │   │
│  │  ┌────────────────┐  │  │  ┌────────────────┐  │  │                  │   │
│  │  │ • prompt_1.md  │  │  │  │ • file1.py     │  │  │  Temperature   │   │
│  │  │ • prompt_2.md  │  │  │  │ • file2.py     │  │  │  [====●====]   │   │
│  │  │ • prompt_3.md  │  │  │  │ • file3.py     │  │  │                │   │
│  │  │ ...            │  │  │  │ ...            │  │  │  Top-P         │   │
│  │  └────────────────┘  │  │  └────────────────┘  │  │  [===●=====]   │   │
│  │                      │  │                      │  │                │   │
│  │  [VIEW] [SELECT]     │  │  [VIEW] [LOAD ▶]     │  │  Threads: [4]  │   │
│  │                      │  │                      │  │                │   │
│  │  ┌────────────────┐  │  │  ┌────────────────┐  │  │  Max Tokens    │   │
│  │  │ SELECTED:      │  │  │  │ LOADED:        │  │  │  [2000]        │   │
│  │  │ prompt_1.md    │  │  │  │ file1.py ✓     │  │  │                │   │
│  │  │ [EDIT] [REMOVE]│  │  │  │ file2.py ✓     │  │  │  □ Auto-retry  │   │
│  │  └────────────────┘  │  │  │ file3.py ✓     │  │  │  □ Dry-run     │   │
│  │                      │  │  │ [CLEAR ALL]    │  │  │                │   │
│  │                      │  │  └────────────────┘  │  └──────────────────┘   │
│  │                      │  │                      │                         │
│  │                      │  │  ┌────────────────┐  │  ┌──────────────────┐   │
│  │                      │  │  │ PAYLOAD EDITOR │  │  │  🎯 SEQUENCE     │   │
│  │                      │  │  │                │  │  │     MANIFEST     │   │
│  │                      │  │  │ ┌────────────┐ │  │  │                  │   │
│  │                      │  │  │ │ [file1]    │ │  │  │  Slot 1: [●●●]   │   │
│  │                      │  │  │ │ [file2]    │ │  │  │  Slot 2: [●●●]   │   │
│  │                      │  │  │ │ [file3]    │ │  │  │  Slot 3: [○○○]   │   │
│  │                      │  │  │ └────────────┘ │  │  │  Slot 4: [○○○]   │   │
│  │                      │  │  │                │  │  │  ...             │   │
│  │                      │  │  │ Custom Prompt: │  │  │                  │   │
│  │                      │  │  │ [per-payload   │  │  │  Model: [▼ Gem ] │   │
│  │                      │  │  │  override]     │  │  │  Key:   [▼ Auto] │   │
│  │                      │  │  └────────────────┘  │  │  Delay: [1000ms] │   │
│  │                      │  │                      │  │                  │   │
│  └──────────────────────┘  └──────────────────────┘  │  [  ▶ LAUNCH   ]  │   │
│                                                      │                  │   │
│                                                      │  ┌──────────────┐ │   │
│                                                      │  │  📊 GAUGES   │ │   │
│                                                      │  │              │ │   │
│                                                      │  │ TPS: 45.2    │ │   │
│                                                      │  │ RPM: 28/60   │ │   │
│                                                      │  │ Cost: $0.023 │ │   │
│                                                      │  │ Queue: 3/10  │ │   │
│                                                      │  └──────────────┘ │   │
│                                                      └──────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  ZONE 4: TELEMETRY & LOGS                                            │   │
│  │                                                                      │   │
│  │  ┌────────────────────────────┐  ┌────────────────────────────────┐  │   │
│  │  │ REAL-TIME LOG STREAM       │  │ STRIKE STATUS                  │  │   │
│  │  │                            │  │                                │  │   │
│  │  │ [14:32:01] Strike #1 INIT  │  │ 🟢 file1.py - COMPLETE (2.3s)  │  │   │
│  │  │ [14:32:03] Strike #1 OK    │  │ 🟡 file2.py - RUNNING          │  │   │
│  │  │ [14:32:04] Strike #2 INIT  │  │ ⚪ file3.py - QUEUED           │  │   │
│  │  │ [14:32:07] Strike #2 OK    │  │ 🔴 file4.py - FAILED (retry)   │  │   │
│  │  │ ...                        │  │                                │  │   │
│  │  └────────────────────────────┘  └────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Syncthing Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        SYNCTHING MESH TOPOLOGY                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                              ┌─────────────┐                                │
│                              │     VPS     │                                │
│                              │  (Introducer│                                │
│                              │   / Hub)    │                                │
│                              │  204.168.   │                                │
│                              │   184.49    │                                │
│                              └──────┬──────┘                                │
│                                     │                                       │
│                    ┌────────────────┼────────────────┐                      │
│                    │                │                │                      │
│                    │                │                │                      │
│           ┌────────▼────────┐      │      ┌─────────▼─────────┐            │
│           │   LOCAL PC      │      │      │    LAPTOP         │            │
│           │  (Development)  │◄─────┴─────►│   (Work/Travel)   │            │
│           └─────────────────┘             └───────────────────┘            │
│                                                                             │
│  SYNC FOLDERS (Bidirectional):                                              │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  liquid-semiotic/english                                             │   │
│  │  ├── VPS: /root/herbert/liquid-semiotic/english                      │   │
│  │  └── LOCAL: ~/herbert/liquid-semiotic/english                        │   │
│  │  [ Sync Mode: Send & Receive ]                                       │   │
│  │                                                                      │   │
│  │  liquid-semiotic/invariants                                          │   │
│  │  ├── VPS: /root/herbert/liquid-semiotic/invariants                   │   │
│  │  └── LOCAL: ~/herbert/liquid-semiotic/invariants                     │   │
│  │  [ Sync Mode: Send & Receive ]                                       │   │
│  │                                                                      │   │
│  │  liquid-semiotic/semiotic-mold                                       │   │
│  │  ├── VPS: /root/herbert/liquid-semiotic/semiotic-mold                │   │
│  │  └── LOCAL: ~/herbert/liquid-semiotic/semiotic-mold                  │   │
│  │  [ Sync Mode: Send & Receive ]                                       │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ACCESS POINTS:                                                             │
│  • VPS Web UI: http://204.168.184.49:8384                                   │
│  • Local Web UI: http://localhost:8384                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Database Schema

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PEACOCK ENGINE DATABASE                                │
│                      SQLite: peacock.db                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  TABLE: conversations                                                 │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │  id (PK)       │ TEXT    │ UUID short form                            │  │
│  │  title         │ TEXT    │ Conversation title                         │  │
│  │  model_id      │ TEXT    │ e.g., "gemini-2.5-pro"                     │  │
│  │  key_account   │ TEXT    │ Key used (e.g., "PEACOCK_1")               │  │
│  │  created_at    │ TIMESTAMP                                     │  │
│  │  updated_at    │ TIMESTAMP                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    │ 1:N                                    │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  TABLE: messages                                                      │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │  id (PK)       │ INTEGER │ Auto-increment                             │  │
│  │  conv_id (FK)  │ TEXT    │ → conversations.id                         │  │
│  │  role          │ TEXT    │ "user" | "assistant" | "system"            │  │
│  │  content       │ TEXT    │ Message content                            │  │
│  │  tokens_used   │ INTEGER │ Total tokens                               │  │
│  │  prompt_tokens │ INTEGER │ Input tokens                               │  │
│  │  completion_tokens │ INTEGER │ Output tokens                          │  │
│  │  model_id      │ TEXT    │ Model used                                 │  │
│  │  key_account   │ TEXT    │ Key used                                   │  │
│  │  created_at    │ TIMESTAMP                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    │ 1:N (indirect via tag)                 │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  TABLE: key_usage                                                     │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │  id (PK)       │ INTEGER │ Auto-increment                             │  │
│  │  gateway       │ TEXT    │ "google", "groq", etc.                     │  │
│  │  key_account   │ TEXT    │ Key identifier                             │  │
│  │  model_id      │ TEXT    │ Model used                                 │  │
│  │  tokens_used   │ INTEGER │ Token count                                │  │
│  │  cost          │ REAL    │ Calculated cost (USD)                      │  │
│  │  strike_tag    │ TEXT    │ Link to vault log (PEA-XXXX)               │  │
│  │  timestamp     │ TIMESTAMP                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  TABLE: batches  (Payload Striker)                                    │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │  id (PK)       │ TEXT    │ Batch UUID                                 │  │
│  │  name          │ TEXT    │ Batch name                                 │  │
│  │  app_identity  │ TEXT    │ Namespace (e.g., "liquid-semiotic")        │  │
│  │  status        │ TEXT    │ "pending" | "running" | "completed" | "failed"│ │
│  │  total_files   │ INTEGER │ Total files in batch                       │  │
│  │  completed_files│ INTEGER │ Files processed                            │  │
│  │  total_tokens  │ INTEGER │ Cumulative tokens                          │  │
│  │  cost          │ REAL    │ Total cost                                 │  │
│  │  created_at    │ TIMESTAMP                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                    │                                        │
│                                    │ 1:N                                    │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │  TABLE: batch_items                                                   │  │
│  ├───────────────────────────────────────────────────────────────────────┤  │
│  │  id (PK)       │ INTEGER │ Auto-increment                             │  │
│  │  batch_id (FK) │ TEXT    │ → batches.id                               │  │
│  │  file_path     │ TEXT    │ Source file path                           │  │
│  │  status        │ TEXT    │ "queued" | "processing" | "completed" | "failed"│ │
│  │  result        │ TEXT    │ LLM output                                 │  │
│  │  tokens        │ INTEGER │ Tokens used                                │  │
│  │  cost          │ REAL    │ Cost for this item                         │  │
│  │  error         │ TEXT    │ Error message if failed                    │  │
│  │  completed_at  │ TIMESTAMP                                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Deployment Decision Tree

```
START
  │
  ├──► NEW VPS SETUP?
  │      │
  │      ├── YES ──► Follow WORKFLOW 1 (Fresh Install)
  │      │            • Server prep
  │      │            • Repo setup
  │      │            • Python env
  │      │            • Frontend build
  │      │            • Systemd service
  │      │            • Caddy proxy
  │      │            • Syncthing
  │      │            └──► DONE
  │      │
  │      └── NO ─────► CODE UPDATE?
  │                     │
  │                     ├── YES ──► Follow WORKFLOW 2 (Update)
  │                     │            • Local changes
  │                     │            • Git push
  │                     │            • VPS pull
  │                     │            • Rebuild UI (if needed)
  │                     │            • Restart service
  │                     │            └──► DONE
  │                     │
  │                     └── NO ───► EMERGENCY?
  │                                  │
  │                                  ├── YES ──► Recovery Mode
  │                                  │            • Check logs
  │                                  │            • Stop service
  │                                  │            • Restore from backup
  │                                  │            • Restart
  │                                  │            └──► DONE
  │                                  │
  │                                  └── NO ───► IDLE
  │                                               └──► END
```

---

*End of Architecture Diagrams*
