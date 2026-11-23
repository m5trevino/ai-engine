# PEACOCK Aviary — Design Brief for Expert Redesign

**Date:** 2026-05-01  
**System:** PEACOCK AI Engine v3  
**Component:** Aviary Pipeline UI  
**Current URL:** `https://chat.save-aichats.com/neural-link/aviary.html`  
**Status:** v3 deployed, functionally working, visually rejected by operator

---

## 1. WHAT THIS SYSTEM ACTUALLY IS

PEACOCK is an AI orchestration engine running on a Hetzner VPS. It has multiple subsystems. **Aviary is ONE workspace inside PEACOCK** — specifically, the "compiler workspace" where the operator transforms raw chat logs (months or years of AI conversations) into deployable software projects.

Think of it like this:
- **PEACOCK** = The factory
- **Aviary** = The assembly line where memory becomes code
- **Neural Link** = The chat interface (separate UI, already built)
- **Project Forge** = The project generation UI (separate, already built)

The operator has ~150,000 documents in ChromaDB vector databases. These are fragmented chat logs from ChatGPT, Claude, Gemini, and other platforms, going back years. They contain ideas, experiments, architecture discussions, debugging sessions, and project plans. The Aviary pipeline is how those conversations become actual files.

---

## 2. THE ARCHITECTURE (What the Designer Needs to Know)

### 2.1 The Data Layer

**ChromaDB Persistent Client** at `/root/chroma-unified/`

**9 Collections (~149,000 documents):**

| Collection | Count | What It Contains |
|------------|-------|------------------|
| `chat_conversations` | 26,124 | Full conversation threads. Rich metadata: platform, project, tags, summary, density score, confidence score. Layer 3 of the dendritic memory system. |
| `tech_vault` | 19,205 | Technical experiments, code snippets, architecture notes, API explorations. |
| `seed_vault` | 11,000 | Early ideas, prototypes, raw concepts before they became projects. |
| `case_files_vault` | 3,103 | Research, case studies, analytical documents. |
| `personal_vault` | 1,034 | Personal notes, reflections, non-technical journaling. |
| `app_invariants` | 1,820 | Layer 2 structural rules the engine has learned about application architecture. Metadata: law_id, category, confidence (0-1), version. |
| `agent_invariants` | 235 | Layer 1 behavioral rules for AI agents. Communication protocols, error handling patterns. |
| `bindings` | 86,665 | API-to-UI invariant mappings. Parsed from OpenAPI specs. Path → HTTP method → intent → UI invariant. **Currently BROKEN in UI** (1000-dim vs 384-dim embedding mismatch). |

**Embedding Model:** `all-MiniLM-L6-v2` (384-dimensional) for all collections except `bindings` which uses a custom 1000-dim intent vector space.

**Document ID Convention:** `{thread_base}_{entry_num}` — e.g., `chatgpt_2024_03_abc123_004`. This allows thread reconstruction by grouping on `batch_id`.

**Original Source Files:** Live on disk at `/home/flintx/ai-chats/` (Markdown files). ChromaDB stores chunked fragments. The UI can reassemble full narratives via the assembly endpoint.

### 2.2 The Compute Layer

**AI Gateways (4 pools, 21 total keys):**

| Gateway | Keys | Models | Role |
|---------|------|--------|------|
| Groq | 16 | Llama 3.3 70B, Mixtral, etc. | Primary. Hard TPM limit: 6,000 tokens/minute. Fast, cheap. |
| Google | 3 | Gemini 1.5 Pro (1M context), Gemini Flash | Overflow / large context. Used when payload >100K tokens. |
| DeepSeek | 1 | DeepSeek V3 | Fallback |
| Mistral | 1 | Mistral Large | Fallback |

**Routing Logic (in `_phase_spark`):**
- Count tokens in full prompt
- If ≤100K tokens → Groq Llama 3.3 70B
- If >100K tokens → Google Gemini 1.5 Pro (can handle ~1M context)
- Temperature locked to 0.0 (deterministic, no creativity)

