# PEACOCK AVIARY — Complete UI Scaffold Specification

> Version: 1.0  
> Date: 2026-05-02  
> Purpose: This document is the single source of truth for wiring the Aviary UI to the PEACOCK backend. Every component, endpoint, event, and data flow is specified here.

---

## 1. ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BROWSER (Client)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │ Search      │  │ Payload     │  │ Modal       │  │ Pipeline  │ │
│  │ Results     │  │ Assembly    │  │ Editor      │  │ Visual    │ │
│  │ (Left)      │  │ (Right)     │  │ (Overlay)   │  │ (Bottom)  │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘ │
│         │                │                │               │       │
│         └────────────────┴────────────────┘               │       │
│                          │                                │       │
│                    WebSocket / SSE                         │       │
│                          │                                │       │
└──────────────────────────┼────────────────────────────────┘       │
                           │                                         │
                           ▼                                         │
┌────────────────────────────────────────────────────────────────────┘
│                      PEACOCK ENGINE (Port 3099)                     │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ Aviary     │  │ Buckets    │  │ Assembly   │  │ Streaming    │  │
│  │ Routes     │  │ Routes     │  │ Endpoint   │  │ SSE Handler  │  │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └──────┬───────┘  │
│        │               │               │                │          │
│        └───────────────┴───────────────┘                │          │
│                        │                                │          │
│                   HTTP (localhost)                       │          │
│                        │                                │          │
└────────────────────────┼────────────────────────────────┘          │
                         │                                            │
                         ▼                                            │
┌─────────────────────────────────────────────────────────────────────┘
│                   PEACOCK UNIFIED (Port 8000)                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │ /api/search│  │ /api/docum-│  │ /api/docum-│  │ ChromaDB     │  │
│  │            │  │ ent/{id}   │  │ ents (where)│  │ Persistent   │  │
│  └────────────┘  └────────────┘  └────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

**Key Principle:** The UI NEVER talks directly to port 8000. All requests go through PEACOCK ENGINE (3099) which proxies to UNIFIED (8000).

---

## 2. PAGES & ROUTES

### 2.1 Aviary Pipeline UI

| Property | Value |
|----------|-------|
| **URL** | `GET /v1/aviary/` |
| **Served By** | `app/routes/aviary.py` → `aviary_ui()` |
| **File** | `app/static/neural-link/aviary.html` |
| **Auth** | None |
| **Method** | Server-side rendered HTML (no framework) |

**Purpose:** Primary interface for building apps from memory. Database-first workflow.

---

## 3. LAYOUT STRUCTURE

### 3.1 Z-Index Hierarchy

| Layer | Z-Index | Elements |
|-------|---------|----------|
| Background | 0 | Body, gradients |
| Content | 1-10 | Workspace, cards, terminal |
| Floating | 1000 | Peacock Boss (wandering) |
| Overlay | 2000 | Modal Editor |

### 3.2 Grid Layout (Desktop)

```css
.workspace {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 15px;
  max-width: 1400px;
  margin: 0 auto;
}
```

- **Left Column:** Search input → Filters → Results list
- **Right Column:** Payload Assembly panel (sticky/fixed feel)

### 3.3 Responsive Breakpoints

| Breakpoint | Behavior |
|------------|----------|
| > 900px | Two-column grid |
| ≤ 900px | Single column, payload panel becomes slide-out drawer from right |

---

## 4. COMPONENT SPECIFICATIONS

### 4.1 HEADER

```
┌─────────────────────────────────────────────┐
│  PEACOCK                                    │  ← h1, gradient text, 3.5rem
│  The Engine That Builds Apps From Memory    │  ← tagline
│  Aviary — 7 Birds. Zero Visibility.         │  ← sub-brand
└─────────────────────────────────────────────┘
```

| Element | Type | Styling |
|---------|------|---------|
| `h1` | Text | `font-size: 3.5rem`, gradient `linear-gradient(135deg, #00d4aa, #00a8e8, #9b59b6, #ff6b35)`, `letter-spacing: 10px`, uppercase, animated gradient shift 4s |
| Tagline | Text | `color: #e0e0e0`, `letter-spacing: 3px` |
| Sub-brand | Text | `color: #6b6b7b`, `letter-spacing: 2px`, uppercase |

---

### 4.2 SEARCH BAR

