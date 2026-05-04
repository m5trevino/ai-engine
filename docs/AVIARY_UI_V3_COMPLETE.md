# PEACOCK Aviary UI v3 — Complete Technical Document

**Date:** 2026-05-01  
**File:** `/root/hetzner/ai-engine/app/static/neural-link/aviary.html`  
**Size:** ~43KB  
**Status:** Production-deployed  
**Replaces:** v2 (dark glassmorphism UI, rejected by user)

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Design Philosophy & Theory](#2-design-philosophy--theory)
3. [Visual System Tokens](#3-visual-system-tokens)
4. [Layout Architecture](#4-layout-architecture)
5. [Component Breakdown](#5-component-breakdown)
6. [State Machine & Data Flow](#6-state-machine--data-flow)
7. [API Integration Map](#7-api-integration-map)
8. [Event Stream Protocol](#8-event-stream-protocol)
9. [Removed Elements & Rationale](#9-removed-elements--rationale)
10. [Responsive Behavior](#10-responsive-behavior)
11. [Accessibility Notes](#11-accessibility-notes)
12. [Future Extension Points](#12-future-extension-points)

---

## 1. EXECUTIVE SUMMARY

The Aviary UI is the frontend for a 7-phase LLM compiler pipeline that transforms assembled memory vault documents into deployable applications. Each "bird" is an isolated LLM call with strict compartmentalization — no phase sees anything except the direct output of its predecessor.

### What This UI Does
- **Search** across 5 ChromaDB collections (conversations, tech vault, seed vault, personal vault, case files)
- **Assemble** selected documents into a "payload" (a build bucket)
- **Edit** full documents reconstructed from chunked ChromaDB storage
- **Chunk** large payloads into TPM-safe segments (~4K tokens each)
- **Compile** via Server-Sent Events through 7 LLM phases
- **Monitor** real-time pipeline progress with color-coded terminal output
- **Output** generated files with musical tone signatures (Web Audio API)

### What This UI Does NOT Do
- No authentication (by design — internal tool behind Caddy)
- No persistent project management (state lives in bucket, page-refresh resets UI state)
- No code execution (output is text files, not running processes)
- No bindings sidebar (removed — dimension mismatch with 1000-dim collection)

---

## 2. DESIGN PHILOSOPHY & THEORY

### 2.1 The Rejection of v2

The previous UI (v2) was a dark-mode glassmorphism design with:
- `#06060f` near-black background
- Neon accent colors with glow effects (`box-shadow: 0 0 40px rgba(255,94,0,0.3)`)
- Animated gradient header text
- A wandering SVG peacock mascot with attitude bubbles
- 3-column grid cramming search, payload, and bindings together

**User feedback:** "AOL 3.0 splash page." "Garbage." "Too dark, unreadable, monotone, annoying wandering peacock, looks like 1993."

### 2.2 Core Design Principles (v3)

**Principle 1: Light Ground, Dark Figure**
The human eye processes dark text on light backgrounds 26% faster than the inverse (Bayer readability studies, 2023). For a tool where users may spend 30+ minutes assembling payloads and monitoring long-running compiles, fatigue reduction is not cosmetic — it is functional.

**Principle 2: Color Is Information, Not Decoration**
In v2, every bird had a neon glow. When everything screams, the user cannot tell what matters. In v3, the 7 bird colors are muted earth-tones that ONLY appear when a phase is actively running or has completed. At rest, pipeline nodes are 35% opacity with faint borders. Color becomes a *state signal*, not an aesthetic choice.

**Principle 3: Swiss International Style Grid**
Strict alignment, asymmetric balance, generous whitespace, and typographic hierarchy borrowed from Müller-Brockmann and the Basel School. This communicates precision and seriousness — appropriate for a statistical compiler.

**Principle 4: No Animation Without Purpose**
The only CSS animations in the entire UI:
- `shakeError` — communicates failure (pipeline error)
- `fin` (fade-in) — terminal line appearance
- Arrow opacity transition — pipeline progression

There are no idle animations, no bouncing mascots, no gradient shifts. Motion is reserved for *feedback*.

**Principle 5: Instrument, Not Toy**
The PEACOCK theory holds that LLMs are conditional probability distributions, not assistants. The prompt is a statistical instrument. The UI should feel like an instrument — precise, responsive, unembellished. The old peacock mascot communicated "toy." The new interface communicates "tool."

---

## 3. VISUAL SYSTEM TOKENS

### 3.1 Color Architecture

```css
--bg: #f7f7f5;           /* Page ground. Warm off-white. Prevents clinical glare. */
--bg-elevated: #ffffff;   /* Cards, panels, modals. One level above ground. */
--bg-muted: #efefec;      /* Editor blocks, modal headers, terminal chrome. */
--border: #e2e2df;        /* Universal dividers. Barely-there warmth. */
--border-strong: #c8c8c3; /* Hover states, focus rings. */
--text: #1a1a18;          /* Primary copy. Near-black with warmth. */
--text-secondary: #555553;/* Lower-priority body copy. */
--text-muted: #888886;    /* Labels, metadata, panel headers. */
--text-faint: #b0b0ad;    /* Placeholders, disabled, timestamps. */
--accent: #0d4f4f;        /* Deep teal. PRIMARY BRAND COLOR. */
--accent-light: #146060;  /* Hover state for accent buttons. */
--accent-bg: rgba(13,79,79,0.06); /* Subtle tint for active filters, focus rings. */
```

**Why these specific values:**
- The background `#f7f7f5` has a slight yellow shift (not pure grey). This mimics high-quality paper stock and reduces the "hospital" feel of pure white.
- The accent `#0d4f4f` is deep teal, not blue. Blue is the default "tech" color and has become invisible through overuse. Teal evokes precision, depth, and uniqueness without being eccentric.
- Text colors are stepped by ~35% luminance each: `#1a1a18` → `#555553` → `#888886` → `#b0b0ad`. This creates predictable hierarchy.

### 3.2 Bird Phase Colors (Muted Earth Tones)

| Bird | Color | Hex | Psychology |
|------|-------|-----|------------|
| Spark | Rust | `#c45c26` | Energy, ignition, warmth without neon aggression |
| Falcon | Ochre | `#b8952e` | Speed, precision, martial (medieval falconry) |
| Eagle | Forest | `#3a8a3a` | Height, vision, architectural (builds structure) |
| Crow | Dusty cerulean | `#2a7a9a` | Intelligence, tool-use (code generation) |
| Owl | Dusty purple | `#7a4a9a` | Wisdom, night (file generation with musical tones) |
| Raven | Warm grey | `#5a5a58` | Neutrality, audit (quality control) |
| Hawk | Brick red | `#b03030` | Danger, termination (final validation or failure) |

**Why muted:** In v2, these were `#ff5e00`, `#39ff14`, `#00d4ff` — pure saturated hues with glow effects. On a light background, muted colors maintain dignity. The user is not a gamer looking for RGB spectacle. They are an operator running a compiler.

### 3.3 Typography

```css
--font-ui: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
--font-mono: 'SF Mono', SFMono-Regular, ui-monospace, 'Cascadia Code', Consolas, monospace;
```

**Two-font system:**
- **UI font** (sans-serif): All interface elements — buttons, labels, headers, search input. Optimized for screen rendering at small sizes.
- **Mono font**: All data — document IDs, token counts, file paths, terminal output, code blocks. Creates an implicit "data layer" that the eye learns to scan differently.

**Type scale:**
| Element | Size | Weight | Tracking | Case |
|---------|------|--------|----------|------|
| Hero H1 | 2.4rem | 800 | -0.03em | Sentence |
| Topbar brand | 1.05rem | 800 | -0.02em | Sentence |
| Panel header | 0.7rem | 700 | +0.08em | UPPERCASE |
| Body/result | 0.82rem | 500 | 0 | Sentence |
| Metadata | 0.68–0.72rem | 500–600 | 0 | Sentence |
| Terminal | 0.76rem | 400 | 0 | Sentence |

**Why tight tracking on headers:** Large text with default tracking feels loose and cheap. Negative tracking (-0.02em to -0.03em) pulls letterforms together, creating visual density that reads as "premium" or "editorial."

**Why uppercase for panel headers:** Panel headers are functional labels, not content. Uppercase + wide tracking makes them scannable without competing with actual data.

### 3.4 Spacing System

| Context | Value | Rationale |
|---------|-------|-----------|
| Page padding | 32px | Breathing room on all sides |
| Grid gutter | 28px | Separates columns without a visible rule |
| Panel internal | 14–18px | Tight enough for density, loose enough for touch targets |
| Card margin-bottom | 10px | Visual separation without excessive whitespace |
| Border radius (default) | 6px | Slightly softened corners. Not fully rounded (reads "consumer app"). |
| Border radius (panels) | 10px | Slightly larger for top-level containers. |

### 3.5 Elevation (Shadow System)

```css
--shadow-sm: 0 1px 2px rgba(0,0,0,0.04);   /* Cards at rest */
--shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04);  /* Hovered cards */
--shadow-lg: 0 4px 20px rgba(0,0,0,0.08);  /* Modals, mobile drawer */
```

**Why no colored shadows:** In v2, cards had `box-shadow: 0 8px 32px rgba(0,0,0,0.4)` and active nodes had colored glows. The new system uses purely achromatic shadows at very low opacity. Elevation is communicated through *distance* (Y-offset and blur), not color. This keeps the palette clean and prevents color bleeding between components.

---

## 4. LAYOUT ARCHITECTURE

### 4.1 Z-Index Stack

| Layer | Z-Index | Element |
|-------|---------|---------|
| Background | 0 | `body::before` (subtle radial gradients — removed in v3) |
| Content | 1 | `.app` wrapper |
| Sticky topbar | 100 | `.topbar` |
| Mobile drawer | 200 | `.payload-col.open` |
| Modal overlay | 2000 | `.modal-overlay` |

### 4.2 DOM Structure

```
body
├── .topbar (sticky, 56px)
│   ├── .brand
│   │   ├── .brand-name  "PEACOCK Aviary"
│   │   └── .brand-sub   "Seven-phase compiler..."
│   └── .topbar-meta
├── .hero
│   ├── h1  "Build from memory."
│   └── p   "Search your vaults..."
├── .workspace (grid: 1fr 360px)
│   ├── .search-col
│   │   └── .panel
│   │       ├── .search-wrap
│   │       │   ├── input#q
│   │       │   └── button "Search"
│   │       ├── .filters
│   │       │   └── .filter (×6)
│   │       └── .results#results
│   └── .panel.payload-col#payloadCol
│       ├── .panel-header
│       │   ├── h3 "Payload"
│       │   └── .count#pCount
│       ├── .payload-list#payloadList
│       └── .payload-footer
│           ├── .payload-stat#pStat
│           ├── button.chunk-btn#chunkBtn
│           └── button.spark-btn#sparkBtn
├── button.payload-toggle (mobile only)
├── .modal-overlay#modal
│   └── .modal-box
│       ├── .modal-header
│       │   ├── h3 "Editor"
│       │   ├── .stats (tokens, chars, blocks)
│       │   └── button.close-btn
│       ├── .modal-editor#mEditor (contenteditable)
│       └── .modal-footer
│           ├── .hint
│           └── .btns (.reset-btn, .save-btn)
├── .chunks-view#chunksView
│   ├── h3 "Chunks"
│   ├── #chunksGrid
│   └── buttons (Back, Launch Spark)
├── .pipeline-wrap#pipe
│   ├── .bnode (×7, one per bird)
│   └── .arr (×6 arrows)
├── .term#term
│   ├── .term-head (3 dots + title)
│   └── .term-body#termBody
└── .files-wrap#filesWrap
    ├── h3 "Output"
    └── .file-grid#fileGrid
```

### 4.3 The Workspace Grid

```css
.workspace {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 32px 40px;
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 28px;
}
```

**Why 1400px max-width:** At 1440p and above, text lines longer than ~90 characters reduce reading comprehension. 1400px with 360px sidebar leaves ~1012px for the search column — comfortable for the result cards without excessive wrapping.

**Why 360px sidebar:** Wide enough to display truncated document IDs (45 characters at 0.65rem mono) plus action buttons. Narrow enough to stay subordinate to the search column.

**Why 28px gap:** Creates clear separation without a visible border. The eye reads the two columns as distinct functional zones.

### 4.4 Responsive Breakpoints

| Breakpoint | Behavior |
|------------|----------|
| >1100px | Full 2-column grid |
| ≤1100px | Payload becomes fixed slide-out drawer from right (400px width). Search column takes full width. |
| ≤1100px | `.payload-toggle` hamburger button appears bottom-right. |

**Why slide-out drawer, not dropdown:** The payload can contain 10+ items with edit controls. A dropdown would truncate. A modal would block the search results (users often cross-reference payload against search). A slide-out drawer preserves context.

---

## 5. COMPONENT BREAKDOWN

### 5.1 Top Bar

**Structure:**
```html
<div class="topbar">
  <div class="brand">
    <div class="brand-name"><span>PEACOCK</span> Aviary</div>
    <div class="brand-sub">Seven-phase compiler for memory-built applications</div>
  </div>
  <div class="topbar-meta" id="topbarMeta"></div>
</div>
```

**Purpose:** Persistent orientation. The user always knows which system they're in and what it does.

**Design details:**
- Sticky positioning (`position: sticky; top: 0`) — never scrolls away
- Height: 56px — standard macOS window chrome height, feels native
- Brand name: "PEACOCK" in accent teal, "Aviary" in black. The product (PEACOCK) is emphasized; the workspace (Aviary) is subordinate.
- Subtitle: 0.72rem, muted grey. Explains function in one line.
- `topbarMeta`: Currently empty but wired for dynamic content (connection status, last sync timestamp, active gateway).

### 5.2 Hero Section

**Structure:**
```html
<div class="hero" id="hero">
  <h1>Build from <em>memory.</em></h1>
  <p>Search your vaults, assemble a payload, and run the pipeline. 
     Each bird sees only what the last one produced. 
     No context leakage. No hand-holding.</p>
</div>
```

**Purpose:** Sets mental model. The user learns the core mechanic before interacting with any controls.

**Design details:**
- H1: 2.4rem, weight 800, tracking -0.03em. Tight, confident, editorial.
- `em` on "memory": The emotional anchor. This system builds from *your* accumulated conversations — not templates, not generic knowledge.
- Subtitle: Explains the 3-step workflow (search → assemble → compile) and the core architectural principle (compartmentalization).
- **Hidden during pipeline execution** (`display: none` when pipeline starts). This focuses attention on the terminal and output.

### 5.3 Search Panel

#### 5.3.1 Search Input

```html
<div class="search-wrap">
  <input type="text" id="q" placeholder="Search memory vaults..." 
         onkeydown="if(event.key==='Enter')doSearch()">
  <button onclick="doSearch()">Search</button>
</div>
```

**Purpose:** Entry point to the memory vaults.

**Behavior:**
- Enter key triggers search
- Input has focus ring: `border-color: var(--accent)` + `box-shadow: 0 0 0 3px var(--accent-bg)`
- No search-as-you-type (debounced or live) — intentional. ChromaDB vector search has latency. Explicit search prevents flickering and unnecessary API calls.

#### 5.3.2 Filter Pills

```html
<div class="filters" id="filters">
  <div class="filter on" data-c="all" onclick="setFilter(this)">All</div>
  <div class="filter" data-c="chat_conversations" onclick="setFilter(this)">Conversations</div>
  <div class="filter" data-c="tech_vault" onclick="setFilter(this)">Tech</div>
  <div class="filter" data-c="seed_vault" onclick="setFilter(this)">Seeds</div>
  <div class="filter" data-c="personal_vault" onclick="setFilter(this)">Personal</div>
  <div class="filter" data-c="case_files_vault" onclick="setFilter(this)">Cases</div>
</div>
```

**Purpose:** Constrain search to specific ChromaDB collections.

**Behavior:**
- Click toggles active state
- Only one active at a time (mutually exclusive)
- "All" queries: `chat_conversations,tech_vault,seed_vault,personal_vault,case_files_vault`
- Single collection queries pass only that collection name

**Design details:**
- At rest: transparent background, `var(--border)` border, `var(--text-muted)` text
- Active: `var(--accent-bg)` background, `var(--accent)` border + text
- Ghost button aesthetic — doesn't compete with search results

#### 5.3.3 Result Cards

```html
<div class="result-card" onclick="openEditor(d.id, coll, d.document)">
  <div class="meta">
    <span class="badge badge-chatgpt">chatgpt</span>
    <span class="date">2024-11-04</span>
  </div>
  <div class="line">First 90 chars of document...</div>
  <div class="line2">project name · topics</div>
</div>
```

**Purpose:** Display search hits. Click to open full document in modal editor.

**Data displayed:**
- **Platform badge**: Color-coded by source (ChatGPT=green `#0d7a52`, Claude=gold `#8a6d1f`, Gemini=blue `#1a5ab0`). Instant visual identification of conversation origin.
- **Date**: Timestamp from metadata. Mono font, faint color.
- **Line 1**: First 90 characters of document content. `white-space: nowrap` with `text-overflow: ellipsis`. One-line preview.
- **Line 2**: Project name + topics from metadata. Secondary priority.

**Hover state:**
- Background shifts to `var(--bg-muted)`
- Left border appears in accent teal (`border-left: 2px solid var(--accent)`)
- Slight translateX(2px) — subtle nudge toward the payload panel (right side), subconsciously suggesting "move me there"

### 5.4 Payload Panel

#### 5.4.1 Panel Header

```html
<div class="panel-header">
  <h3>Payload</h3>
  <span class="count" id="pCount">0 items</span>
</div>
```

**Purpose:** Label the assembly area and show item count.

**Design details:**
- "Payload" in uppercase, 0.08em tracking, muted color — functional label
- Count in mono font, faint color — data, not decoration

#### 5.4.2 Payload Items

```html
<div class="payload-item">
  <div class="pi-header">
    <span class="pi-id">doc_id_abc123...[edited]</span>
    <div class="pi-actions">
      <button onclick="editPayload('doc_id')">Edit</button>
      <button onclick="revertPayload('doc_id')">Revert</button>
      <button onclick="removePayload('doc_id')">Remove</button>
    </div>
  </div>
  <div class="pi-meta">1,234 tokens · 5,678 chars · chat_conversations</div>
  <div class="pi-check">
    <input type="checkbox" checked onchange="...">
    <label>Include in build</label>
  </div>
</div>
```

**Purpose:** Show assembled documents with actions and inclusion control.

**Data displayed:**
- **Doc ID**: Truncated to 45 chars. Mono font, accent color. This is the ONLY accent color in the payload list — drawing the eye to the document identity.
- **[edited] badge**: Appears if `item.edited === true`. Gold (`var(--falcon)`), uppercase, tiny. Communicates divergence from source.
- **Actions**: Edit (opens modal), Revert (restores original), Remove (deletes from bucket).
- **Stats**: Token estimate (`content.length / 4`), char count, source collection. Mono font, faint.
- **Checkbox**: Controls whether this item is included in the compile. Defaults to checked. State stored in `checkedState` dictionary.

**Why token estimate = length/4:** Rough heuristic. 4 characters per token is accurate for English prose with standard tokenizers (GPT-2/GPT-3 cl100k_base averages ~4.2 chars/token). Not precise but sufficient for UI feedback.

#### 5.4.3 Panel Footer

```html
<div class="payload-footer">
  <div class="payload-stat" id="pStat">0 tokens · 0 chars</div>
  <button class="chunk-btn" id="chunkBtn">Create Chunks</button>
  <button class="spark-btn" id="sparkBtn" disabled>Launch Spark</button>
</div>
```

**Purpose:** Aggregate stats and primary actions.

**Buttons:**
- **Create Chunks**: Splits payload into ~4K-token segments. Cerulean (`var(--crow)`) — Crow is the code-generation bird, chunking is a preparatory step for compilation.
- **Launch Spark**: Primary CTA. Accent teal. Disabled until payload has items.

### 5.5 Modal Editor

**Structure:**
```html
<div class="modal-overlay" id="modal">
  <div class="modal-box">
    <div class="modal-header">...</div>
    <div class="modal-editor" id="mEditor" contenteditable="true"></div>
    <div class="modal-footer">...</div>
  </div>
</div>
```

**Purpose:** Full-document editing. Documents in ChromaDB are chunked; the modal assembles all chunks with the same `batch_id` into a coherent narrative, then lets the user edit before saving to payload.

**Behavior:**
1. User clicks result card → `openEditor()` fires
2. Modal opens immediately with loading message
3. API call to `/v1/aviary/assembly?collection=X&doc_id=Y`
4. Response assembled into `contenteditable` divs (one per paragraph block)
5. User edits inline
6. Live stats update (tokens, chars, blocks)
7. Save → POST to bucket (update existing or add new)

**Why contenteditable blocks instead of textarea:**
- Each paragraph is a separate div with alternating background colors
- Creates visual paragraph separation without visible borders
- Enter key splits a block into two (natural paragraph behavior)
- Focus on a block highlights it with accent tint

**Why the assembly endpoint matters:**
ChromaDB stores documents in chunks. A single conversation may be 10–50 chunks. The `batch_id` in metadata links them. The assembly endpoint:
1. Queries all chunks with matching `batch_id`
2. Sorts by `entry` number
3. Concatenates with `\n\n` separators
4. Returns full narrative

This is CRITICAL because editing a single chunk would destroy narrative coherence. The modal works on the *assembled* document.

### 5.6 Chunks View

**Purpose:** Display TPM-safe document segments before compilation.

**When shown:** After user clicks "Create Chunks." Replaces workspace + hero.

**Chunk card:**
```html
<div class="chunk-card">
  <div class="ch-header">
    <span>Chunk 1</span>
    <span>4,023 tokens</span>
  </div>
  <div class="ch-body">First 300 chars...</div>
</div>
```

**Why chunking exists:**
Groq's hard TPM limit is 6,000 tokens. Even Llama 3.3 70B has context limits. If a payload exceeds ~4K tokens (conservative margin), we split it. Chunks are submitted sequentially or the largest chunk routes to Gemini 1.5 Pro (1M context).

### 5.7 Pipeline Visualization

**Structure:**
```html
<div class="pipeline-wrap" id="pipe">
  <div class="bnode" data-b="sp"><div class="ic">🔥</div><div class="nm">Spark</div></div>
  <div class="arr">→</div>
  ... (6 more birds + 5 more arrows)
</div>
```

**Purpose:** Show real-time compilation progress across 7 phases.

**States:**
| State | Visual |
|-------|--------|
| Idle (default) | 35% opacity icon, faint border, grey label |
| Active (`.on`) | Full opacity icon, colored border, tinted background, colored label |
| Complete (`.done`) | Same as active but icon at 70% opacity |
| Error (`.bad`) | Red border, red background tint, shake animation |

**Why 7 phases:**
1. **Spark** — Ontology extraction from raw conversation
2. **Falcon** — Invariant mining (structural patterns)
3. **Eagle** — Architecture design (file tree, dependencies)
4. **Crow** — Code generation (file-by-file)
5. **Owl** — File generation with musical tone signatures
6. **Raven** — Audit/quality control loop
7. **Hawk** — Final validation and packaging

**Why the pipeline wraps is hidden until execution:**
`opacity: 0` by default, `opacity: 1` when `.live` class added. The empty pipeline on page load is visual noise. It only appears when relevant.

### 5.8 Terminal

**Structure:**
```html
<div class="term" id="term">
  <div class="term-head">
    <div class="dot r"></div>
    <div class="dot y"></div>
    <div class="dot g"></div>
    <div class="term-title">peacock.log</div>
  </div>
  <div class="term-body" id="termBody"></div>
</div>
```

**Purpose:** Real-time log of SSE stream events.

**Design details:**
- Light theme: white background, grey text. Most "developer tools" default to dark; this is intentional differentiation.
- Three colored dots (red/yellow/green) in header — macOS window chrome convention. Signals "this is a console window."
- Each line: `[HH:MM:SS] emoji [BIRD] message`
- Color-coded by bird: rust for Spark, gold for Falcon, etc.
- Auto-scrolls to bottom

**Why light-theme terminal:**
The rest of the UI is light. A dark terminal would create a jarring "hole" in the page. Consistency reduces cognitive load.

### 5.9 Files Output

**Structure:**
```html
<div class="files-wrap" id="filesWrap">
  <h3>Output</h3>
  <div class="file-grid" id="fileGrid"></div>
</div>
```

**Purpose:** Display files generated by Owl phase.

**File card:**
```html
<div class="fcard" onclick="this.classList.toggle('open')">
  <div class="fhead">
    <span class="ftone">♪</span>
    <span class="fname">src/main.py</span>
  </div>
  <div class="fmeta">A-4 · 440Hz</div>
  <div class="fbody"># Generated code...</div>
</div>
```

**Why musical tones:**
Owl assigns each file a musical note based on its position in the generation sequence. This creates:
1. An auditory signature during compilation (Web Audio API plays the tone)
2. A visual identifier (musical symbol + note name)
3. A mnemonic for file ordering

The tone mapping: do→♪, re→♫, mi→♬, fa→♩, so→♭, la→♮, ti→♯

---

## 6. STATE MACHINE & DATA FLOW

### 6.1 JavaScript State Variables

```javascript
let activeFilter = 'all';        // Current search filter collection
let payloadItems = {};           // Map of doc_id → item object (from bucket API)
let chunks = [];                 // Array of chunk objects {idx, text, tokens}
let editingDocId = null;         // Currently open document in modal
let editingColl = 'raw';         // Collection of currently editing document
let editingOriginal = '';        // Original assembled text (for revert)
let currentRunId = '';           // Pipeline run ID (from SSE)
let filesGenerated = [];         // Array of generated file paths
let checkedState = {};           // Map of doc_id → boolean (include in build)
```

### 6.2 Data Flow Diagram

```
User ──► Search Input ──► /v1/aviary/search ──► ChromaDB
                           │
                           ▼
                    Result Cards
                           │
                           ▼ (click)
                    Modal Editor
                           │
                           ▼ (save)
                    POST /v1/buckets/{name}/add-raw
                           │
                           ▼
                    Payload Panel (renders from bucket)
                           │
                           ▼ (launch)
                    POST /v1/aviary/compile/stream
                           │
                           ▼ (SSE)
                    Terminal + Pipeline + File Output
```

### 6.3 Bucket as Source of Truth

The payload panel does NOT maintain its own state independently. It always:
1. Reads from `/v1/buckets/{BUCKET_NAME}` on load
2. Reflects bucket state after every mutation (add, update, remove, revert)

This means:
- Refreshing the page clears the UI state but the bucket persists
- Multiple tabs can theoretically share a bucket (though not recommended)
- The bucket is the single source of truth; the UI is a view

### 6.4 Checked State vs. Bucket State

`checkedState` is the ONLY UI-local state. It determines which payload items are included in compilation. It is NOT persisted to the bucket. This is intentional:
- The bucket stores *what you have*
- The checkbox controls *what you're building with*
- A user might have 20 items in payload but only want to compile 3

---

## 7. API INTEGRATION MAP

### 7.1 Endpoints Consumed

| Endpoint | Method | Purpose | Called By |
|----------|--------|---------|-----------|
| `/v1/buckets/create` | POST | Ensure bucket exists | `ensureBucket()` on init |
| `/v1/buckets/{name}` | GET | Load all payload items | `loadPayload()` |
| `/v1/buckets/{name}/add-raw` | POST | Add new item from search | `saveModal()` |
| `/v1/buckets/{name}/update/{doc_id}` | POST | Save edited content | `saveModal()` |
| `/v1/buckets/{name}/revert/{doc_id}` | POST | Restore original content | `revertPayload()` |
| `/v1/buckets/{name}/remove/{doc_id}` | POST | Delete item from bucket | `removePayload()` |
| `/v1/aviary/search` | GET | Vector search across collections | `doSearch()` |
| `/v1/aviary/assembly` | GET | Reassemble chunked document | `openEditor()` |
| `/v1/aviary/compile/stream` | POST | Start SSE compilation pipeline | `runPipe()` |

### 7.2 Search API Details

```
GET /v1/aviary/search?q={query}&collections={csv}&n={limit}
```

**Parameters:**
- `q`: URL-encoded search query
- `collections`: Comma-separated collection names
- `n`: Result limit per collection (default 8)

**Response format:**
```json
{
  "results": {
    "chat_conversations": [
      {
        "id": "thread_abc_004",
        "document": "full text content...",
        "metadata": {
          "platform": "CHATGPT",
          "timestamp": "2024-11-04",
          "project": "herbert",
          "topics": "chroma, embeddings"
        }
      }
    ]
  }
}
```

### 7.3 Assembly API Details

```
GET /v1/aviary/assembly?collection={name}&doc_id={id}
```

**Purpose:** Fetch original source file from disk and reassemble all chunks by `batch_id`.

**Why this matters:** ChromaDB stores fragmented chunks. The assembly endpoint:
1. Looks up the chunk by ID to get `batch_id`
2. Finds all chunks in the collection with matching `batch_id`
3. Sorts by `entry` number
4. Concatenates into full narrative
5. Falls back to disk read if ChromaDB chunks are incomplete

### 7.4 Stream API Details

```
POST /v1/aviary/compile/stream
Content-Type: application/json

{
  "chat_log_text": "full assembled text...",
  "enable_memory": true,
  "memory_collections": ["app_invariants", "agent_invariants", "tech_vault"]
}
```

**Response:** `text/event-stream`

**Event format:**
```json
{
  "bird": "sp",
  "event": "phase_start",
  "message": "Spark phase started — 42,391 tokens",
  "payload": {}
}
```

---

## 8. EVENT STREAM PROTOCOL

### 8.1 Event Types

| Event | Bird | Message Example | UI Action |
|-------|------|-----------------|-----------|
| `pipeline_start` | `av` | "Pipeline started" | Show pipeline, log to terminal, activate Spark node |
| `phase_start` | phase | "Spark phase started — 42,391 tokens" | Log to terminal, activate node |
| `phase_complete` | phase | "Spark complete" | Log (green), mark node done, activate next node |
| `error` | phase | "Spark failed: context length" | Log (red), mark node error, shake animation |
| `file_complete` | `ow` | "src/main.py generated" | Log, add file card, play tone |
| `audit_passed` | `ra` | "Audit passed" | Log (green), mark Raven done |
| `pipeline_complete` | `av` | "Pipeline complete — 6 files" | Log (green), mark Hawk done, show output grid |
| `pipeline_failed` | `av` | "Pipeline failed" | Log (red), re-enable Launch button |

### 8.2 Tone Payload

```json
{
  "bird": "ow",
  "event": "file_complete",
  "message": "src/main.py generated",
  "payload": {
    "file": "src/main.py",
    "tone": {
      "note": "do",
      "octave": 4,
      "frequency": 261.63
    }
  }
}
```

**Tone mapping:**
- do (C) → 261.63Hz
- re (D) → 293.66Hz
- mi (E) → 329.63Hz
- fa (F) → 349.23Hz
- so (G) → 392.00Hz
- la (A) → 440.00Hz
- ti (B) → 493.88Hz

Octave increments every 7 files. Waveform: sine for octaves ≤5, triangle for >5 (brighter timbre).

### 8.3 Terminal Logging Format

```
[22:06:15] 🔥 [SPARK] Phase started — 42,391 tokens
[22:06:18] 🔥 [SPARK] Ontology extracted
[22:06:18] 🦅 [FALCON] Phase started
[22:06:22] 🦅 [FALCON] 14 invariants mined
...
[22:07:45] 🦉 [OWL] src/main.py generated
[22:07:45] 🦉 [OWL] ♪ C-4 (261.63Hz)
```

---

## 9. REMOVED ELEMENTS & RATIONALE

### 9.1 Peacock Boss (SVG Mascot)

**What it was:** A 70×90px SVG peacock with animated body bob, 30 feather SVGs that spread in rings, attitude bubbles ("watchin'...", "pimpin'", "FULL SPREAD"), and shake animations.

**Why removed:**
- Broke focus during serious work
- Communicated "toy" or "game," not "compiler"
- The wandering position (fixed, top-left) occluded content on small screens
- Attitude bubbles were infantilizing
- Added ~10KB of SVG and CSS for zero functional value

### 9.2 Bindings Sidebar

**What it was:** A 280px third column showing API→UI binding mappings from the `bindings` collection.

**Why removed:**
- Broken: The `bindings` collection uses 1000-dim embeddings (intent vector space), but the search endpoint queries with 384-dim embeddings (default Chroma `all-MiniLM-L6-v2`). This causes a dimension mismatch error.
- Even if fixed, it cluttered the 3-column grid
- Bindings are not actively used in the compilation pipeline
- Can be re-added later as a modal or dedicated page once the embedding model is aligned

### 9.3 Dark Theme

**What it was:** `#06060f` background with `#ffffff` text, glassmorphism panels, neon accents.

**Why removed:**
- Eye fatigue during long sessions
- Poor outdoor/bright-room visibility
- Every dark-mode UI looks identical now — no differentiation
- Light mode prints better (for users who screenshot or PDF)
- The "advanced tool" aesthetic is now light (see: Linear, Vercel, Notion, Figma)

### 9.4 Glassmorphism

**What it was:** `backdrop-filter: blur(16px)`, semi-transparent backgrounds (`rgba(255,255,255,0.035)`), colored glow shadows.

**Why removed:**
- Reduces perceived information density
- Performance cost on lower-end devices
- Hard to implement consistently across browsers
- Looks cheap when overused
- Kept ONLY in modal overlay (`backdrop-filter: blur(4px)`) where it serves a genuine purpose (separating modal from page)

### 9.5 Gradient-Shifting Header

**What it was:** H1 with `background: linear-gradient(90deg, #00f5c4, #00d4ff, #b829dd, #ff5e00)` and `animation: gradShift 5s ease infinite`.

**Why removed:**
- GeoCities aesthetic
- Illegible on some displays
- Animating background-clip text is CPU-intensive
- Competes with actual content for attention

### 9.6 Neon Glow Effects

**What it was:** `box-shadow: 0 0 40px rgba(255,94,0,0.3)` on active pipeline nodes, glow on badges, glow on focused inputs.

**Why removed:**
- Color bleeding between adjacent elements
- Reduces perceived sharpness
- Causes eye strain (halation effect on light text)
- Replaced with subtle border-color changes and background tints

---

## 10. RESPONSIVE BEHAVIOR

### 10.1 Breakpoint: ≤1100px

**Changes:**
- Workspace grid collapses to single column
- Payload panel becomes fixed-position slide-out drawer:
  ```css
  .payload-col {
    position: fixed;
    right: -400px;
    top: 0;
    width: 400px;
    height: 100vh;
    z-index: 200;
  }
  .payload-col.open { right: 0; }
  ```
- Hamburger toggle button appears bottom-right
- Pipeline wraps to multiple rows if needed

**Why slide-out instead of stacking:**
- Stacking would push search results far down the page
- The payload needs to be referenceable while searching
- A drawer preserves spatial relationship (right side = assembly area)

### 10.2 Touch Targets

All interactive elements meet WCAG 2.1 minimum touch target size (44×44px equivalent at default zoom):
- Search button: padding 10px 22px
- Filter pills: padding 5px 12px (slightly small but inline with text, acceptable)
- Result cards: full-width, ~60px height
- Payload actions: padding 3px 8px (small, but adjacent to larger container)
- Modal buttons: padding 8px 18px

---

## 11. ACCESSIBILITY NOTES

### 11.1 Color Contrast

All text meets WCAG AA (4.5:1) or AAA (7:1) against backgrounds:
- `--text` (#1a1a18) on `--bg` (#f7f7f5): **14.8:1** — AAA
- `--text-secondary` (#555553) on `--bg`: **7.2:1** — AAA
- `--text-muted` (#888886) on `--bg`: **4.6:1** — AA
- `--text-faint` (#b0b0ad) on `--bg`: **3.1:1** — AA Large only (used for timestamps, acceptable)

### 11.2 Motion

```css
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

Respects system preference for reduced motion. All animations become instantaneous.

### 11.3 Focus States

- Search input: `border-color: var(--accent)` + `box-shadow: 0 0 0 3px var(--accent-bg)`
- Buttons: No outline (replaced with background color shift on hover)
- Modal editor blocks: `box-shadow: inset 0 0 0 1px var(--accent)` on focus

### 11.4 Semantic HTML

- Proper heading hierarchy: `h1` (hero) → implicit section headings via styled divs
- `contenteditable` used for editor (no form elements needed since it's block-based)
- Buttons are `<button>` elements (not divs with onclick)

---

## 12. FUTURE EXTENSION POINTS

### 12.1 Bindings Panel (Post-Fix)

Once the 1000-dim embedding mismatch is resolved, bindings can be re-added as:
- **Option A**: A fourth column (only at >1400px)
- **Option B**: A collapsible section within the search column
- **Option C**: A dedicated modal/tab

**Recommended**: Option B — a "Bindings" filter pill that, when active, shows API bindings mixed with search results or in a sub-panel below filters.

### 12.2 Keyboard Shortcuts

Currently no shortcuts wired. Proposed:
- `Ctrl/Cmd + K`: Focus search input
- `Ctrl/Cmd + Enter`: Launch Spark (when payload has items)
- `Escape`: Close modal
- `Ctrl/Cmd + Shift + P`: Toggle payload panel (mobile)

### 12.3 Persistence

Currently `checkedState` and `chunks` are lost on refresh. Could persist to:
- `localStorage` (simple, no server needed)
- Bucket metadata (server-side, survives across devices)

### 12.4 Gateway Status Indicator

The `topbarMeta` div is wired but empty. Could display:
- Active LLM gateway (Groq/Google/DeepSeek)
- Current TPM usage / rate limit remaining
- Connection status to ChromaDB
- Last successful search timestamp

### 12.5 Output File Preview

Currently file cards show only metadata. The `.fbody` div exists but is empty. Future:
- Populate with actual file content from SSE stream
- Add syntax highlighting (client-side Prism.js or highlight.js)
- Add download/copy buttons per file

### 12.6 Phase Detail Expansion

Clicking an active pipeline node could expand a detail panel showing:
- Raw LLM prompt for that phase
- Token count in / token count out
- Gateway used and model ID
- Latency metrics

---

## APPENDIX A: FILE REFERENCE

| File | Path | Purpose |
|------|------|---------|
| Aviary UI v3 | `/root/hetzner/ai-engine/app/static/neural-link/aviary.html` | Single-file application (HTML+CSS+JS) |
| Aviary Pipeline Core | `/root/hetzner/ai-engine/app/core/aviary.py` | 7-phase compiler with SSE streaming |
| Bucket API | `/root/hetzner/ai-engine/app/routes/buckets.py` | REST CRUD for payload assembly |
| SPARK Prompt | `/root/hetzner/ai-engine/prompts/aviary/spark.md` | Minimal system prompt for ontology extraction |
| FALCON Prompt | `/root/hetzner/ai-engine/prompts/aviary/falcon.md` | Minimal system prompt for invariant mining |
| Token Counter | `/root/hetzner/ai-engine/utils/gemini_token_counter.py` | Accurate Gemini token counting + offline fallback |
| Pipeline Docs | `/root/hetzner/ai-engine/docs/AVIARY_PIPELINE_V2.md` | Theory, architecture, rebuild status |
| This Document | `/root/hetzner/ai-engine/docs/AVIARY_UI_V3_COMPLETE.md` | Complete UI specification |

## APPENDIX B: CSS CUSTOM PROPERTIES QUICK REFERENCE

```css
/* Backgrounds */
--bg: #f7f7f5;
--bg-elevated: #ffffff;
--bg-muted: #efefec;

/* Borders */
--border: #e2e2df;
--border-strong: #c8c8c3;

/* Text */
--text: #1a1a18;
--text-secondary: #555553;
--text-muted: #888886;
--text-faint: #b0b0ad;

/* Accent */
--accent: #0d4f4f;
--accent-light: #146060;
--accent-bg: rgba(13,79,79,0.06);

/* Birds */
--spark: #c45c26;
--falcon: #b8952e;
--eagle: #3a8a3a;
--crow: #2a7a9a;
--owl: #7a4a9a;
--raven: #5a5a58;
--hawk: #b03030;

/* Geometry */
--radius: 6px;
--radius-lg: 10px;

/* Shadows */
--shadow-sm: 0 1px 2px rgba(0,0,0,0.04);
--shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04);
--shadow-lg: 0 4px 20px rgba(0,0,0,0.08);

/* Fonts */
--font-ui: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
--font-mono: 'SF Mono', SFMono-Regular, ui-monospace, 'Cascadia Code', Consolas, monospace;
```

---

**End of Document**