**Runtime:** Python 3.12, FastAPI, systemd service on Ubuntu VPS.

### 2.3 The Memory Integration

Before compilation, the pipeline queries PEACOCK Unified (localhost:8000) for relevant context:
- `app_invariants` → architectural constraints
- `agent_invariants` → behavioral patterns  
- `tech_vault` → implementation patterns

This context is injected into prompts (prompt-injection approach, not tool calling).

### 2.4 The 7-Phase Pipeline (The Birds)

Each bird is an **isolated LLM call**. Compartmentalization is absolute. Bird N sees ONLY the output of Bird N-1. No project-wide context. No peeking ahead.

| Phase | Bird | Input | Output | What It Actually Does |
|-------|------|-------|--------|----------------------|
| 1 | **SPARK** | Assembled chat log text (up to ~1M tokens) | Structured project ontology + task DAG | Ingests the ENTIRE compiled payload. Validates DB metadata against actual conversation content. Extracts: technologies mentioned, entities, topics, decisions made, action items. Not a summarizer — a cognitive architect. Emits token count for routing. |
| 2 | **FALCON** | SPARK's ontology | Structural invariants | Mines patterns from the ontology. Produces "laws" that constrain the architecture. Uses few-shot examples showing ONTOLOGY → INVARIANTS pattern. Completion starter: `### STRUCTURAL INVARIANTS` |
| 3 | **EAGLE** | FALCON's invariants | File tree + dependencies + architecture decisions | Designs the complete project structure. What files exist, what depends on what, which frameworks, which patterns. |
| 4 | **CROW** | EAGLE's architecture | Code for each file | Generates actual source code. File-by-file. Uses heredoc bash block format: `cat > path << 'EOF'`...`EOF` |
| 5 | **OWL** | CROW's code blocks | Validated files + musical tones | Receives code, validates syntax, assigns musical note to each file based on generation order. Plays tone via Web Audio API in browser. |
| 6 | **RAVEN** | OWL's files | Audit report + retry signal | Quality control loop. Checks against invariants, spots inconsistencies. If fail → sends back to OWL (max 2 retries). |
| 7 | **HAWK** | RAVEN's audit | Final package: deploy.sh + README + manifest | Final validation. Assembles deployable artifact. |

**Total pipeline latency:** 2–8 minutes depending on payload size, gateway load, and retry count.

---

## 3. THE USER (Operator Profile)

This is NOT a consumer product. There is ONE user — the operator who built it.

**User characteristics:**
- Technical: writes Python, understands LLM tokenization, vector databases, systemd
- Has YEARS of chat logs across multiple AI platforms
- Treats conversations as primary source material — ChromaDB metadata is scaffolding, the conversation TEXT is truth
- Believes LLMs are conditional probability distributions, not assistants
- Rejects "assistant" framing — wants statistical instruments, not chatbots
- Values compartmentalization, determinism (temperature=0), and token-aware design
- Willing to read dense technical documentation
- Wants the UI to feel as sophisticated as the theory behind it
- Rejected the previous UI as "AOL 3.0," "1993," "garbage"

**Primary workflow:**
1. Has an idea for a project or needs to resurrect an old one
2. Searches memory vaults for relevant conversations
3. Assembles 3–20 documents into a payload
4. Optionally edits documents in modal (fixes, condenses, removes noise)
5. Chunks if payload is large
6. Launches pipeline
7. Monitors terminal for 2–8 minutes
8. Reviews output files
9. Downloads/deploys generated code

**Secondary workflow:**
1. Browses invariants to understand architectural constraints
2. Searches bindings for API→UI mappings (currently broken)
3. Reviews past pipeline runs (not yet implemented in UI)

---

## 4. THE CURRENT UI (v3) — WHAT EXISTS NOW

### 4.1 Layout