```
┌──────────────────────────────────────────┬──────────┐
│  [Search your memory vault...          ] │ [Search] │
└──────────────────────────────────────────┴──────────┘
```

| Element | Specification |
|---------|--------------|
| **Input Field** | `id="q"`, placeholder `"Search your memory vault..."`, triggers `doSearch()` on Enter key |
| **Search Button** | Background `#00d4aa`, text black, font-weight 700, calls `doSearch()` |
| **Styling** | Input: `background: #12121a`, `border: 1px solid #1e1e2e`, `border-radius: 8px`, focus state border turns `#00d4aa` |

**Event Flow:**
```
User types → Presses Enter → doSearch() → GET /v1/aviary/search?q={query}&collections={activeFilter}&n=8
                                      → renderResults(response)
```

---

### 4.3 COLLECTION FILTERS

```
[ All ] [ Conversations ] [ Tech ] [ Seeds ] [ Personal ] [ Cases ]
   ↑on
```

| Element | Specification |
|---------|--------------|
| **Filter Pills** | `.filter` class, `border-radius: 16px`, padding `5px 12px` |
| **Active State** | `.on` class → border `#00d4aa`, text `#00d4aa`, background `rgba(0,212,170,0.05)` |
| **Inactive** | border `#1e1e2e`, text `#6b6b7b` |
| **Data Attribute** | `data-c` values: `all`, `chat_conversations`, `tech_vault`, `seed_vault`, `personal_vault`, `case_files_vault` |

**Behavior:**
- Clicking a filter sets `activeFilter` global variable
- Next search uses this filter
- `all` = search all vault collections

---

### 4.4 SEARCH RESULT CARDS

```
┌────────────────────────────────────────────┐
│ [chatgpt]  2025-01-27                      │  ← badge + date
│ what is an easy way to reverse engineer... │  ← line 1 (truncated)
│ api security • burp, mitmproxy, openapi    │  ← line 2 (metadata)
└────────────────────────────────────────────┘
```

