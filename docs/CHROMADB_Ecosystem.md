# PEACOCK ChromaDB Ecosystem — Complete Overview

**Date:** 2026-05-01  
**Version:** 3.0  
**Author:** Operator Documentation  
**Scope:** All ChromaDB instances, collections, schemas, ingestion pipelines, and query patterns across the PEACOCK system.

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [The Three ChromaDB Instances](#2-the-three-chromadb-instances)
3. [The Unified Database (`/root/chroma-unified/`)](#3-the-unified-database-rootchroma-unified)
4. [Collection Schemas in Detail](#4-collection-schemas-in-detail)
5. [Document ID Conventions & Threading](#5-document-id-conventions--threading)
6. [The Ingestion Pipeline](#6-the-ingestion-pipeline)
7. [The Invariant Mining Pipeline](#7-the-invariant-mining-pipeline)
8. [Query Patterns & APIs](#8-query-patterns--apis)
9. [Embedding Strategy](#9-embedding-strategy)
10. [Physical Storage & Maintenance](#10-physical-storage--maintenance)

---

## 1. EXECUTIVE SUMMARY

PEACOCK maintains **three separate ChromaDB persistent instances** on a single Hetzner VPS. Together they store approximately **236,000 vector documents** across **10+ collections**.

| Instance | Path | Port | Documents | Purpose |
|----------|------|------|-----------|---------|
| **Unified** | `/root/chroma-unified/` | 8000 | ~149,000 | Primary memory system — vaults, conversations, invariants, bindings |
| **Bindings** | `/root/flintx/chroma_db/` | 7878 | 86,665 | Dedicated API→UI binding database (1000-dim vectors) |
| **Dendritic** | `/root/hetzner/herbert/liquid-semiotic/dendritic/data/chroma_db/` | 8001 | ~27,000 | Original Herbert 3-layer memory system |

**Key architectural principle:** Documents are stored as **chunked fragments** in ChromaDB. The original source files live on disk at `/home/flintx/ai-chats/`. Thread reconstruction is performed at query time by grouping chunks via `batch_id` and sorting by `entry` number.

**Embedding model:** `all-MiniLM-L6-v2` (384-dimensional) for all collections **except** `bindings`, which uses a custom 1000-dimensional intent vector space.

---

## 2. THE THREE CHromaDB INSTANCES

### 2.1 Unified Database — Primary Memory

**Code:** `/root/peacock_unified.py`  
**Path:** `/root/chroma-unified/`  
**Port:** 8000  
**Service:** `peacock-unified.service`  
**Embedding Function:** `all-MiniLM-L6-v2` (384-dim)

This is the main memory system. It powers `herbert.save-aichats.com` and `skillz.save-aichats.com` via Caddy reverse proxy. All vaults, invariants, and conversations live here.

**Collections (9 total):**

| Collection | Count | Description |
|------------|-------|-------------|
| `bindings` | 86,665 | API→UI mappings (⚠️ 1000-dim, mismatched with unified's 384-dim) |
| `chat_conversations` | 26,124 | Layer 3 — full conversations with rich metadata |
| `tech_vault` | 19,205 | Technical knowledge, code, experiments |
| `seed_vault` | 11,000 | Early ideas and prototypes |
| `case_files_vault` | 3,103 | Research, case studies, analysis |
| `app_invariants` | 1,820 | Layer 2 — app architecture laws |
| `personal_vault` | 1,034 | Personal notes, reflections |
| `agent_invariants` | 235 | Layer 1 — agent framework laws |
| `codebase_vault` | varies | Analyzed codebases and architecture docs |

**How it's initialized:**
```python
import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="/root/chroma-unified")
EF = embedding_functions.DefaultEmbeddingFunction()  # all-MiniLM-L6-v2, 384-dim

# All collections are auto-created on startup if missing
for coll_name in COLLECTIONS.keys():
    try:
        client.get_collection(coll_name, embedding_function=EF)
    except Exception:
        client.create_collection(coll_name, embedding_function=EF)
```

**Note on `bindings` in unified:** The bindings collection exists in unified with the SAME 1000-dim embeddings as the standalone binding DB. However, unified always uses the 384-dim embedding function. This causes `InvalidArgumentError` whenever unified attempts semantic search on bindings. The bindings collection in unified is effectively **broken for text-based search** but works for metadata filtering (`get()` with `where` clauses).

---

### 2.2 Binding Database — Intent Vector Space

**Code:** `/root/flintx/peacock_api.py`  
**Path:** `/root/flintx/chroma_db/`  
**Port:** 7878  
**Service:** `peacock-bindings.service`  
**Embedding:** Custom 1000-dim sparse one-hot intent vectors

This is a specialized database for API→UI invariant lookups. It uses a **programmatic embedding strategy** (not a neural model). Each binding's 1000-dim vector encodes:
- Intent category (one of 35 hardcoded intents)
- HTTP method type
- Path depth and nesting
- Resource type
- Parameter count
- Summary length

**Why 1000 dimensions?** The intent space is categorical, not semantic. A 384-dim sentence embedding would cluster "create user" near "create file" — which is semantically correct but operationally wrong. The 1000-dim space guarantees that `RESOURCE_CREATION` and `AUTHENTICATION` are orthogonal, even if their natural language descriptions are similar.

**How it's queried:**
```python
# peacock_api.py — does NOT use an embedding function
def build_intent_vector(intent: str) -> List[float]:
    vec = [0.0] * 1000
    if intent in INTENTS:
        vec[INTENTS.index(intent)] = 1.0
    else:
        vec[hash(intent) % 50] = 1.0
    return vec

# Search by intent vector + metadata filter
collection.query(
    query_embeddings=[build_intent_vector("FILE_SELECTION")],
    n_results=10,
    where={"intent": "FILE_SELECTION"},
    include=["documents", "metadatas", "distances"]
)
```

**Standalone access:**
- API: `https://peacock.save-aichats.com/search?intent=FILE_SELECTION&n=10`
- Web UI: `https://peacock.save-aichats.com/app`
- CLI: `python3 /root/flintx/peacock_cli.py --intent FILE_SELECTION`

**Full details in:** `BINDINGS_HowTo.md` (separate document)

---

### 2.3 Dendritic Database — Original Herbert

**Code:** `/root/hetzner/herbert/liquid-semiotic/dendritic/herbert_v2.py`  
**Path:** `/root/hetzner/herbert/liquid-semiotic/dendritic/data/chroma_db/`  
**Port:** 8001  
**Service:** `herbert.service`  
**Status:** Running but NOT exposed via Caddy

The original 3-layer dendritic memory system:
- `dendritic_layer1_agent_invariants`
- `dendritic_layer2_app_invariants`
- `dendritic_layer3_chat_conversations`

Features query expansion, stopword removal, confidence/density boosting, and `where` filters. This is the **legacy** system — Peacock Unified (port 8000) superseded it. The Caddy config routes `herbert.save-aichats.com` to Unified, not Herbert v2.

---

## 3. THE UNIFIED DATABASE (`/root/chroma-unified/`)

### 3.1 Physical Storage

```
/root/chroma-unified/
├── chroma.sqlite3              # 1.1 GB — main metadata & vector index
├── 04f1e7ce-.../              # segment directories (HNSW index shards)
├── 07d1e6d3-.../
├── 17f140a3-.../
├── 21a9d2ea-.../
├── 3ac443d4-.../
├── 4500756c-.../
├── a2a2c574-.../
├── cfb7553a-.../
└── e213731f-.../
```

SQLite schema:
```sql
SELECT name, dimension FROM collections;
-- agent_invariants    | 384
-- app_invariants      | 384
-- chat_conversations  | 384
-- tech_vault          | 384
-- seed_vault          | 384
-- case_files_vault    | 384
-- personal_vault      | 384
-- bindings            | 1000  ← mismatch
-- codebase_vault      | 384
```

### 3.2 Collection Registration

```python
# peacock_unified.py
COLLECTIONS = {
    "agent_invariants":    {"label": "Agent Invariants",    "icon": "🧬", "desc": "Layer 1 — agent framework laws"},
    "app_invariants":      {"label": "App Invariants",      "icon": "🏗️", "desc": "Layer 2 — application architecture"},
    "chat_conversations":  {"label": "Chat Conversations",  "icon": "💬", "desc": "Layer 3 — conversation archaeology"},
    "tech_vault":          {"label": "Tech Vault",          "icon": "⚙️", "desc": "Technical knowledge & experiments"},
    "seed_vault":          {"label": "Seed Vault",          "icon": "🌱", "desc": "Early ideas & prototypes"},
    "case_files_vault":    {"label": "Case Files",          "icon": "📁", "desc": "Research & case studies"},
    "personal_vault":      {"label": "Personal Vault",      "icon": "🔒", "desc": "Personal notes & reflections"},
    "bindings":            {"label": "API Bindings",        "icon": "🔗", "desc": "API → UI component mappings"},
    "codebase_vault":      {"label": "Codebase Vault",      "icon": "🧩", "desc": "Analyzed codebases & architecture docs"},
}
```

---

## 4. COLLECTION SCHEMAS IN DETAIL

### 4.1 Vault Collections (`tech_vault`, `seed_vault`, `case_files_vault`, `personal_vault`)

**Document text:** Chunked fragments of markdown chat logs (typically 500–2000 chars per chunk).

**Metadata schema:**
```python
{
    "file": "/home/flintx/ai-chats/2024/03/herbert-refactor.md",
    "timestamp": "2024-11-04",
    "platform": "CHATGPT",           # CHATGPT | CLAUDE | GEMINI | ...
    "project": "herbert",            # Project name or "unknown"
    "vault": "tech_vault",           # Which vault this belongs to
    "entry": "004",                  # Sequence number in source file
    "has_code_blocks": "true",       # "true" | "false"
    "idea_maturity": "exploring",    # exploring | developing | mature
    "topics": "chroma, embeddings",  # Comma-separated topics
    "batch_id": "chatgpt_2024_03_abc123",  # Thread grouping key
}
```

**Ingestion flow:**
1. Raw markdown files at `/home/flintx/ai-chats/`
2. `dendritic_diamond_miner.py` / `build_dossier.py` chunks files into fragments
3. Each fragment gets metadata extracted (platform from filename, timestamp from frontmatter, etc.)
4. Fragments are upserted to ChromaDB with `batch_id` linking them to source file

**Query patterns:**
```python
# Vector search across all vaults
coll.query(query_texts=["fastapi chromadb setup"], n_results=10)

# Metadata-filtered search
coll.query(
    query_texts=["authentication pattern"],
    n_results=10,
    where={"platform": "CLAUDE", "has_code_blocks": "true"}
)

# Browse by project (no vector search needed)
coll.get(where={"project": "herbert"}, limit=100)
```

---

### 4.2 `chat_conversations` — Layer 3

**Document text:** Same chunked fragments as vaults, but with **richer metadata**.

**Metadata schema:**
```python
{
    "file": "/home/flintx/ai-chats/2024/11/project-x.md",
    "timestamp": "2024-11-04",
    "platform": "CHATGPT",
    "project": "project-x",
    "vault": "chat_conversations",
    "entry": "007",
    "has_code_blocks": "true",
    "idea_maturity": "mature",
    "topics": "fastapi, pydantic, validation",
    "batch_id": "chatgpt_2024_11_project_x",
    # Layer 3 specific fields:
    "tags": "architecture, database, migration",
    "summary": "Discussion of database schema migration strategy",
    "density": 0.85,           # 0-1, information density score
    "confidence": 0.92,        # 0-1, pattern confidence score
}
```

**Why separate from vaults?** Chat conversations are processed through the dendritic diamond miner which extracts confidence and density scores. Not all vault documents have these scores.

---

### 4.3 `app_invariants` — Layer 2

**Document text:** Structured invariant statements (single sentences or short paragraphs).

**Metadata schema:**
```python
{
    "law_id": "16cf46817d4a768a",   # Unique hash identifier
    "layer": "layer2_app_invariants",
    "category": "communication_protocol",  # communication_protocol | bramble | error_handling | ...
    "confidence": 0.85,             # 0-1
    "version": "v3",
    "source": "chat_conversations",  # Which collection this was mined from
}
```

**Example document:**
```
All inter-agent communication MUST include a trace_id header. Failure to include trace_id results in silent rejection with 400 Bad Request.
```

**How they're created:**
1. `dendritic_diamond_miner.py` analyzes chat conversations for recurring patterns
2. Patterns are extracted as invariant statements
3. Each invariant gets a `law_id` (hash of statement text)
4. Confidence score derived from frequency of pattern occurrence

---

### 4.4 `agent_invariants` — Layer 1

**Document text:** Agent behavioral rules and framework laws.

**Metadata schema:**
```python
{
    "law_id": "a3f9e2b1c4d56789",
    "layer": "layer1_agent_invariants",
    "category": "communication_protocol",
    "confidence": 0.91,
    "version": "v3",
    "source": "agent_invariants",
}
```

**Example document:**
```
When an agent encounters an unknown tool, it MUST NOT hallucinate the tool's output. It MUST return a TOOL_NOT_FOUND error and request clarification from the operator.
```

**Count:** Only 235 — these are high-confidence, manually curated or heavily validated rules.

---

### 4.5 `bindings` — API→UI Mappings

**Document text:** Concatenated API metadata:
```
METHOD:POST PATH:/api/v1/itemusages Retrieves item usages INTENT:RESOURCE_CREATION Create Api form with validation REST_CREATE_NESTED
```

**Metadata schema:**
```python
{
    "intent": "RESOURCE_CREATION",
    "method": "POST",
    "path": "/api/v1/itemusages",
    "ui_invariant": "Create Api form with validation",
    "source": "openapi_spec",
}
```

**Dimension:** 1000 (see BINDINGS_HowTo.md for full details)

**⚠️ Critical Issue:** Cannot be semantically searched through unified (384-dim mismatch). Must use standalone API on port 7878 or metadata-only `get()` queries.

---

### 4.6 `codebase_vault`

**Document text:** Analyzed codebase fragments (function signatures, class definitions, architecture notes).

**Metadata schema:**
```python
{
    "file": "/path/to/analyzed/repo/src/main.py",
    "language": "python",
    "type": "function",     # function | class | module | architecture
    "repo": "repo-name",
}
```

**Usage:** Fed into the AI Engine's project generation pipeline as implementation reference.

---

## 5. DOCUMENT ID CONVENTIONS & THREADING

### 5.1 Document IDs

**Format:** `{thread_base}_{entry_num}`

Examples:
- `chatgpt_2024_03_abc123_004`
- `claude_2024_11_project_x_007`
- `gemini_2025_01_refactor_012`

**Thread base:** Everything before the last underscore + number. Used for thread reconstruction.

### 5.2 Thread Reconstruction

ChromaDB stores **fragments**, not full files. A 10,000-word conversation may be split into 20 chunks. To read the full narrative:

**Method 1: Assembly Endpoint (Recommended)**
```
GET /v1/aviary/assembly?collection=chat_conversations&doc_id=chatgpt_2024_03_abc123_004
```

This endpoint:
1. Looks up the document by ID
2. Extracts `source_file` from metadata
3. Queries ALL documents in the collection where `file == source_file`
4. Sorts by `entry` number (ascending)
5. Concatenates with `\n\n` separators

**Method 2: Direct ChromaDB Query**
```python
source_file = "/home/flintx/ai-chats/2024/03/herbert-refactor.md"
results = coll.get(
    where={"file": source_file},
    limit=500,
    include=["documents", "metadatas"]
)
# Sort by entry number
entries = sorted(
    zip(results["ids"], results["documents"], results["metadatas"]),
    key=lambda x: int(x[2].get("entry", "0"))
)
full_text = "\n\n".join(doc for _, doc, _ in entries)
```

### 5.3 Why Chunking?

ChromaDB has practical limits on document size per entry:
- Vector embedding models have token limits
- HNSW index performs better with shorter documents
- Granular metadata allows precise filtering

**Trade-off:** You cannot retrieve a full conversation in a single ChromaDB query. Assembly is required.

---

## 6. THE INGESTION PIPELINE

### 6.1 Source Files

**Location:** `/home/flintx/ai-chats/`  
**Format:** Markdown files with YAML frontmatter  
**Naming convention:** `{platform}_{YYYY}_{MM}_{topic}.md`

Example source file structure:
```markdown
---
platform: CHATGPT
date: 2024-11-04
project: herbert
tags: [architecture, database]
---

# Herbert Refactor Discussion

## User
I want to restructure the memory system into three layers...

## Assistant
That's a solid approach. Here's how I'd design it:

```python
class DendriticLayer:
    ...
```

## User
What about confidence scoring?
```

### 6.2 Chunking Process

**Tool:** `dendritic_diamond_miner.py` / `build_dossier.py`

1. Parse markdown frontmatter → extract metadata
2. Split document by paragraph boundaries (`\n\n`)
3. Group paragraphs into chunks (~1000–2000 chars)
4. Assign `entry` numbers sequentially
5. Generate `batch_id` from thread base (filename + date hash)
6. Extract topics via simple keyword matching or LLM
7. Detect code blocks (` ``` ` fences)
8. Determine `idea_maturity` from conversation progression
9. Upsert each chunk to appropriate vault collection

### 6.3 Upsert Operation

```python
# Each chunk becomes one ChromaDB document
collection.add(
    ids=[f"{batch_id}_{entry_num:03d}"],
    documents=[chunk_text],
    metadatas=[{
        "file": source_path,
        "timestamp": date,
        "platform": platform,
        "project": project,
        "vault": target_vault,
        "entry": f"{entry_num:03d}",
        "has_code_blocks": str(has_code).lower(),
        "idea_maturity": maturity,
        "topics": ", ".join(topics),
        "batch_id": batch_id,
    }]
)
```

### 6.4 Invariant Mining (Separate Pipeline)

**Tools:** `dendritic_diamond_miner.py`, `build_dossier.py`

1. Read all chunks from `chat_conversations`
2. Group by `batch_id` (full thread)
3. Run LLM prompt: "Extract recurring patterns, architectural decisions, and behavioral rules from this conversation"
4. Parse LLM output into invariant statements
5. Hash each statement → `law_id`
6. Calculate confidence from frequency across threads
7. Categorize into `communication_protocol`, `bramble`, `error_handling`, etc.
8. Upsert to `app_invariants` or `agent_invariants`

---

## 7. THE INVARIANT MINING PIPELINE

### 7.1 What Are Invariants?

Invariants are **learned rules** extracted from the operator's conversation history. They represent:
- Architectural preferences ("Always use FastAPI, never Flask")
- Behavioral patterns ("Agents must include trace_id")
- Error handling strategies ("Retry 3 times then escalate")
- UI conventions ("Forms need validation before submit")

### 7.2 The Three Layers

| Layer | Collection | Count | What It Contains |
|-------|------------|-------|------------------|
| Layer 1 | `agent_invariants` | 235 | Agent framework laws — how AI agents should behave |
| Layer 2 | `app_invariants` | 1,820 | Application architecture laws — how systems should be built |
| Layer 3 | `chat_conversations` | 26,124 | Raw conversations — source material for mining |

### 7.3 Mining Process

```
Chat Conversations (Layer 3)
    ↓ dendritic_diamond_miner.py
Pattern Extraction
    ↓ confidence scoring
App Invariants (Layer 2)
    ↓ further abstraction
Agent Invariants (Layer 1)
```

**Confidence scoring:**
- High confidence (>0.8): Pattern appears across 5+ conversations
- Medium confidence (0.5–0.8): Pattern appears in 2–4 conversations
- Low confidence (<0.5): Pattern appears once or is exploratory

### 7.4 Using Invariants in Generation

Before the Aviary pipeline compiles a payload, it queries:
```python
memory_collections = ["app_invariants", "agent_invariants", "tech_vault"]
```

Relevant invariants are injected into the SPARK phase prompt as constraints:
```
[ARCHITECTURAL CONSTRAINTS]
- All inter-agent communication MUST include trace_id (law_id: 16cf46817d4a768a, confidence: 0.91)
- Use FastAPI for all web services (law_id: a3b2c1d4e5f67890, confidence: 0.87)
```

---

## 8. QUERY PATTERNS & APIs

### 8.1 Peacock Unified REST API (Port 8000)

**Search:**
```
GET /api/search?q={query}&collections={csv}&n={limit}
```

**Document fetch:**
```
GET /api/document/{collection_name}/{doc_id}
```

**Thread reconstruction:**
```
GET /api/thread/{thread_id}
```

**Stats:**
```
GET /api/stats
```

**Browse (HTML):**
```
GET /              → Dashboard
GET /search        → Universal search page
GET /chat-logs     → Chat log browser
GET /bindings      → Bindings browser (metadata-only, semantic search broken)
GET /invariants    → Invariants explorer
GET /thread/{id}   → Thread view
```

### 8.2 Aviary API (Port 3099 — AI Engine)

**Memory search:**
```
GET /v1/aviary/search?q={query}&collections={csv}&n={limit}
```
Proxies to unified `/api/search`.

**Document assembly:**
```
GET /v1/aviary/assembly?collection={name}&doc_id={id}
```
Reconstructs full document from chunks.

**Pipeline compile (SSE stream):**
```
POST /v1/aviary/compile/stream
Body: {chat_log_text, enable_memory, memory_collections}
```

### 8.3 Binding API (Port 7878)

**Intent search:**
```
GET /search?intent=FILE_SELECTION&text=grid&method=POST&n=10
```

**List intents:**
```
GET /intents
```

**Web UI:**
```
GET /app
```

---

## 9. EMBEDDING STRATEGY

### 9.1 Default Embedding: `all-MiniLM-L6-v2`

```python
from chromadb.utils import embedding_functions
EF = embedding_functions.DefaultEmbeddingFunction()
# 384-dimensional, CPU-optimized, ~50MB model
```

**Why this model?**
- Fast inference (no GPU needed)
- Good enough for sentence-level semantic similarity
- Small footprint (fits on VPS without disk pressure)
- Widely tested with ChromaDB

### 9.2 When It's Used

| Operation | Uses Embedding? | Dimension |
|-----------|----------------|-----------|
| `collection.query(query_texts=[...])` | ✅ Yes | 384 |
| `collection.query(query_embeddings=[...])` | ❌ No (user provides) | User's |
| `collection.get()` | ❌ No | N/A |
| `collection.get(where=...)` | ❌ No | N/A |
| Binding API search | ❌ No (intent vector) | 1000 |

### 9.3 The Bindings Exception

Bindings were ingested with **pre-computed 1000-dim vectors**:
```python
collection.add(
    ids=ids,
    embeddings=embeddings,  # 1000-dim vectors from JSONL
    documents=documents,
    metadatas=metadatas
)
```

No embedding function was passed during add. The vectors were stored verbatim.

When unified tries to query bindings:
```python
coll = client.get_collection("bindings", embedding_function=EF)  # 384-dim EF
coll.query(query_texts=["test"])  # EF generates 384-dim query vector
# ChromaDB HNSW index expects 1000-dim → InvalidArgumentError
```

**Solutions:** See `BINDINGS_HowTo.md` Section 10.

---

## 10. PHYSICAL STORAGE & MAINTENANCE

### 10.1 Database Sizes

| Instance | SQLite Size | Collections | Total Docs |
|----------|-------------|-------------|------------|
| Unified | ~1.1 GB | 9 | ~149,000 |
| Bindings | ~253 MB | 1 | 86,665 |
| Dendritic | ~45 MB | 3 | ~27,000 |

### 10.2 Backup Strategy

**SQLite files are the backups.** ChromaDB persistent client stores everything in SQLite. To backup:
```bash
# Stop services first to ensure consistency
systemctl stop peacock-unified peacock-bindings herbert

# Copy SQLite files
cp /root/chroma-unified/chroma.sqlite3 /backup/chroma-unified-$(date +%Y%m%d).sqlite3
cp /root/flintx/chroma_db/chroma.sqlite3 /backup/chroma-bindings-$(date +%Y%m%d).sqlite3

# Restart services
systemctl start peacock-unified peacock-bindings herbert
```

### 10.3 Re-ingestion from Source

If a collection is corrupted, it can be rebuilt:

**Vaults:** Re-run ingestion scripts against `/home/flintx/ai-chats/`
**Invariants:** Re-run `dendritic_diamond_miner.py`
**Bindings:** Re-run `chroma_ingest.py` (reads from `mega_1000_vectors.jsonl`)

### 10.4 Deleting a Collection

```python
import chromadb
client = chromadb.PersistentClient(path="/root/chroma-unified")
client.delete_collection("bindings")
```

**Caution:** Deletion is immediate and irreversible. Have a backup.

---

## APPENDIX A: Quick Reference — Collection Metadata Fields

| Field | Type | Collections | Description |
|-------|------|-------------|-------------|
| `file` | string | All vaults, chat | Absolute path to source markdown |
| `timestamp` | string | All vaults, chat | ISO date or YYYY-MM-DD |
| `platform` | string | All vaults, chat | CHATGPT, CLAUDE, GEMINI, etc. |
| `project` | string | All vaults, chat | Project name or "unknown" |
| `vault` | string | All vaults | Collection name (self-reference) |
| `entry` | string | All vaults, chat | Sequence number (zero-padded) |
| `has_code_blocks` | string | All vaults, chat | "true" or "false" |
| `idea_maturity` | string | All vaults, chat | exploring, developing, mature |
| `topics` | string | All vaults, chat | Comma-separated keywords |
| `batch_id` | string | All vaults, chat | Thread grouping key |
| `tags` | string | chat_conversations | Comma-separated tags |
| `summary` | string | chat_conversations | One-line description |
| `density` | float | chat_conversations | 0–1 information density |
| `confidence` | float | chat_conversations, invariants | 0–1 confidence score |
| `law_id` | string | invariants | Unique hash |
| `layer` | string | invariants | layer1_agent, layer2_app |
| `category` | string | invariants | communication_protocol, bramble, etc. |
| `version` | string | invariants | v1, v2, v3 |
| `intent` | string | bindings | One of 35 intent categories |
| `method` | string | bindings | GET, POST, PUT, PATCH, DELETE |
| `path` | string | bindings | API endpoint path |
| `ui_invariant` | string | bindings | UI component description |
| `source` | string | bindings, invariants | openapi_spec, chat_conversations, etc. |

## APPENDIX B: Services & Ports

| Service | Port | File | systemd Unit |
|---------|------|------|--------------|
| Peacock Unified | 8000 | `/root/peacock_unified.py` | `peacock-unified.service` |
| Herbert v2 | 8001 | `/root/hetzner/herbert/liquid-semiotic/dendritic/herbert_v2.py` | `herbert.service` |
| Peacock Bindings | 7878 | `/root/flintx/peacock_api.py` | `peacock-bindings.service` |
| AI Engine | 3099 | `/root/hetzner/ai-engine/` | `peacock.service` |

## APPENDIX C: Related Files

| File | Purpose |
|------|---------|
| `/root/peacock_unified.py` | Unified web app + API |
| `/root/flintx/peacock_api.py` | Binding API server |
| `/root/flintx/chroma_ingest.py` | Binding ingestion script |
| `/root/flintx/peacock_cli.py` | Binding CLI client |
| `/root/flintx/peacock_web.html` | Binding web UI |
| `/root/flintx/mega_1000_vectors.jsonl` | Binding source data (86,665 lines) |
| `/root/hetzner/ai-engine/app/core/memory_engine.py` | AI Engine memory queries |
| `/root/hetzner/ai-engine/app/core/ui_scaffold.py` | Component map generation |
| `/root/hetzner/ai-engine/app/core/groq_tool_engine.py` | LLM tool definitions |
| `/root/hetzner/ai-engine/app/routes/aviary.py` | Aviary pipeline routes |
| `/root/hetzner/ai-engine/app/routes/buckets.py` | Bucket CRUD API |

---

**End of Document**