```
┌─────────────────────────────────────────────────────────────┐
│ PEACOCK Aviary                              [topbar]        │
├─────────────────────────────────────────────────────────────┤
│ Build from memory.                                          │
│ Search your vaults, assemble a payload, and run... [hero]   │
├───────────────────────────────┬─────────────────────────────┤
│ Search memory vaults... [    ]│ Payload                    │
│ [All] [Conversations] [Tech]  │ ┌────────────────────────┐│
│                               │ │ doc_id_abc... [Edit]   ││
│ Result Card                   │ │ 1,234 tokens · raw     ││
│ Platform badge · Date         │ │ [✓] Include in build   ││
│ Preview text line...          │ ├────────────────────────┤│
│ project · topics              │ │ doc_id_def... [Edit]   ││
│                               │ │ 5,678 tokens · tech    ││
│ Result Card                   │ │ [✓] Include in build   ││
│ ...                           │ └────────────────────────┘│
│                               │ 6,912 tokens · 12,345 chars│
│                               │ [Create Chunks]            │
│                               │ [Launch Spark]             │
└───────────────────────────────┴─────────────────────────────┘

        🔥 → 🦅 → 🦅 → 🐦‍⬛ → 🦉 → 🐦‍⬛ → 🦅
       Spark  Falcon Eagle Crow  Owl  Raven Hawk
       [pipeline — hidden until compile]

┌─────────────────────────────────────────────────────────────┐
│ ● ● ●  peacock.log                                         │
│ [22:06:15] 🔥 [SPARK] Phase started — 42,391 tokens        │
│ [22:06:18] 🔥 [SPARK] Ontology extracted                   │
│ ...                                                         │
└─────────────────────────────────────────────────────────────┘

Output
┌─────────────┐ ┌─────────────┐
│ ♪ main.py   │ │ ♫ utils.py  │
│ A-4 · 440Hz │ │ C-5 · 523Hz │
│ [click to   │ │ [click to   │
│  expand]    │ │  expand]    │
└─────────────┘ └─────────────┘
```

### 4.2 Visual Design (v3)

- **Light theme**: Off-white `#f7f7f5` background, near-black `#1a1a18` text
- **Single accent**: Deep teal `#0d4f4f` — buttons, active states, focus rings
- **Muted bird colors**: Rust, ochre, forest, dusty cerulean, dusty purple, grey, brick red
- **Typography**: System sans for UI, SF Mono for all data
- **No animations** except error shake and terminal line fade-in
- **No mascot** (removed)
- **No glassmorphism** (removed)
- **No neon** (removed)

### 4.3 What's Working

- Search across 5 collections works
- Payload assembly via bucket API works
- Modal editor with block-based editing works
- Chunking works
- Full pipeline execution via SSE works
- Terminal logging with bird-color coding works
- File output with musical tones works
- Responsive slide-out drawer for mobile works

### 4.4 What's Broken

- **Bindings sidebar**: Removed entirely. 1000-dim vs 384-dim embedding mismatch causes query failures.
- **No persistent state**: Checked items, chunk state lost on refresh
- **File output content**: File cards show metadata but body is empty (content not streamed to UI yet)
- **No keyboard shortcuts**: Everything is mouse-driven
- **No gateway status**: Operator can't see which LLM is being used, TPM remaining, or latency
- **No run history**: Can't see past compilations
- **No invariant browser**: Can't explore the 2,055 invariants directly in UI
- **Eagle/Crow/Owl/Raven/Hawk prompts**: Not rebuilt with statistical instrument theory (only SPARK and FALCON are modern)

---

## 5. WHAT THE OPERATOR WANTS (Redesign Goals)

### 5.1 From Direct Feedback

- **"Not AOL 3.0"**: Rejected dark glassmorphism, neon, gradients, animations, mascots
- **"Needs staging"**: Information should have clear hierarchy. Not everything visible at once.
- **"Proper emphasis"**: Important things should LOOK important. Trivial things should recede.
- **"Reflects the ambition"**: The theory behind this system is sophisticated. The UI should feel sophisticated.
- **"Logical flow"**: The interface should guide the operator through the workflow, not dump everything on screen

### 5.2 Implied Needs (From Observing Usage)