| Element | Specification |
|---------|--------------|
| **Container** | `.result-card`, `background: #12121a`, `border: 1px solid #1e1e2e`, `border-radius: 10px`, hover → border `#00d4aa`, translateX(3px) |
| **Platform Badge** | `.badge-{platform}` — chatgpt (#10a37f), claude (#d4a332), gemini (#4285f4), default (#6b6b7b) |
| **Line 1** | `.line`, max 90 chars, `white-space: nowrap`, `text-overflow: ellipsis` |
| **Line 2** | `.line2`, metadata: `{project} • {topics substring}` |
| **Click Action** | `openEditor(docId, collection, text)` — opens Modal Editor with the document text |

**Data Binding:**
```javascript
{
  id: "chat_conversations__abc123",
  collection: "chat_conversations",
  document: "...text...",
  metadata: {
    platform: "CHATGPT",
    timestamp: "2025-01-27",
    project: "api security",
    topics: "burp, mitmproxy, openapi"
  }
}
```

---

### 4.5 MODAL EDITOR (Overlay)

```
┌─────────────────────────────────────────────────────────────┐
│  ✏️ Editor          Tokens: 12,450  Chars: 49,800  Blocks:  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │  ← Block A (dark blue)
│  │  what is an easy way to reverse engineer an api...  │   │
│  │  are there any tools that work with burp...         │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│   │  ← Block B (brown)
│  │  When you talk about reverse engineering...         │   │
│  │  By examining these requests, you can learn...      │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ...                                │
│                                                             │
│  Each colored block is a paragraph...          [Save] [Rst]│
└─────────────────────────────────────────────────────────────┘
```

| Element | Specification |
|---------|--------------|
| **Overlay** | `.modal-overlay`, `position: fixed`, `z-index: 2000`, `background: rgba(0,0,0,0.85)`, hidden by default, `.on` class shows flex |
| **Modal Box** | `.modal-box`, `max-width: 900px`, `height: 85vh`, `background: #12121a`, `border: 1px solid #1e1e2e`, `border-radius: 16px` |
| **Header** | Shows "✏️ Editor", token count, char count, block count, Close button |
| **Editor Area** | `.modal-editor`, `contenteditable="true"`, font: `'SF Mono' monospace`, `font-size: 0.82rem` |
| **Block Highlighting** | Each paragraph (split by `\n\n+`) becomes a `.block` div. Odd blocks: `background: #1a1a2e` (dark blue-gray). Even blocks: `background: #1e1810` (brown). Focus state: `rgba(0,212,170,0.08)` with accent border |
| **Save Button** | `.save-btn`, `background: #00d4aa`, text black, calls `saveModal()` |
| **Reset Button** | `.reset-btn`, transparent, border `#ffd93d`, text `#ffd93d`, calls `resetModal()` |
| **Stats** | Live-updated on every keystroke: tokens = `Math.floor(text.length / 4)`, chars = `text.length`, blocks = paragraph count |

**Text Splitting Rule:**
```javascript
function splitBlocks(text) {
  return text.split(/\n\n+/).filter(b => b.trim()).map(b => b.trim());
}
```
Every double-newline (or more) creates a new block. Single newlines stay inside the block.

**Editing Behavior:**
- Each block is `contenteditable`
- Pressing Enter INSIDE a block: splits the block at cursor position
- Pressing Backspace at start of block: merges with previous block
- Clicking a block focuses it with accent glow
- Scrolling: modal editor has `overflow: auto`, shows ~20-25 lines visible at once

**Save Flow:**
```
saveModal():
  1. Collect all block.textContent values
  2. Join with '\n\n'
  3. If editingIdx >= 0: update payload[editingIdx].text
  4. Else: push new item to payload array
  5. renderPayload()
  6. closeModal()
```

**Reset Flow:**
```
resetModal():
  1. Restore editingOriginal (the untouched assembled content)
  2. Re-split into blocks
  3. Re-render editor
```

---

### 4.6 PAYLOAD ASSEMBLY PANEL (Right Column)

```
┌─────────────────────────────┐
│ 🎯 Payload        3 items   │
│                             │
│ ┌─────────────────────────┐ │
│ │ doc_abc123        ✏️ 🗑️ │ │
│ │ 12,450 tokens         □ │ │  ← checkbox unchecked
│ └─────────────────────────┘ │
│ ┌─────────────────────────┐ │
│ │ doc_def456        ✏️ 🗑️ │ │
│ │ 8,200 tokens          ☑ │ │  ← checkbox checked
│ └─────────────────────────┘ │
│                             │
│  20,650 tokens • 82,600   │
│ [✂️ Create Chunks]          │
│ [🦚 PEACOCK — Launch Spark] │
└─────────────────────────────┘
```

| Element | Specification |
|---------|--------------|
| **Container** | `.payload-col`, `background: #12121a`, `border: 1px solid #1e1e2e`, `border-radius: 12px`, `padding: 14px`, sticky/fixed feel |
| **Header** | "🎯 Payload" title + item count |
| **Payload Items** | `.payload-item`, `background: #0d0d14`, `border: 1px solid #1e1e2e`, `border-radius: 8px` |
| **Item Actions** | ✏️ Edit (calls `editPayload(index)`), 🗑️ Remove (calls `removePayload(index)`) |
| **Checkbox** | `type="checkbox"`, checked items are included in build, unchecked items are skipped |
| **Footer Stats** | Total tokens + total chars of ALL items (checked or not) |
| **Create Chunks Button** | `.chunk-btn`, gradient `#4d4dff` → `#9b59b6`, hidden when payload empty, calls `createChunks()` |
| **Launch Spark Button** | `.spark-btn`, gradient `#00d4aa` → `#00a8e8`, disabled when payload empty, calls `launchSpark()` |

**Payload Item Data Structure:**
```javascript
{
  id: "doc_{timestamp}_{random}",
  text: "...full assembled content...",
  original: "...untouched original from DB...",
  checked: true
}
```

**Create Chunks Flow:**
```
createChunks():
  1. Filter payload for checked items only
  2. Join all checked texts with '\n\n\n'
  3. Split into paragraphs by '\n\n'
  4. Greedy chunking: max 4000 tokens per chunk (~16,000 chars)
  5. Pack paragraphs into chunks without exceeding limit
  6. Store chunks in global `chunks` array
  7. renderChunks() — replaces payload view with chunk cards
```

---

### 4.7 CHUNKS VIEW

```
┌─────────────────────────────────────────┐
│ 📦 Chunks Ready for Spark               │
│                                         │
│ ┌─────────────────────────────────────┐ │
│ │ Chunk 1              3,980 tokens   │ │
│ │ what is an easy way to reverse...   │ │
│ └─────────────────────────────────────┘ │
│ ┌─────────────────────────────────────┐ │
│ │ Chunk 2              3,950 tokens   │ │
│ │ When you talk about reverse eng...  │ │
│ └─────────────────────────────────────┘ │
│                                         │
│          [🦚 PEACOCK — Launch Spark]    │
└─────────────────────────────────────────┘
```

| Element | Specification |
|---------|--------------|
| **Shown When** | After `createChunks()` is called |
| **Hides** | `.workspace` grid and `.payload-col` |
| **Chunk Cards** | `.chunk-card`, `background: #0d0d14`, shows chunk number + token count + preview |
| **Launch Button** | Same `.spark-btn`, calls `launchSpark()` which uses `chunks` array |

---

### 4.8 PIPELINE VISUAL

```
[🔥 Spark] → [🦅 Falcon] → [🦅 Eagle] → [🐦‍⬛ Crow] → [🦉 Owl] → [🐦‍⬛ Raven] → [🦅 Hawk]
```

| Phase | Icon | Name | Job | Feather Spread |
|-------|------|------|-----|----------------|
| 1 | 🔥 | Spark | Distill chat log → spec | 2 feathers |
| 2 | 🦅 | Falcon | Mine invariants | 5 feathers |
| 3 | 🦅 | Eagle | Create implementation plan | 9 feathers |
| 4 | 🐦‍⬛ | Crow | UI scaffold design | 13 feathers |
| 5 | 🦉 | Owl | Code file by file | 18 feathers |
| 6 | 🐦‍⬛ | Raven | Audit & route fixes | 21 feathers |
| 7 | 🦅 | Hawk | Package for deploy | 26 feathers (full spread) |

**States:**
- `.bnode` = default (dim)
- `.bnode.on` = active (accent border, glowing icon, pulsing animation)
- `.bnode.done` = complete (accent border, faded)
- `.bnode.bad` = failed (red border)

**Arrow Animation:** `.arr.on` = flowing right animation when next bird activates

---

### 4.9 TERMINAL

```
┌──────── peacock.log — live stream ────────┐
│ [22:15:30] 🚀 [AVIARY] PEACOCK LAUNCHED   │
│ [22:15:31] 🔥 [SPARK] Phase 1/7: distilling│
│ [22:15:45] ✨ [SPARK] Complete (14,230ms)  │
│ [22:15:46] 🦅 [FALCON] diving...           │
│ ...                                         │
└─────────────────────────────────────────────┘
```

| Element | Specification |
|---------|--------------|
| **Shown When** | Pipeline starts (`.term.on` class) |
| **Lines** | `.term-line`, color-coded by bird: spark=#ff6b35, falcon=#ffd93d, eagle=#6bcb77, crow=#4d4dff, owl=#9b59b6, raven=#7f8c8d, hawk=#e74c3c, aviary=#00d4aa, error=#e74c3c, success=#6bcb77, tone=#ff69b4 |
| **Auto-scroll** | `scrollTop = scrollHeight` on every new line |

---

### 4.10 PEACOCK BOSS (Wandering Character)

```
     👑
    🕶️  ← sunglasses
     💲  ← gold chain
    👟👟 ← red kicks
```

| Property | Value |
|----------|-------|
| **Position** | `fixed`, `z-index: 1000` |
| **Animation** | `bossWander` — drifts across viewport, flips horizontally at waypoints |
| **Bob** | `bossBob` — gentle up/down float |
| **Attitude Bubble** | `.boss-bubble`, pops up with random phrases every 4-6 seconds |
| **Feathers** | 26 SVG feathers, spread incrementally per phase completion |
| **Shake** | Rapid side-to-side wiggle when feathers spread (funny peacock butt shake) |
| **Celebrate** | Full 26-feather spread with shimmer animation on pipeline complete |

**Attitude Phrases:**
```javascript
{
  idle: ["watchin'...", "easy money", "let's go", "pimpin'", "no sweat", "chillin'", "too easy"],
  select: ["good choice", "that one's fire", "solid pick", "let's cook", "build it"],
  shake: ["*wiggle wiggle*", "check this out", "shake it baby", "brrrrrrr", "vibratin'"],
  complete: ["FULL SPREAD", "PIMP WALK", "FEATHERS OUT", "TOO EASY", "KING SHIT", "DONE DEAL"]
}
```

---

## 5. STATE MANAGEMENT

### 5.1 Global Variables (Frontend)

```javascript
let activeFilter = 'all';        // Current collection filter
let payload = [];                // Array of payload items
let chunks = [];                 // Array of chunked payloads
let editingIdx = -1;             // Index of item being edited in modal (-1 = new)
let editingOriginal = '';        // Untouched original text for revert
let currentRunId = '';           // Active pipeline run ID
let filesGenerated = [];         // Files from Owl phase
let startTime = 0;               // Pipeline start timestamp
```

### 5.2 Payload Item Shape

```javascript
{
  id: string,           // Unique ID: "doc_{timestamp}_{random4}"
  text: string,         // Current editable content
  original: string,     // Untouched assembled content from DB
  checked: boolean      // Include in build?
}
```

### 5.3 Chunk Shape

```javascript
{
  idx: number,          // 1-based chunk index
  text: string,         // Chunk content
  tokens: number        // Approximate token count
}
```

---

## 6. API ENDPOINTS

### 6.1 Aviary Routes (`/v1/aviary/`)

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| GET | `/` | Serve UI HTML | — | HTML |
| GET | `/search` | Search memory vault | `q`, `collections`, `n` | `{query, results: {coll: [docs]}}` |
| GET | `/recent` | Recent conversations | `collection`, `n` | `{collection, results: [docs]}` |
| GET | `/assembly` | Assemble full doc from chunks | `collection`, `doc_id` | `{content, chars, tokens, chunks_found, source_file, is_fragment}` |
| POST | `/compile` | Start pipeline (background) | `{chat_log_text, ...}` | `{status, run_id}` |
| POST | `/compile/stream` | Start pipeline (SSE) | `{chat_log_text, ...}` | `text/event-stream` |
| GET | `/compile/{run_id}` | Get run status | — | Full result JSON |
| GET | `/compile/{run_id}/file/{path}` | Get generated file | — | `{path, content}` |
| GET | `/compile/{run_id}/deploy` | Get deploy script | — | `{deploy_script, readme}` |
| GET | `/compile/{run_id}/raven` | Get audit log | — | `{raven_approved, audit_log}` |
| GET | `/runs` | List all runs | — | `{runs: [...]}` |

### 6.2 Bucket Routes (`/v1/buckets/`)

| Method | Path | Description | Request | Response |
|--------|------|-------------|---------|----------|
| POST | `/create` | Create bucket | `{name, description}` | `{status, bucket_name}` |
| GET | `/list` | List buckets | — | `{buckets, total}` |
| GET | `/{name}` | Get bucket | — | `{name, description, items, ...}` |
| DELETE | `/{name}` | Delete bucket | — | `{status, deleted}` |
| POST | `/{name}/search` | Search & fill bucket | `{query, collections, n_results}` | `{status, result}` |
| POST | `/{name}/add` | Add doc by ID | `{collection, doc_id, note}` | `{status, result}` |
| POST | `/{name}/add-raw` | Add raw content | `{doc_id, content, original_content, collection, note}` | `{status, added, chars}` |
| POST | `/{name}/remove/{doc_id}` | Remove item | — | `{status, removed, remaining}` |
| POST | `/{name}/update/{doc_id}` | Edit content/note | `{content, note}` | `{status, updated}` |
| POST | `/{name}/revert/{doc_id}` | Revert to original | — | `{status, reverted}` |
| GET | `/{name}/summary` | Text summary | — | `{summary}` |
| GET | `/{name}/tokens` | Token breakdown | — | `{bucket, items, total_chars, total_tokens, breakdown}` |
| POST | `/{name}/compile` | Compile payload | `{separator}` | `{payload, items, total_chars, total_tokens}` |
| POST | `/{name}/chunk` | Split into chunks | `{max_tokens_per_chunk, separator}` | `{chunks, chunk_count, total_tokens}` |
| POST | `/{name}/generate` | Legacy project gen | `{description, project_type_hint, model}` | `{status, project_id}` |
| POST | `/{name}/aviary` | 7-bird pipeline | `{description, enable_memory}` | `{status, run_id, payload_tokens}` |
| POST | `/{name}/aviary/stream` | 7-bird SSE | `{description, enable_memory}` | `text/event-stream` |

### 6.3 Peacock Unified Routes (proxied, Port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/search?q=&collections=&n=` | Vector search across collections |
| GET | `/api/document/{collection}/{doc_id}` | Get single document by ID |
| GET | `/api/documents?collection_name=&where=&limit=` | Query by metadata filter |
| GET | `/api/thread/{thread_id}` | Reconstruct thread from vault entries |
| GET | `/api/stats` | Collection stats |
| GET | `/api/platforms` | Platform distribution |

---

## 7. DATA FLOW DIAGRAMS

### 7.1 Search → Edit → Payload → Chunk → Spark

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Search  │────▶│  Modal   │────▶│ Payload  │────▶│  Chunk   │────▶│  Spark   │
│  Vault   │     │  Editor  │     │  Panel   │     │  Engine  │     │  Phase   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
      │                │                │                │                │
      │ GET /search    │ Edit blocks    │ Save to array  │ Greedy split   │ POST /compile
      │                │                │                │ @ 4000 tok     │ /stream
      ▼                ▼                ▼                ▼                ▼
Results list    Alternating       Checked items    Chunk cards      SSE events
(1-2 lines)     blue/brown        move to right    4000 tok max     per bird
                blocks                                each             phase
```

### 7.2 Assembly Endpoint (No Truncation)

```
User clicks result
       │
       ▼
GET /v1/aviary/assembly?collection=X&doc_id=Y
       │
       ▼
Fetch doc metadata ──▶ Extract "file" path from metadata
       │
       ▼
GET /api/documents?collection_name=X&where={"file": "/path/to/file.md"}
       │
       ▼
Receive ALL chunks (56 chunks example)
       │
       ▼
Sort by "entry" metadata (001, 002, 003...)
       │
       ▼
Concatenate with "\n\n"
       │
       ▼
Return: {content: "FULL TEXT", chars: 292612, tokens: 73153, chunks_found: 56}
```

### 7.3 Pipeline SSE Event Stream

```
Client opens EventSource to POST /v1/aviary/compile/stream
       │
       ├── event: pipeline_start  ──▶ Spark bird goes "on"
       │
       ├── event: phase_start     ──▶ Current bird goes "on"
       │
       ├── event: phase_complete  ──▶ Bird goes "done", next bird "on", feathers spread
       │
       ├── event: file_complete   ──▶ Tone played, file card added to output
       │
       ├── event: audit_passed    ──▶ Raven approved
       │
       ├── event: pipeline_complete ──▶ All feathers spread, celebrate animation
       │
       └── event: stream_end      ──▶ Connection closes
```

---

## 8. EVENT TYPES (SSE)

| Event | Bird | Payload Fields | UI Action |
|-------|------|----------------|-----------|
| `pipeline_start` | aviary | `input_length` | Spark goes active, peacock attitude |
| `phase_start` | any | — | Bird node active, attitude bubble |
| `phase_complete` | any | `output_length`, `latency_ms` | Bird done, next active, feathers spread, THE SHAKE |
| `file_list` | owl | `files: [...]` | Log file list |
| `file_start` | owl | `file`, `index` | Log "Generating X..." |
| `file_complete` | owl | `file`, `tone: {note, octave, frequency}` | File card added, tone played |
| `file_error` | owl | `file`, `error` | Log error |
| `audit_fail` | raven | `issues`, `critical`, `route_to` | Raven failed, show warning |
| `audit_passed` | raven | `attempts` | Raven done, checkmark |
| `loopback` | aviary | `retry` | Owl re-activates for fix |
| `pipeline_complete` | aviary | `file_count`, `duration_ms`, `raven_approved` | Full celebration, output panel shown |
| `pipeline_failed` | aviary | `error` | Error state, all stop |
| `memory_loaded` | aviary | `context_length` | Log memory loaded |
| `stream_end` | aviary | `status` | Close stream |

---

## 9. TOKEN MATH

```javascript
// Approximation used throughout
function countTokens(text) {
  return Math.max(1, Math.floor(text.length / 4));
}

// Chunk sizing
const MAX_TOKENS_PER_CHUNK = 4000;  // Safe for Groq llama-3.3-70b
const MAX_CHARS_PER_CHUNK = 4000 * 4; // ~16,000 chars

// Greedy chunking algorithm
 paragraphs = text.split('\n\n');
 currentChunk = [];
 currentTokens = 0;
 
 for each paragraph:
   paraTokens = countTokens(paragraph);
   if (currentTokens + paraTokens > MAX_TOKENS && currentChunk not empty):
     output.push(currentChunk.join('\n\n'));
     currentChunk = [paragraph];
     currentTokens = paraTokens;
   else:
     currentChunk.push(paragraph);
     currentTokens += paraTokens;
 
 if (currentChunk not empty):
   output.push(currentChunk.join('\n\n'));
```

---

## 10. ANIMATIONS & TRANSITIONS

| Animation | Trigger | Duration | CSS |
|-----------|---------|----------|-----|
| Gradient shift | Always (header) | 4s | `background-position` animation |
| Boss wander | Always | 20s | `transform: translate()` keyframes |
| Boss bob | Always | 2.5s | `translateY()` + `rotate()` |
| Boss shake | Phase complete | 0.6s | Rapid `translateX()` + `rotate()` |
| Feather spread | Phase complete | 0.6s staggered | `opacity` + `rotate()` per feather |
| Feather shimmer | Pipeline complete | 0.4s alternate | `brightness` + `drop-shadow` |
| Result card hover | Mouse over | 0.2s | `border-color`, `translateX(3px)` |
| Modal open | Click result | 0.3s | `display: flex` + opacity fade |
| Block focus | Click block | 0.3s | `box-shadow`, `background` |
| Terminal line | New log | 0.3s | `opacity` + `translateX` fade-in |
| File card | Complete | 0.5s | `fadeIn` keyframe |

---

## 11. ERROR HANDLING

| Scenario | Behavior |
|----------|----------|
| Search fails | Results area shows error message in red |
| Assembly fails (no file metadata) | Returns `is_fragment: true` with warning. Modal shows truncated text with warning banner |
| Empty payload | "Launch Spark" disabled, "Create Chunks" hidden |
| No checked items | Alert: "Check at least one item to chunk" |
| Pipeline fails mid-flight | Bird node turns red (`bad` class), terminal logs error, peacock attitude = "💥" |
| SSE disconnect | Terminal logs "Stream failed", Launch button re-enabled |

---

## 12. ACCESSIBILITY

| Feature | Implementation |
|---------|---------------|
| Focus states | All interactive elements have visible focus rings |
| Modal trap | Tab cycles within modal when open. Escape closes modal |
| Checkbox labels | All checkboxes have `<label>` elements |
| Color contrast | Text `#e0e0e0` on `#0a0a0f` = 15.3:1 ratio |
| Reduced motion | `@media (prefers-reduced-motion)` disables wander, shimmer, pulse |

---

## 13. FILE LOCATIONS

| Component | Path |
|-----------|------|
| UI HTML | `/root/hetzner/ai-engine/app/static/neural-link/aviary.html` |
| Aviary Routes | `/root/hetzner/ai-engine/app/routes/aviary.py` |
| Aviary Core | `/root/hetzner/ai-engine/app/core/aviary.py` |
| Bucket Routes | `/root/hetzner/ai-engine/app/routes/buckets.py` |
| Prompts | `/root/hetzner/ai-engine/prompts/aviary/` |
| This Document | `/root/hetzner/ai-engine/docs/AVIARY_UI_SCAFFOLD.md` |
| Peacock Unified | `/root/peacock_unified.py` |
| Unified DB | `/root/chroma-unified/` |

---

## 14. BIRD PROMPTS (Aviary Pipeline)

| Bird | File | Job |
|------|------|-----|
| Spark | `prompts/aviary/spark.md` | Distill chat log into specification |
| Falcon | `prompts/aviary/falcon.md` | Mine invariants from spec |
| Eagle | `prompts/aviary/eagle.md` | Create implementation plan |
| Crow | `prompts/aviary/crow.md` | Design complete UI scaffold |
| Owl | `prompts/aviary/owl.md` | Generate code file by file |
| Raven | `prompts/aviary/raven.md` | Audit code, route fixes |
| Hawk | `prompts/aviary/hawk.md` | Package deploy script + README |

---

*End of Scaffold. This document should be updated whenever the UI or API changes.*
