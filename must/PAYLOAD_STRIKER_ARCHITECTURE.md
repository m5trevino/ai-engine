# 🦚 PAYLOAD STRIKER: COMPLETE ARCHITECTURE GUIDE

> **Pilot's Dashboard & Strike Manifest System**
> 
> This document details the complete architecture for the Sequence Striker system with Context Vault, dual-mode threading, and Hellcat Governor.

---

## 1. SYSTEM OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PAYLOAD STRIKER - SYSTEM MAP                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         UI LAYER (React/Vite)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────────────┐    │
│  │  LEFT PANEL     │    │  CENTER PANEL   │    │  RIGHT PANEL         │    │
│  │                 │    │                 │    │                      │    │
│  │ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌────────────────┐   │    │
│  │ │ PROMPT      │ │    │ │ PAYLOAD     │ │    │ │ STRIKE MANIFEST│   │    │
│  │ │ MANAGER     │ │    │ │ SELECTOR    │ │    │ │ (10 Slots)     │   │    │
│  │ │             │ │    │ │             │ │    │ │                │   │    │
│  │ │ • List      │ │    │ │ • Ammo Pile │ │    │ │ Slot 1: [Key▼] │   │    │
│  │ │ • View Full │ │◄───┼─┤ • Loaded    │ │◄───┼─┤         [Mod▼] │   │    │
│  │ │ • Edit      │ │    │ │ • Transfer  │ │    │ │         [Dly]  │   │    │
│  │ │ • Save New  │ │    │ │ • Preview   │ │    │ │ Slot 2: [...]  │   │    │
│  │ └─────────────┘ │    │ └─────────────┘ │    │ │ ...            │   │    │
│  │                 │    │                 │    │ │ Slot 10: [...] │   │    │
│  │ Collapsible:    │    │                 │    │ │                │   │    │
│  │ [Prompt Editor] │    │                 │    │ │ [▶ LAUNCH]     │   │    │
│  │                 │    │                 │    │ │ [🔁 REPEAT]    │   │    │
│  └─────────────────┘    └─────────────────┘    │ │ [🔄 ROTATE KEYS│   │    │
│                                                │ └────────────────┘   │    │
│                                                │                      │    │
│                                                │ ┌────────────────┐   │    │
│                                                │ │ GAUGES PANEL   │   │    │
│                                                │ │ • TPS: 45.2    │   │    │
│                                                │ │ • RPM: 28/60   │   │    │
│                                                │ │ • Latency: 234ms│   │    │
│                                                │ │ • Tokens: 1.2K │   │    │
│                                                │ │ • Cost: $0.023 │   │    │
│                                                │ └────────────────┘   │    │
│                                                └──────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTP/WebSocket
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      BACKEND LAYER (FastAPI)                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  API ENDPOINTS                                                       │   │
│  │  ├── GET  /v1/fs/payloads         → List payload directory          │   │
│  │  ├── GET  /v1/fs/payloads/{path}  → Read file content               │   │
│  │  ├── GET  /v1/prompts             → List available prompts          │   │
│  │  ├── POST /v1/prompts             → Save new/edit prompt            │   │
│  │  ├── GET  /v1/keys/available      → List healthy keys               │   │
│  │  └── POST /v1/striker/sequence    → Execute strike sequence         │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  STRIKE ORCHESTRATOR                                               │   │
│  │                                                                    │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │   │
│  │  │ ULTRA MODE   │    │ BATCH MODE   │    │ KEY ROTATOR  │         │   │
│  │  │ (Continuous) │    │ (Wave)       │    │              │         │   │
│  │  │              │    │              │    │ • Pool mgmt   │         │   │
│  │  │ Worker Pool  │    │ Synchronous  │    │ • Health check│         │   │
│  │  │ Always full  │    │ Batch wait   │    │ • Auto-rotate │         │   │
│  │  └──────────────┘    └──────────────┘    └──────────────┘         │   │
│  │                                                                    │   │
│  │  ┌─────────────────────────────────────────────────────────────┐  │   │
│  │  │ HELLCAT GOVERNOR                                            │  │   │
│  │  │ • RPM Limiter (per key)                                     │  │   │
│  │  │ • TPM Limiter (per key)                                     │  │   │
│  │  │ • RPD Limiter (per key)                                     │  │   │
│  │  │ • Global circuit breaker                                    │  │   │
│  │  └─────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. THE TWO THREADING MODES EXPLAINED

### Mode A: Ultra Mode (Continuous Worker Pool)

```
CONCEPT: Keep N threads constantly busy. As soon as one finishes, start the next.

Example: 6 payloads, 2 threads configured

Timeline:
┌─────────────────────────────────────────────────────────────────┐
│ Time │ Thread 1      │ Thread 2      │ Queue                    │
├──────┼───────────────┼───────────────┼──────────────────────────┤
│ 0s   │ Payload 1     │ Payload 2     │ [3, 4, 5, 6]             │
│      │ (starts)      │ (starts)      │                          │
│      │               │               │                          │
│ 1.2s │ Payload 1     │ Payload 2     │ [3, 4, 5, 6]             │
│      │ (DONE ✓)      │ (running)     │                          │
│      │               │               │                          │
│ 1.2s │ Payload 3     │ Payload 2     │ [4, 5, 6]                │
│      │ (starts)      │ (running)     │ (3 pulled from queue)    │
│      │               │               │                          │
│ 2.5s │ Payload 3     │ Payload 2     │ [4, 5, 6]                │
│      │ (running)     │ (DONE ✓)      │                          │
│      │               │               │                          │
│ 2.5s │ Payload 3     │ Payload 4     │ [5, 6]                   │
│      │ (running)     │ (starts)      │ (4 pulled from queue)    │
│      │               │               │                          │
│ ...  │ ... continues until queue empty ...                      │
└─────────────────────────────────────────────────────────────────┘

Characteristics:
• Maximum throughput
• Uneven completion times (depends on payload complexity)
• Best for: Large batches, variable processing times
• Risk: Can hit rate limits if not governed
```

### Mode B: Regular Mode (Synchronous Batch)

```
CONCEPT: Fire N threads at once, wait for ALL to complete, then fire next N.

Example: 6 payloads, 2 threads configured

Timeline:
┌─────────────────────────────────────────────────────────────────┐
│ Time │ Thread 1      │ Thread 2      │ Queue                    │
├──────┼───────────────┼───────────────┼──────────────────────────┤
│ 0s   │ Payload 1     │ Payload 2     │ [3, 4, 5, 6]             │
│      │ (starts)      │ (starts)      │                          │
│      │               │               │                          │
│ 1.2s │ Payload 1     │ Payload 2     │ [3, 4, 5, 6]             │
│      │ (DONE ✓)      │ (running)     │ (waiting...)             │
│      │               │               │                          │
│ 2.5s │ Payload 1     │ Payload 2     │ [3, 4, 5, 6]             │
│      │ (DONE ✓)      │ (DONE ✓)      │ (BOTH done, next batch)  │
│      │               │               │                          │
│ 2.5s │ Payload 3     │ Payload 4     │ [5, 6]                   │
│      │ (starts)      │ (starts)      │ (next batch pulled)      │
│      │               │               │                          │
│ ...  │ ... continues until queue empty ...                      │
└─────────────────────────────────────────────────────────────────┘

Characteristics:
• Predictable batch completion
• Easier to track progress (X of Y batches done)
• Best for: Controlled execution, testing, debugging
• Risk: Thread idle time waiting for slowest in batch
```

---

## 3. THE 10-SLOT STRIKE MANIFEST

### Slot Configuration Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    STRIKE MANIFEST (10 SLOTS)                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ GLOBAL SETTINGS (Apply to all slots unless overridden)              │   │
│  │                                                                     │   │
│  │ • Default Model: [gemini-2.5-pro ▼]                                │   │
│  │ • Default Key:   [AUTO-ROTATE   ▼]  ← or specific key              │   │
│  │ • Base Delay:    [1000 ms]     ← Between strikes                   │   │
│  │ • Threading:     [Ultra Mode ▼]  ← Ultra or Batch                  │   │
│  │ • Thread Count:  [4]          ← How many concurrent                │   │
│  │                                                                     │   │
│  │ ⚠️ WARNING: High thread count may trigger rate limits              │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ SLOT-SPECIFIC CONFIGURATIONS (Can override globals)                 │   │
│  │                                                                     │   │
│  │ ┌──────┬──────────────┬─────────────┬─────────┬──────────────────┐ │   │
│  │ │ Slot │ Model        │ Key         │ Delay   │ Payload          │ │   │
│  │ ├──────┼──────────────┼─────────────┼─────────┼──────────────────┤ │   │
│  │ │  1   │ (inherit)    │ Key-A       │ +500ms  │ file1.py         │ │   │
│  │ │  2   │ (inherit)    │ Key-B       │ (base)  │ file2.py         │ │   │
│  │ │  3   │ llama-3.3-70b│ (inherit)   │ +200ms  │ file3.py         │ │   │
│  │ │  4   │ (inherit)    │ AUTO        │ (base)  │ file4.py         │ │   │
│  │ │ ...  │ ...          │ ...         │ ...     │ ...              │ │   │
│  │ │ 10   │ (inherit)    │ Key-C       │ +1000ms │ file10.py        │ │   │
│  │ └──────┴──────────────┴─────────────┴─────────┴──────────────────┘ │   │
│  │                                                                     │   │
│  │ Each slot can:                                                      │   │
│  │ • Use global model OR specify different model                       │   │
│  │ • Use AUTO key rotation OR specific key                             │   │
│  │ • Add extra delay to base delay (for staggering)                    │   │
│  │ • Target specific payload file                                      │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │ POST-SEQUENCE OPTIONS                                               │   │
│  │                                                                     │   │
│  │ [🔁 REPEAT SEQUENCE]  ← Run same 10 slots again                     │   │
│  │                                                                     │   │
│  │ [🔄 ROTATE KEYS AFTER 10]                                           │   │
│  │     When checked: After slot 10 completes, rotate to next key      │   │
│  │     in pool before any repeats                                      │   │
│  │                                                                     │   │
│  │ Example rotation:                                                   │   │
│  │     • Run 1: Slots 1-10 use Keys A, B, C, D...                      │   │
│  │     • Rotate: Advance key pool pointer                              │   │
│  │     • Run 2: Slots 1-10 use Keys E, F, G, H...                      │   │
│  │                                                                     │   │
│  │ [📊 AUTO-REPEAT UNTIL DONE]                                         │   │
│  │     If >10 payloads loaded, automatically queue next 10             │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. CONTEXT VAULT: PAYLOAD & PROMPT SYSTEM

### The File Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FILE FLOW ARCHITECTURE                              │
└─────────────────────────────────────────────────────────────────────────────┘

SYNCTHING SYNCED DIRECTORY
(/root/herbert/liquid-semiotic/)
            │
            ▼
┌─────────────────────────────────┐
│      SEMIOTIC-MOLD/             │  ← PROMPTS DIRECTORY
│  ┌─────────────────────────┐    │
│  │ analyze_code.md         │    │
│  │ document_api.md         │    │
│  │ refactor_legacy.md      │    │
│  │ security_audit.md       │    │
│  │ custom_template.md      │    │
│  └─────────────────────────┘    │
└────────────────┬────────────────┘
                 │
                 │ UI: List available prompts
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PROMPT SELECTOR UI                          │
│  ┌─────────────────────────┐  ┌──────────────────────────────┐ │
│  │ Available Prompts       │  │ Selected Prompt Preview      │ │
│  │                         │  │                              │ │
│  │ ○ analyze_code.md       │  │ ┌──────────────────────────┐ │ │
│  │ ● document_api.md  ◄────┼──┤ │ You are a technical...   │ │ │
│  │ ○ refactor_legacy.md    │  │ │ writer. Generate API...  │ │ │
│  │ ○ security_audit.md     │  │ │ documentation for the... │ │ │
│  │ ○ custom_template.md    │  │ │ following code:          │ │ │
│  │                         │  │ │                          │ │ │
│  │ [✏️ Edit] [➕ New]      │  │ │ {CODE}                   │ │ │
│  │                         │  │ │                          │ │ │
│  └─────────────────────────┘  │ │ Parameters:              │ │ │
│                               │ │ • Format: Markdown       │ │ │
│                               │ │ • Style: Technical       │ │ │
│                               │ └──────────────────────────┘ │ │
│                               └──────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                 │
                 │ Collapsible: [📝 EDIT PROMPT]
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PROMPT EDITOR (Collapsible)                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Name: [document_api.md                    ]              │  │
│  │                                                           │  │
│  │  Content:                                                 │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │ You are a technical writer...                      │  │  │
│  │  │                                                    │  │  │
│  │  │ Generate API documentation for:                    │  │  │
│  │  │                                                    │  │  │
│  │  │ {{CODE}}                                           │  │  │
│  │  │                                                    │  │  │
│  │  │ Requirements:                                      │  │  │
│  │  │ - Include parameter descriptions                   │  │  │
│  │  │ - Document return values                           │  │  │
│  │  │ - Provide usage examples                           │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  │                                                           │  │
│  │  [💾 SAVE] [💾 SAVE AS NEW] [🗑️ DELETE] [❌ CANCEL]       │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘


SYNCTHING SYNCED DIRECTORY (continued)
            │
            ▼
┌─────────────────────────────────┐
│         ENGLISH/                │  ← PAYLOADS DIRECTORY
│  ┌─────────────────────────┐    │
│  │ project-a/              │    │
│  │   ├── auth.py           │    │
│  │   ├── database.py       │    │
│  │   └── routes.py         │    │
│  │                         │    │
│  │ project-b/              │    │
│  │   ├── models.py         │    │
│  │   └── utils.py          │    │
│  │                         │    │
│  │ legacy-code/            │    │
│  │   ├── old-system.py     │    │
│  │   └── migrations/       │    │
│  │       ├── 001.sql       │    │
│  │       └── 002.sql       │    │
│  └─────────────────────────┘    │
└────────────────┬────────────────┘
                 │
                 │ UI: Browse & select
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PAYLOAD SELECTOR UI                          │
│                                                                  │
│  ┌──────────────────────────────┐  ┌──────────────────────────┐ │
│  │  AMMO PILE (Available)       │  │  LOADED (Selected)       │ │
│  │                              │  │                          │ │
│  │ 📁 project-a/                │  │ ┌──────────────────────┐ │ │
│  │    📄 auth.py                │  │ │ project-a/auth.py    │ │ │
│  │    📄 database.py            │  │ │ • 234 lines          │ │ │
│  │    📄 routes.py              │  │ │ • Python             │ │ │
│  │ 📁 project-b/                │  │ │ [👁️] [🗑️]           │ │ │
│  │    📄 models.py              │  │ └──────────────────────┘ │ │
│  │    📄 utils.py               │  │                          │ │
│  │ 📁 legacy-code/              │  │ ┌──────────────────────┐ │ │
│  │    📄 old-system.py          │  │ │ project-b/models.py  │ │ │
│  │    📁 migrations/            │  │ │ • 156 lines          │ │ │
│  │       📄 001.sql             │  │ │ • Python             │ │ │
│  │       📄 002.sql             │  │ │ [👁️] [🗑️]           │ │ │
│  │                              │  │ └──────────────────────┘ │ │
│  │ [🔍 Filter...]               │  │                          │ │
│  │                              │  │ ┌──────────────────────┐ │ │
│  │ [☑️ Select All] [📂 Expand]  │  │ │ legacy-code/old-...  │ │ │
│  │                              │  │ │ • 1,204 lines        │ │ │
│  │                              │  │ │ [👁️] [🗑️]           │ │ │
│  └──────────────┬───────────────┘  │ └──────────────────────┘ │ │
│                 │                   │                          │ │
│                 │                   │ [🗑️ Clear All]          │ │
│                 │                   │                          │ │
│                 │                   │ Loaded: 3 files          │ │
│                 │                   │ Est. tokens: ~4,200      │ │
│                 └──────────────────►│                          │ │
│                      [MOVE ▶]       └──────────────────────────┘ │
│                                                                  │
│  Transfer Options:                                               │
│  ○ Move (remove from ammo)  ● Copy (keep in both)               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. THE PILOT'S GAUGES: REV LIMITER & GOVERNOR

### Gauge Panel Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PILOT'S GAUGE PANEL                                       │
│                    (Real-time Telemetry)                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ HELLCAT PROTOCOL - PERFORMANCE MODE                                   │ │
│  │                                                                       │ │
│  │  [STEALTH ▼]  [BALANCED ▼]  [APEX ▼]  ◄── Current: APEX              │ │
│  │   (3.0x)       (1.15x)       (1.02x)                                  │ │
│  │                                                                       │ │
│  │ Mode determines RPM/TPM multipliers for rate limiting                 │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌────────────────────────┐  ┌────────────────────────┐  ┌───────────────┐ │
│  │  🔥 TPS GAUGE          │  │  ⏱️ RPM GAUGE          │  │  💰 COST      │ │
│  │  (Tokens Per Sec)      │  │  (Requests Per Min)    │  │               │ │
│  │                        │  │                        │  │  Session:     │ │
│  │     ┌──────────┐       │  │     ┌──────────┐       │  │  $0.047       │ │
│  │    /   45.2    \      │  │    /    28/60   \      │  │               │ │
│  │   /              \     │  │   /    ████░░░░  \     │  │  Hourly est:  │ │
│  │  │    ████████    │    │  │  │    SAFE       │    │  │  $1.24        │ │
│  │  │   ██████████   │    │  │  │               │    │  │               │ │
│  │   \   ████████   /     │  │   \             /     │  │  Daily est:   │ │
│  │    \  ████████  /      │  │    \           /      │  │  $29.76       │ │
│  │     └──────────┘       │  │     └──────────┘       │  │               │ │
│  │        HIGH            │  │       46% of limit     │  └───────────────┘ │
│  │                        │  │                        │                   │
│  └────────────────────────┘  └────────────────────────┘                   │
│                                                                             │
│  ┌────────────────────────┐  ┌────────────────────────┐  ┌───────────────┐ │
│  │  ⏲️ LATENCY GAUGE      │  │  📊 QUEUE STATUS       │  │  🔋 KEY POOL  │ │
│  │                        │  │                        │  │               │ │
│  │  Current: 234ms        │  │  Active: 3             │  │  🟢 14/16     │ │
│  │  Avg: 189ms            │  │  Queued: 7             │  │  🟡 2 cooling │ │
│  │  P95: 456ms            │  │  Completed: 23         │  │  🔴 0 exhausted│ │
│  │                        │  │                        │  │               │ │
│  │  [████████████████░░]  │  │  Progress: [████░░░░░░]│  │  Next rotate: │ │
│  │       GOOD             │  │       70%              │  │  Slot 7       │ │
│  │                        │  │                        │  │               │ │
│  └────────────────────────┘  └────────────────────────┘  └───────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ ⚠️ ALERTS & WARNINGS                                                  │ │
│  │                                                                       │ │
│  │ 🟡 Key G_OMSX cooling down (429 received 23s ago)                    │ │
│  │ 🔴 Approaching daily limit on PEACOCK_3 (89% of RPD)                 │ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │ 🎛️ MASTER ARM SWITCH                                                  │ │
│  │                                                                       │ │
│  │      [🔴 ARMED]  ←── Toggle to enable strike launch                  │ │
│  │                                                                       │ │
│  │ When DISARMED: All strikes blocked, queue only                        │ │
│  │ When ARMED: Full execution authorized                                 │ │
│  │                                                                       │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Hellcat Governor Logic

```python
# Conceptual implementation of the governor

class HellcatGovernor:
    """
    Rate limiting governor with three modes:
    - STEALTH: 3.0x multiplier (very conservative)
    - BALANCED: 1.15x multiplier (default)
    - APEX: 1.02x multiplier (aggressive, max throughput)
    """
    
    MODES = {
        "stealth": {"multiplier": 3.0, "color": "🟢"},
        "balanced": {"multiplier": 1.15, "color": "🔵"},
        "apex": {"multiplier": 1.02, "color": "🔴"}
    }
    
    def __init__(self, mode="balanced"):
        self.mode = mode
        self.multiplier = self.MODES[mode]["multiplier"]
        
    def check_limits(self, key, gateway):
        """
        Check if strike should proceed based on:
        - RPM (Requests Per Minute)
        - TPM (Tokens Per Minute)
        - RPD (Requests Per Day)
        """
        limits = get_key_limits(key, gateway)
        current = get_current_usage(key, gateway)
        
        # Apply mode multiplier
        rpm_limit = limits.rpm / self.multiplier
        tpm_limit = limits.tpm / self.multiplier
        
        if current.rpm >= rpm_limit:
            return False, f"RPM limit reached: {current.rpm}/{rpm_limit}"
            
        if current.tpm >= tpm_limit:
            return False, f"TPM limit reached: {current.tpm}/{tpm_limit}"
            
        return True, "Clear for strike"
    
    def calculate_delay(self, base_delay):
        """
        Adjust delay based on mode
        """
        if self.mode == "apex":
            return base_delay * 0.5  # 50% faster
        elif self.mode == "stealth":
            return base_delay * 2.0  # 2x slower
        return base_delay
```

---

## 6. DATA STRUCTURES

### Strike Sequence Request (Backend API)

```typescript
// POST /v1/striker/sequence
interface StrikeSequenceRequest {
  // Global settings
  global: {
    default_model: string;           // e.g., "gemini-2.5-pro"
    default_key_strategy: "auto" | "rotate" | string;  // "auto" or specific key label
    base_delay_ms: number;           // Base delay between strikes
    threading_mode: "ultra" | "batch";
    thread_count: number;            // Max concurrent threads
    hellcat_mode: "stealth" | "balanced" | "apex";
  };
  
  // Prompt configuration
  prompt: {
    id: string;                      // Prompt file ID
    content: string;                 // Full prompt text
    variables: Record<string, string>; // {{CODE}} → actual content
  };
  
  // The 10 strike slots
  slots: StrikeSlot[];
  
  // Post-sequence behavior
  post_sequence: {
    repeat: boolean;                 // 🔁 Repeat same sequence
    rotate_keys_after_10: boolean;   // 🔄 Advance key pool after slot 10
    auto_repeat_until_done: boolean; // 📊 Auto-queue next 10 if more payloads
  };
  
  // Payload files to process
  payloads: {
    source_directory: string;        // /root/herbert/liquid-semiotic/english
    files: string[];                 // Selected file paths
  };
}

interface StrikeSlot {
  slot_number: number;               // 1-10
  enabled: boolean;                  // Skip if disabled
  
  // Overrides (null = use global)
  model_override: string | null;
  key_override: string | null;       // Specific key or null for auto
  additional_delay_ms: number;       // Added to base_delay
  
  // Target payload (if auto_repeat, this cycles through payload list)
  target_payload_index: number;
  
  // Status (populated during execution)
  status: "queued" | "running" | "completed" | "failed";
  result?: {
    output_file: string;
    tokens_used: number;
    cost: number;
    duration_ms: number;
  };
}
```

### Backend Strike Orchestrator

```python
class StrikeOrchestrator:
    """
    Manages the execution of strike sequences with support for
    both Ultra (continuous) and Batch (synchronous) modes.
    """
    
    def __init__(self):
        self.active_strikes = {}  # track_id -> StrikeState
        self.key_pool = KeyPool()
        self.governor = HellcatGovernor()
        
    async def execute_sequence(self, request: StrikeSequenceRequest) -> StrikeResult:
        track_id = generate_track_id()
        
        # Initialize state
        state = StrikeState(
            track_id=track_id,
            slots=request.slots,
            payloads=request.payloads,
            mode=request.global.threading_mode,
            thread_count=request.global.thread_count
        )
        self.active_strikes[track_id] = state
        
        try:
            if request.global.threading_mode == "ultra":
                return await self._execute_ultra_mode(state, request)
            else:
                return await self._execute_batch_mode(state, request)
        finally:
            del self.active_strikes[track_id]
    
    async def _execute_ultra_mode(self, state, request):
        """
        Ultra Mode: Keep N workers constantly busy.
        As soon as one finishes, start the next.
        """
        queue = asyncio.Queue()
        
        # Fill queue with all slot+payload combinations
        for payload_idx, payload in enumerate(request.payloads.files):
            slot = state.slots[payload_idx % len(state.slots)]
            await queue.put((slot, payload))
        
        async def worker():
            while not queue.empty():
                slot, payload = await queue.get()
                
                # Check governor
                can_proceed, reason = self.governor.check_limits(
                    slot.key_override or "auto",
                    request.global.default_model
                )
                
                if not can_proceed:
                    await self._log_blocked(slot, reason)
                    await asyncio.sleep(1)  # Brief pause
                    await queue.put((slot, payload))  # Re-queue
                    continue
                
                # Execute strike
                await self._execute_single_strike(state, slot, payload)
        
        # Start N workers
        workers = [
            asyncio.create_task(worker())
            for _ in range(request.global.thread_count)
        ]
        
        await asyncio.gather(*workers)
        return state.get_result()
    
    async def _execute_batch_mode(self, state, request):
        """
        Batch Mode: Fire N at once, wait for all, then next N.
        """
        payloads = request.payloads.files
        thread_count = request.global.thread_count
        
        for batch_start in range(0, len(payloads), thread_count):
            batch = payloads[batch_start:batch_start + thread_count]
            
            # Execute batch in parallel
            tasks = []
            for i, payload in enumerate(batch):
                slot = state.slots[i]
                task = asyncio.create_task(
                    self._execute_single_strike(state, slot, payload)
                )
                tasks.append(task)
            
            # Wait for ALL to complete
            await asyncio.gather(*tasks)
            
            # Optional: delay between batches
            await asyncio.sleep(request.global.base_delay_ms / 1000)
        
        return state.get_result()
```

---

## 7. IMPLEMENTATION PLAN

### Phase 1: Backend API (FastAPI)

```
1. Extend /v1/fs routes
   ├── GET /v1/fs/payloads?dir=english
   ├── GET /v1/fs/payloads/{path}/content
   └── GET /v1/fs/payloads/{path}/stats (line count, size, etc.)

2. Extend /v1/prompts routes
   ├── GET /v1/prompts (list all)
   ├── GET /v1/prompts/{id}/content
   ├── POST /v1/prompts (create new)
   ├── PUT /v1/prompts/{id} (update)
   └── DELETE /v1/prompts/{id}

3. New /v1/striker routes
   ├── POST /v1/striker/sequence (execute)
   ├── GET /v1/striker/sequence/{track_id}/status
   ├── POST /v1/striker/sequence/{track_id}/cancel
   └── GET /v1/striker/keys/available (healthy keys)

4. WebSocket for real-time telemetry
   └── WS /v1/striker/stream
       (emits: slot_start, slot_complete, gauge_updates, alerts)
```

### Phase 2: Frontend UI (React)

```
1. Context Vault Components
   ├── PromptSelector
   │   ├── PromptList
   │   ├── PromptPreview
   │   └── PromptEditor (collapsible)
   │
   └── PayloadSelector
       ├── DirectoryBrowser (tree view)
       ├── FileList (ammo pile)
       ├── LoadedFilesList
       └── TransferControls (move/copy buttons)

2. Strike Manifest Components
   ├── SlotConfiguration (10 rows)
   │   ├── ModelDropdown
   │   ├── KeyDropdown
   │   ├── DelayInput
   │   └── PayloadAssignment
   │
   ├── GlobalSettings
   │   ├── ThreadingModeToggle
   │   ├── ThreadCountSlider
   │   ├── HellcatModeSelector
   │   └── BaseDelayInput
   │
   └── PostSequenceControls
       ├── RepeatToggle
       ├── RotateKeysToggle
       └── AutoRepeatToggle

3. Gauges Panel
   ├── TPSGauge (Tokens Per Second)
   ├── RPMGauge (Requests Per Minute)
   ├── LatencyGauge
   ├── CostTracker
   ├── QueueStatus
   ├── KeyPoolStatus
   ├── AlertsList
   └── MasterArmSwitch

4. Execution Monitor
   ├── LiveLogStream
   ├── SlotStatusGrid
   ├── ProgressBar
   └── ResultViewer
```

### Phase 3: State Management

```typescript
// Global strike state
interface StrikeState {
  // Configuration
  config: {
    global: GlobalSettings;
    prompt: Prompt;
    slots: StrikeSlot[];
    postSequence: PostSequenceSettings;
    payloads: string[];  // Selected file paths
  };
  
  // Execution state
  execution: {
    status: 'idle' | 'arming' | 'running' | 'paused' | 'completed';
    trackId: string | null;
    currentBatch: number;
    totalBatches: number;
    completedCount: number;
    failedCount: number;
  };
  
  // Real-time telemetry
  telemetry: {
    tps: number;
    rpm: number;
    rpmLimit: number;
    latency: number;
    costSession: number;
    activeStrikes: number;
    queuedStrikes: number;
    keyStatus: KeyStatus[];
    alerts: Alert[];
  };
  
  // Slot states
  slots: {
    [slotNumber: number]: {
      status: 'idle' | 'queued' | 'running' | 'completed' | 'failed';
      progress?: number;
      result?: StrikeResult;
    }
  };
}
```

---

## 8. KEY FEATURES SUMMARY

This architecture gives you:

1. **Payload Directory Browser** - Navigate `/root/herbert/liquid-semiotic/english` tree
2. **Multi-select & Transfer** - Checkbox selection, Move/Copy to Loaded
3. **Prompt Preview & Editor** - Full view, collapsible editor with Save/Save As
4. **10-Slot Manifest** - Each slot: model, key, delay, payload assignment
5. **Ultra Mode** - Continuous worker pool (start next as soon as one finishes)
6. **Batch Mode** - Synchronous batches (wait for all N, then next N)
7. **Key Rotation** - Auto-rotate after 10, or per-slot assignment
8. **Repeat Options** - 🔁 Repeat, 🔄 Rotate keys after 10, 📊 Auto-repeat until done
9. **Hellcat Gauges** - TPS, RPM, Latency, Cost, Queue, Key Pool health
10. **Master Arm** - Safety switch to enable/disable execution

The system is designed as a **pilot's dashboard** - every control visible, real-time feedback, safety limits enforced by the governor.

---

*Generated for PEACOCK ENGINE V3 - Payload Striker System*