- **Token awareness**: The operator thinks in tokens. Token counts should be prominent, accurate, and update in real time.
- **Gateway visibility**: Knowing WHICH model is running and HOW MUCH headroom remains is operational critical data.
- **Source fidelity**: Being able to see the ORIGINAL conversation (not just ChromaDB chunks) is essential. The assembly endpoint exists for this reason.
- **Edit control**: The operator frequently wants to clean up conversation text before feeding it to the pipeline (remove "Sure! I'd be happy to help!" fluff).
- **Phase visibility**: During a 5-minute compile, the operator wants to know EXACTLY which bird is working, what it's doing, and how long it's taking.
- **Output confidence**: When files are generated, the operator wants to know if they passed audit, what invariants were applied, and whether Raven had to retry.

### 5.3 What "Better" Means

| Dimension | Current (v3) | Target |
|-----------|-------------|--------|
| **Density** | Medium, some waste | High — operator wants information, not whitespace worship |
| **Hierarchy** | Flat — everything visible | Staged — progressive disclosure based on workflow phase |
| **Feedback** | Terminal logs only | Rich phase indicators, timing, model info, token burn |
| **Control** | Checkbox on/off | Granular inclusion, preview before compile, abort mid-flight |
| **Recovery** | None — refresh loses state | Persistent payload, run history, draft saves |
| **Browsing** | Search-only | Browse invariants, browse vaults by project/date, thread view |
| **Output** | File list with empty bodies | Full file preview, diff vs previous run, deploy button |

---

## 6. THE WORKFLOW (What a Designer Must Design For)

### 6.1 Phase 0: Discovery

The operator is NOT always searching for a specific term. Sometimes they:
- Browse recent conversations
- Look at all conversations tagged with a project
- Explore invariants to understand current architectural constraints
- Review what was generated last time

**Current UI gap:** No browse mode. Only search.

### 6.2 Phase 1: Search

Operator enters a query. System performs vector search across selected collections.

**What the operator needs to see:**
- Result relevance score (distance from query vector)
- Which collection each result came from
- How old it is
- Which AI platform generated it
- What project it belongs to
- Whether it's been used in a previous compile
- A meaningful preview (not just first 90 chars — maybe the most relevant passage)

**Current gap:** No relevance score. No "used before" indicator. Preview is just first 90 characters.

### 6.3 Phase 2: Assembly

Operator clicks results to add to payload. Each addition is a decision.

**What the operator needs:**
- One-click add (not just open-editor-then-save)
- See running token total as items are added
- Reorder items (sequence matters — SPARK reads them in order)
- Collapse/expand items in payload
- See duplicate detection (same thread added twice)
- Auto-suggest related documents ("You added X, Y is also from that thread")

**Current gap:** No reordering. No duplicates check. No auto-suggest. No quick-add.

### 6.4 Phase 3: Edit

Operator opens a document. System assembles all chunks from disk/ChromaDB.

**What the operator needs:**
- Side-by-side: original vs edited (diff view)
- Search within the document
- Find-and-replace
- See token delta (original vs current)
- Mark sections for exclusion (not just edit — "skip this paragraph")
- Highlight passages that will be heavily tokenized (long code blocks, URLs)

**Current gap:** No diff. No find/replace. No exclusion markers.

### 6.5 Phase 4: Chunk Review

If payload > ~4K tokens, operator chunks it.

**What the operator needs:**
- Visual chunk boundaries
- Per-chunk token count
- Ability to merge/split chunks manually
- See which chunks will route to Groq vs Gemini
- Reorder chunks

**Current gap:** No manual split/merge. No gateway routing preview.

### 6.6 Phase 5: Compile

Operator launches. 2–8 minute wait.

**What the operator needs:**
- Clear "in progress" state that can't be accidentally dismissed
- Live token burn count
- Which gateway/model is currently active
- Time elapsed / estimated time remaining
- Per-phase output preview (not just "Spark complete" — show the ACTUAL ontology)
- Ability to abort
- If error: clear diagnosis + suggested fix

**Current gap:** No gateway indicator. No time estimate. No phase output preview. No abort.

### 6.7 Phase 6: Review

Files generated. Operator reviews.

**What the operator needs:**
- File tree view (not just grid)
- Syntax highlighted code preview
- Which invariants were applied to each file
- Raven audit results per file
- Diff from previous run (if recompiling same payload)
- Deploy button (triggers deploy.sh)
- Download as zip

**Current gap:** No syntax highlight. No tree view. No audit results. No diff. No deploy.

---

## 7. INFORMATION ARCHITECTURE (Recommended Restructure)

The current UI is a single page with everything visible. A better approach:

### 7.1 Proposed Navigation Structure

```
Aviary Workspace
├── Discover
│   ├── Search (current main view)
│   ├── Browse by Project
│   ├── Browse by Date
│   └── Browse Invariants
├── Assemble
│   ├── Payload Builder (drag-drop, reorder)
│   ├── Chunk Review
│   └── Edit Document (full-screen editor)
├── Compile
│   ├── Launch Config (gateway, model, memory toggles)
│   ├── Live Monitor (terminal + phase detail + timing)
│   └── Run History
└── Output
    ├── File Browser (tree + preview)
    ├── Audit Report
    ├── Deploy
    └── Compare Runs
```

### 7.2 Single-Page Alternative (If Tabs Are Undesirable)

If the operator prefers a single-page flow (no navigation), use a **stepped wizard** or **scroll-linked sections**:

```
[Sticky progress bar: Discover → Assemble → Compile → Output]

Section 1: DISCOVER (search + browse)
Section 2: ASSEMBLE (payload builder)
Section 3: COMPILE (launch + monitor)
Section 4: OUTPUT (files + deploy)
```

The progress bar advances as the operator completes each phase. Sections below the current phase are collapsed or dimmed.

---

## 8. DATA MODELS (For the Designer)

### 8.1 Search Result

```typescript
interface SearchResult {
  id: string;                    // "chatgpt_2024_03_abc123_004"
  document: string;              // Full text (may be truncated in response)
  metadata: {
    file: string;                // "/home/flintx/ai-chats/2024-03/project.md"
    timestamp: string;           // "2024-11-04"
    platform: string;            // "CHATGPT" | "CLAUDE" | "GEMINI" | ...
    project: string;             // "herbert" | "unknown"
    vault: string;               // "tech_vault" | "personal_vault" | ...
    entry: string;               // "004" (sequence in thread)
    has_code_blocks: string;     // "true" | "false"
    idea_maturity: string;       // "exploring" | "developing" | "mature"
    topics: string;              // "chroma, embeddings, fastapi"
    batch_id: string;            // "thread_base_abc123" (for assembly)
  };
  distance?: number;             // Vector distance (lower = more relevant)
}
```

### 8.2 Bucket Item (Payload Entry)

```typescript
interface BucketItem {
  doc_id: string;
  collection: string;            // Source collection
  content: string;               // Current text (may be edited)
  original_content: string;      // Original assembled text
  edited: boolean;
  added_at: string;              // ISO timestamp
}
```

### 8.3 Pipeline Event (SSE)

```typescript
interface PipelineEvent {
  bird: "sp" | "fa" | "ea" | "cr" | "ow" | "ra" | "ha" | "av";
  event: "pipeline_start" | "phase_start" | "phase_complete" | 
         "error" | "file_complete" | "audit_passed" | 
         "pipeline_complete" | "pipeline_failed";
  message: string;
  payload?: {
    file?: string;               // For file_complete
    tone?: {
      note: "do" | "re" | "mi" | "fa" | "so" | "la" | "ti";
      octave: number;
      frequency: number;
    };
  };
}
```

### 8.4 Generated File

```typescript
interface GeneratedFile {
  path: string;                  // "src/main.py"
  content: string;               // Full source code
  tone: {
    note: string;
    octave: number;
    frequency: number;
  };
  audit_passed: boolean;
  retries: number;               // How many Raven retries
}
```

---

## 9. TECHNICAL CONSTRAINTS

### 9.1 What You CAN Change

- Everything in `aviary.html` (single file, inline CSS/JS)
- The CSS custom properties, colors, layout, grid, animations
- The DOM structure
- The JavaScript state management
- Which API endpoints are called and when
- The information architecture (tabs, wizard, single-page, etc.)

### 9.2 What You CANNOT Change (Without Backend Work)

- **No authentication** — the API endpoints are wide open (`allow_origins=["*"]`)
- **No WebSocket** — pipeline uses SSE (`text/event-stream`), not WebSockets
- **No file system access from browser** — files are generated server-side, streamed as text
- **Embedding dimension mismatch** — `bindings` collection cannot be queried with the standard search endpoint without backend changes
- **Token counter is server-side** — the accurate Gemini token counter runs in Python, not JS
- **Gateway routing is server-side** — the decision to use Groq vs Gemini happens in `_phase_spark`, not the browser

### 9.3 What Would Require Backend Work

| Feature | Backend Change Needed |
|---------|----------------------|
| Bindings sidebar | Fix embedding dimension mismatch OR create separate query endpoint |
| Syntax highlighting in output | None — can use client-side Prism.js/highlight.js |
| File deploy button | Add `/v1/projects/{id}/deploy` endpoint (already exists in Project Forge, needs Aviary integration) |
| Run history | Add database table or file-based persistence for pipeline runs |
| Relevance scores in search | Already returned by ChromaDB, just need to expose in API response |
| Abort mid-compilation | Add cancellation token to async pipeline generator |
| Per-phase output preview | Stream intermediate outputs (ontology, invariants, file tree) as additional SSE events |
| Auto-suggest related docs | Add "more like this" endpoint using ChromaDB query |

---

## 10. COMPETITIVE / INSPIRATIONAL REFERENCES

The operator has NOT explicitly requested any of these, but these are the kinds of interfaces that communicate "sophisticated tool for sophisticated users":

- **Linear** — Light theme, density without clutter, keyboard-first, command palette
- **Vercel Dashboard** — Deployment pipeline visualization, clean staging, live logs
- **GitHub Actions** — Workflow visualization with step-by-step status
- **Figma** — Canvas + sidebar + properties panel (if going multi-pane)
- **Observable** — Notebook-style progressive execution (if going stepped)
- **Warp Terminal** — Modern terminal aesthetics (if keeping terminal prominent)
- **Raycast** — Command palette, keyboard-driven, fast

**What NOT to reference:**
- ChatGPT/Claude interfaces (the operator explicitly rejects "assistant" framing)
- Dark-themed "hacker" UIs (rejected)
- No-code builders with drag-and-drop canvas (too consumer)
- Dashboards with big numbers and charts (not a metrics tool)

---

## 11. SUCCESS CRITERIA FOR REDESIGN

The operator will judge the redesign on:

1. **"Does it feel advanced?"** — Not gimmicky, not toy-like. Confident, precise, editorial.
2. **"Can I assemble a payload in under 60 seconds?"** — From search to launch. Current flow takes 2–3 minutes.
3. **"Do I know what's happening during compile?"** — Rich feedback, not just a scrolling terminal.
4. **"Can I trust the output?"** — Clear audit trail, invariant visibility, retry indication.
5. **"Is it readable after 30 minutes?"** — No eye fatigue. Good contrast, good type.
6. **"Does it respect the theory?"** — The UI should communicate compartmentalization, determinism, and token-awareness. It should feel like operating a statistical compiler, not chatting with an AI.

---

## 12. DELIVERABLES EXPECTED

The designer should produce:

1. **Information Architecture Diagram** — How the sections relate, navigation model
2. **Wireframes (Low-Fi)** — Layout for each major state/screen
3. **High-Fidelity Mockups** — Key screens at desktop and mobile breakpoints
4. **Design System Spec** — Colors, typography, spacing, components (can reuse or replace current CSS tokens)
5. **Interaction Spec** — Transitions, animations (if any), hover states, keyboard flows
6. **Prototype (Optional)** — Clickable Figma or HTML prototype

---

**End of Brief**
