# PEACOCK Bindings Collection — Complete How-To

**Date:** 2026-05-01  
**Version:** 1.0  
**Scope:** The `bindings` collection — what it is, how it works, how to query it, how to extend it, and how to fix the dimension mismatch.

---

## TABLE OF CONTENTS

1. [What Are Bindings?](#1-what-are-bindings)
2. [The Data Model](#2-the-data-model)
3. [The 1000-Dimensional Intent Vector Space](#3-the-1000-dimensional-intent-vector-space)
4. [How Bindings Were Created](#4-how-bindings-were-created)
5. [The Three Ways to Query Bindings](#5-the-three-ways-to-query-bindings)
6. [The Dimension Mismatch Problem](#6-the-dimension-mismatch-problem)
7. [Fix Options](#7-fix-options)
8. [How to Add New Bindings](#8-how-to-add-new-bindings)
9. [How Bindings Are Used in the Pipeline](#9-how-bindings-are-used-in-the-pipeline)
10. [Reference: All 35 Intent Categories](#10-reference-all-35-intent-categories)

---

## 1. WHAT ARE BINDINGS?

A **binding** is a mapping between an **API endpoint** and a **UI invariant**.

**In plain English:** When you have a backend API endpoint like `POST /api/v1/users`, what UI component should the frontend display for it? The binding answers that.

**Example binding:**
```json
{
  "api_endpoint": {
    "method": "POST",
    "path": "/api/v1/users",
    "summary": "Create a new user"
  },
  "distilled": {
    "intent": "RESOURCE_CREATION",
    "ui_invariant": "Create User form with validation",
    "backend_signature": "REST_CREATE_SINGLE"
  }
}
```

This says: "`POST /api/v1/users` is a resource creation endpoint. The frontend should render a 'Create User form with validation' component."

**Total bindings in database:** 86,665  
**Source:** Parsed from OpenAPI specifications  
**Database:** `/root/flintx/chroma_db/` (port 7878) + copy in `/root/chroma-unified/` (port 8000)

---

## 2. THE DATA MODEL

### 2.1 Raw Source Format (`mega_1000_vectors.jsonl`)

Each line is a JSON object with this structure:

```json
{
  "binding_id": "24727de2e559dd58",
  "source": "openapi_spec",
  "spec_source": "unknown",
  "confidence": 0.95,
  "quality_tier": 1,

  "api_endpoint": {
    "method": "POST",
    "path": "/api/v1/itemusages",
    "operation_id": "getItemUsages",
    "summary": "Retrieves item usages",
    "tags": ["api-v1"],
    "parameters": []
  },

  "distilled": {
    "intent": "RESOURCE_CREATION",
    "interaction": "POST_IMMEDIATE",
    "backend_signature": "REST_CREATE_NESTED",
    "ui_invariant": "Create Api form with validation",
    "logic_score": 0.95,
    "temporal_pattern": "SYNCHRONOUS_WITH_VALIDATION",
    "state_transition": ["CREATING", "CREATED"],
    "feedback_mechanism": "SUCCESS_MESSAGE_WITH_NAVIGATION",
    "expected_payload": {
      "type": "application/json",
      "fields": ["data"]
    }
  },

  "vector_dimensions": {
    "intent_category": 1,
    "method_type": 1,
    "path_depth": 3,
    "has_path_params": 0,
    "has_query_params": 0,
    "resource_type": 7,
    "action_verb": "unknown",
    "parameter_count": 0,
    "summary_length": 21,
    "is_nested": 1
  },

  "embedding": [1.0, 0.0, 0.0, ...]
}
```

### 2.2 Field Descriptions

| Field | Description |
|-------|-------------|
| `binding_id` | Unique identifier (hash of endpoint signature) |
| `source` | Where this binding came from (`openapi_spec`, `manual`, `inferred`) |
| `confidence` | 0–1 quality score from the distillation process |
| `quality_tier` | 1 = high quality, 2 = medium, 3 = low |
| `api_endpoint.method` | HTTP method (GET, POST, PUT, PATCH, DELETE) |
| `api_endpoint.path` | API endpoint path |
| `api_endpoint.operation_id` | OpenAPI operationId |
| `api_endpoint.summary` | Human-readable summary |
| `api_endpoint.tags` | OpenAPI tags |
| `api_endpoint.parameters` | Path/query parameter names |
| `distilled.intent` | One of 35 intent categories |
| `distilled.ui_invariant` | Description of the UI component that should handle this endpoint |
| `distilled.backend_signature` | Pattern name for the backend operation |
| `distilled.logic_score` | 0–1 score for how well the intent matches the endpoint |
| `distilled.temporal_pattern` | SYNC, ASYNC, BATCH, etc. |
| `distilled.state_transition` | State machine states (e.g., ["CREATING", "CREATED"]) |
| `distilled.feedback_mechanism` | How the UI should respond (success message, redirect, etc.) |
| `vector_dimensions` | 10 numerical/categorical features used to build the embedding |
| `embedding` | 1000-dimensional sparse float vector |

### 2.3 ChromaDB Storage Format

When `chroma_ingest.py` processes a JSONL line, it creates:

**Document text:**
```
METHOD:POST PATH:/api/v1/itemusages Retrieves item usages INTENT:RESOURCE_CREATION Create Api form with validation REST_CREATE_NESTED
```

**Metadata:**
```python
{
    "intent": "RESOURCE_CREATION",
    "method": "POST",
    "path": "/api/v1/itemusages",
    "ui_invariant": "Create Api form with validation",
    "source": "openapi_spec"
}
```

**Embedding:** The pre-computed 1000-dim vector from the JSONL file.

**ID:** `{binding_id}_{count}` (count appended for deduplication)

---

## 3. THE 1000-DIMENSIONAL INTENT VECTOR SPACE

### 3.1 Why 1000 Dimensions?

Bindings use a **hand-crafted sparse vector** instead of a neural embedding. Here's why:

**Neural embeddings (384-dim) are semantically dense:**
- "Create a user" and "Create a file" are close in vector space
- This is correct for natural language understanding
- But WRONG for API→UI mapping — these endpoints need completely different UI components

**Intent vectors (1000-dim) are categorically orthogonal:**
- `RESOURCE_CREATION` and `AUTHENTICATION` are far apart regardless of their natural language similarity
- `POST` and `GET` occupy different dimensions
- Path depth, nesting, and parameter count each get their own dimensions

### 3.2 How the Vector Is Built

The vector is constructed from `vector_dimensions` plus the intent one-hot:

```
Index 0–34:    Intent one-hot (35 categories)
Index ~50:     Method type one-hot
Index ~70:     Path depth + nested flag
Index ~115:    Resource type
Index ~200:    Parameter count
Index ~300:    Summary length bucket
Index ~500+:   Additional categorical features
Index ~900+:   Fractional confidence scores
```

Example vector for `POST /api/v1/itemusages`:
```python
vec[0] = 1.0    # RESOURCE_CREATION at index 0
vec[52] = 1.0   # POST method
vec[72] = 1.0   # Path depth 3
vec[73] = 1.0   # Nested resource
vec[115] = 1.0  # Resource type 7
# ... mostly zeros elsewhere
```

This is a **sparse vector** — typically <20 non-zero values out of 1000.

### 3.3 Why Not Just Use Metadata Filtering?

You might ask: "Why not just filter `where={"intent": "RESOURCE_CREATION"}` and skip the vector?"

Because the vector search also captures:
- **Method similarity:** POST and PUT are closer than POST and GET
- **Path structure similarity:** `/users/{id}/posts` is closer to `/projects/{id}/tasks` than to `/health`
- **Parameter complexity:** Endpoints with many parameters cluster together
- **Interaction pattern:** Immediate vs. async endpoints separate naturally

The metadata filter gives you exact matches. The vector gives you **nearest neighbors in intent space**.

---

## 4. HOW BINDINGS WERE CREATED

### 4.1 Source: OpenAPI Specifications

Bindings were generated by parsing OpenAPI (Swagger) specification files:

1. Collect OpenAPI JSON/YAML files from various APIs
2. For each endpoint (`path` + `method`):
   - Extract `operationId`, `summary`, `parameters`, `tags`
   - Run an LLM prompt to classify the intent
   - Generate `ui_invariant` (what UI component this endpoint needs)
   - Compute `vector_dimensions` from endpoint structure
   - Build 1000-dim embedding
3. Write all bindings to `mega_1000_vectors.jsonl`
4. Run `chroma_ingest.py` to load into ChromaDB

### 4.2 The Ingestion Script

```python
# /root/flintx/chroma_ingest.py
CHROMA_DIR = "/root/flintx/chroma_db"
VECTORS_FILE = "/root/flintx/mega_1000_vectors.jsonl"
BATCH_SIZE = 1000

client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = client.get_or_create_collection(
    name="bindings",
    metadata={"hnsw:space": "cosine"}
)

with open(VECTORS_FILE) as f:
    for line in f:
        data = json.loads(line)
        emb = data["embedding"]  # 1000-dim, validated

        # Build document text from fields
        parts = []
        parts.append(f"METHOD:{method} PATH:{path}")
        parts.append(summary)
        parts.append(operation_id)
        parts.append(f"INTENT:{intent}")
        parts.append(ui_invariant)
        doc = " ".join(parts)

        # Extract metadata
        meta = {
            "intent": intent,
            "method": method,
            "path": path,
            "ui_invariant": ui_invariant[:500],
            "source": source,
        }

        collection.add(
            ids=[f"{binding_id}_{count}"],
            embeddings=[emb],      # ← 1000-dim, no embedding function
            documents=[doc],
            metadatas=[meta]
        )
```

**Key point:** The embeddings are passed directly. No `embedding_function` is used during ingestion. This is why the collection stores 1000-dim vectors.

---

## 5. THE THREE WAYS TO QUERY BINDINGS

### 5.1 Method 1: Peacock Binding API (Port 7878) — RECOMMENDED

This is the **only** interface that properly handles 1000-dim vectors.

**Running instance:** `https://peacock.save-aichats.com`  
**Code:** `/root/flintx/peacock_api.py`  
**Service:** `peacock-bindings.service`

#### 5.1.1 HTTP API

```bash
# Search by intent only
curl "https://peacock.save-aichats.com/search?intent=RESOURCE_CREATION&n=5"

# Search by intent + method
curl "https://peacock.save-aichats.com/search?intent=FILE_SELECTION&method=POST&n=10"

# Search by intent + text
curl "https://peacock.save-aichats.com/search?intent=AUTHENTICATION&text=login%20credential&n=5"

# List all intents
curl "https://peacock.save-aichats.com/intents"
```

**Response format:**
```json
{
  "intent": "RESOURCE_CREATION",
  "text": null,
  "method": null,
  "count": 5,
  "results": [
    {
      "rank": 1,
      "id": "binding_24727_0",
      "distance": 0.1234,
      "document": "METHOD:POST PATH:/api/v1/itemusages ...",
      "meta": {
        "intent": "RESOURCE_CREATION",
        "method": "POST",
        "path": "/api/v1/itemusages",
        "ui_invariant": "Create Api form with validation",
        "source": "openapi_spec"
      }
    }
  ]
}
```

#### 5.1.2 Web UI

Open `https://peacock.save-aichats.com/app` in a browser.

Features:
- Intent dropdown (all 35 categories)
- Method filter (GET/POST/PUT/PATCH/DELETE)
- Text query input
- Result cards with method badge, path, UI invariant, distance score

#### 5.1.3 CLI Tool

```bash
cd /root/flintx
python3 peacock_cli.py --intent FILE_SELECTION -n 5
python3 peacock_cli.py --intent RESOURCE_CREATION --method POST --text "form validation" -n 10
python3 peacock_cli.py --list-intents
```

#### 5.1.4 Python Direct

```python
import httpx

resp = httpx.get(
    "https://peacock.save-aichats.com/search",
    params={"intent": "RESOURCE_CREATION", "method": "POST", "n": 10}
)
data = resp.json()
for r in data["results"]:
    print(f"{r['meta']['method']} {r['meta']['path']}")
    print(f"  UI: {r['meta']['ui_invariant']}")
    print(f"  Distance: {r['distance']:.4f}")
```

---

### 5.2 Method 2: ChromaDB Direct (Port 7878 Database)

Query the raw ChromaDB client directly.

```python
import chromadb
from chromadb.config import Settings

client = chromadb.PersistentClient(
    path="/root/flintx/chroma_db",
    settings=Settings(anonymized_telemetry=False)
)
coll = client.get_collection("bindings")

# Method A: Metadata-only filter (no embedding needed)
results = coll.get(
    where={"intent": "RESOURCE_CREATION", "method": "POST"},
    limit=10,
    include=["documents", "metadatas"]
)

# Method B: Intent vector search (build vector manually)
INTENTS = ["RESOURCE_CREATION", "BULK_RESOURCE_CREATION", "AI_INFERENCE",
           "RESOURCE_DELETION", "RESOURCE_UPDATE", ...]  # 35 total

def build_intent_vector(intent):
    vec = [0.0] * 1000
    if intent in INTENTS:
        vec[INTENTS.index(intent)] = 1.0
    return vec

results = coll.query(
    query_embeddings=[build_intent_vector("RESOURCE_CREATION")],
    n_results=10,
    where={"method": "POST"},
    include=["documents", "metadatas", "distances"]
)

# Method C: Get by ID
binding = coll.get(ids=["binding_24727_0"], include=["documents", "metadatas"])
```

---

### 5.3 Method 3: Peacock Unified (Port 8000) — LIMITED

The unified app has a `/bindings` page, but **semantic search is broken**.

**What works:**
- Browse all bindings (pagination)
- Filter by intent (metadata dropdown)
- Filter by method (metadata dropdown)
- Filter by path substring (post-filtering)

**What does NOT work:**
- The `q=` text search field on `/bindings` (crashes with dimension mismatch)
- Searching bindings through `/api/search` or `/search`
- Including `"bindings"` in the Aviary UI search collections

**How to use it safely:**
```
https://herbert.save-aichats.com/bindings           → Browse all
https://herbert.save-aichats.com/bindings?intent=RESOURCE_CREATION&method=POST → Filtered browse
```

**DO NOT use:**
```
https://herbert.save-aichats.com/bindings?q=login   → WILL CRASH
```

---

## 6. THE DIMENSION MISMATCH PROBLEM

### 6.1 What Happens

**Error message:**
```
InvalidArgumentError: Collection expecting embedding with dimension of 1000, got 384
```

**Where it occurs:**

| Caller | File | Line | Trigger |
|--------|------|------|---------|
| Unified search | `peacock_unified.py:333` | `coll.query(query_texts=[q])` | Any search including bindings |
| Unified bindings page | `peacock_unified.py:653` | `coll.query(query_texts=[q])` | Text search on /bindings |
| Unified API | `peacock_unified.py:839` | `coll.query(query_texts=[q])` | `/api/search` with bindings |
| AI Engine memory | `memory_engine.py:40` | `query_memory(collections=["bindings"])` | Any pipeline query |
| UI scaffold | `ui_scaffold.py:161` | `query_memory(collections=["bindings"])` | Frontend generation |
| Groq tool | `groq_tool_engine.py:542` | `query_memory(collections=["bindings"])` | `search_bindings` tool |

### 6.2 Why It Happens

**Step-by-step:**

1. `peacock_unified.py` initializes with `DefaultEmbeddingFunction()` (384-dim)
2. This EF is attached to ALL collections via `get_collection(name, embedding_function=EF)`
3. When you call `coll.query(query_texts=["login"])`, ChromaDB:
   a. Calls EF to embed "login" → produces 384-dim vector
   b. Passes 384-dim vector to HNSW index
   c. HNSW index expects 1000-dim → raises `InvalidArgumentError`

**The binding collection in unified was copied from `/root/flintx/chroma_db/` with its original 1000-dim embeddings intact.** No re-embedding was performed.

### 6.3 Current Workarounds in Code

**In `peacock_unified.py`:**
```python
# The error is caught by broad exception handling
try:
    coll = get_collection(cname)
    res = coll.query(query_texts=[q], ...)
except Exception as e:
    results[cname] = {"error": str(e)}  # Silently returns error JSON
```

This means the UI shows an error message instead of results — not a crash, but non-functional.

**In `groq_tool_engine.py`:**
```python
async def _tool_search_bindings(arguments: dict) -> str:
    result = await query_memory(query=..., collections=["bindings"], n=10)
    ctx = result.get("context", "")
    if not ctx or ctx.strip().endswith("=== END MEMORY"):
        return f"No bindings found for: {mem_query}"  # Silent failure
```

The tool returns "No bindings found" even though the real problem is a dimension mismatch.

---

## 7. FIX OPTIONS

### 7.1 Option A: Re-embed Bindings with 384-dim Model (Recommended for Unified)

**What to do:**
1. Delete the `bindings` collection from unified DB
2. Re-ingest from `mega_1000_vectors.jsonl` using `DefaultEmbeddingFunction()` on the document text

**Steps:**
```python
import chromadb
from chromadb.utils import embedding_functions

client = chromadb.PersistentClient(path="/root/chroma-unified")
ef = embedding_functions.DefaultEmbeddingFunction()

# Step 1: Delete old collection
client.delete_collection("bindings")

# Step 2: Create new collection with 384-dim EF
new_coll = client.create_collection("bindings", embedding_function=ef)

# Step 3: Re-ingest from JSONL (using document text, not pre-computed vectors)
import json
with open("/root/flintx/mega_1000_vectors.jsonl") as f:
    for line in f:
        data = json.loads(line)
        doc = f"METHOD:{data['api_endpoint']['method']} PATH:{data['api_endpoint']['path']} ..."
        meta = {
            "intent": data["distilled"]["intent"],
            "method": data["api_endpoint"]["method"],
            "path": data["api_endpoint"]["path"],
            "ui_invariant": data["distilled"]["ui_invariant"][:500],
            "source": data.get("source", "unknown"),
        }
        new_coll.add(ids=[data["binding_id"]], documents=[doc], metadatas=[meta])
        # ChromaDB auto-embeds with 384-dim EF
```

**Pros:**
- Unified search works seamlessly
- No special-case code needed
- AI Engine queries work automatically
- Single embedding function across all collections

**Cons:**
- Loses the custom intent-vector search semantics
- "Create user" and "Create file" will cluster together (semantic similarity)
- The standalone Peacock API (7878) would still use 1000-dim, creating divergence
- Re-ingestion takes time (~86K documents)

---

### 7.2 Option B: Hybrid Query Layer in Unified

**What to do:** Modify `peacock_unified.py` to detect bindings and handle them specially.

**Implementation:**
```python
def get_collection(name: str):
    if name == "bindings":
        # Don't attach embedding function — we'll pass vectors manually
        return client.get_collection(name)
    return client.get_collection(name, embedding_function=EF)

# In search/browsings routes, for bindings:
if cname == "bindings" and q:
    # Build intent vector from query text heuristic
    # OR proxy to port 7878
    # OR use metadata-only get() with post-filtering
```

**Pros:**
- Preserves 1000-dim intent vectors
- No data migration
- Keeps both query modes available

**Cons:**
- More complex code (special case for one collection)
- AI Engine still goes through unified → needs same fix
- Two query paths to maintain

---

### 7.3 Option C: Proxy to Port 7878

**What to do:** Modify `peacock_unified.py` to forward binding queries to the standalone API.

**Implementation:**
```python
import httpx

async def search_bindings_proxy(intent, text, method, n):
    params = {"intent": intent or "FILE_SELECTION", "n": n}
    if text: params["text"] = text
    if method: params["method"] = method
    resp = await httpx.get("http://localhost:7878/search", params=params)
    return resp.json()
```

**Pros:**
- Uses the working API directly
- Intent-vector semantics preserved
- Minimal code changes

**Cons:**
- Adds HTTP hop latency
- Unified now depends on 7878 being up
- Error handling more complex

---

### 7.4 Option D: Fix AI Engine Directly

**What to do:** Update `memory_engine.py` and `ui_scaffold.py` to query port 7878 directly for bindings.

**Implementation:**
```python
# memory_engine.py
async def query_bindings_direct(query, intent=None, method=None, n=10):
    params = {"intent": intent or "FILE_SELECTION", "n": n}
    if method: params["method"] = method
    resp = await httpx.get("http://localhost:7878/search", params=params)
    return resp.json()
```

**Pros:**
- Bypasses broken unified path entirely
- Working immediately

**Cons:**
- peacock_unified.py `/bindings` page still broken
- Duplicated query logic between systems
- Frontend UI still can't search bindings through unified

---

## 8. HOW TO ADD NEW BINDINGS

### 8.1 From a New OpenAPI Spec

**Step 1:** Parse the OpenAPI spec into binding JSON objects

```python
import json

bindings = []
for path, methods in spec["paths"].items():
    for method, details in methods.items():
        binding = {
            "binding_id": f"{method.lower()}_{path.replace('/', '_').replace('{', '').replace('}', '')}",
            "source": "openapi_spec",
            "confidence": 0.9,
            "api_endpoint": {
                "method": method.upper(),
                "path": path,
                "operation_id": details.get("operationId", ""),
                "summary": details.get("summary", ""),
                "parameters": [p["name"] for p in details.get("parameters", [])]
            },
            "distilled": {
                "intent": classify_intent(method.upper(), path, details),  # Your logic
                "ui_invariant": generate_ui_invariant(method.upper(), path, details),
                "backend_signature": infer_backend_pattern(method.upper(), path),
            },
            "vector_dimensions": compute_dimensions(method.upper(), path, details),
            "embedding": build_embedding_vector(intent, method.upper(), path, details)
        }
        bindings.append(binding)
```

**Step 2:** Append to `mega_1000_vectors.jsonl`

```bash
python3 -c "
import json
for b in new_bindings:
    print(json.dumps(b))
" >> /root/flintx/mega_1000_vectors.jsonl
```

**Step 3:** Re-run ingestion

```bash
cd /root/flintx
python3 chroma_ingest.py
```

This will re-ingest ALL bindings (including the new ones). The script uses `get_or_create_collection`, so existing bindings are duplicated. **Better approach:**

```python
# Add only new bindings directly
collection = client.get_collection("bindings")
collection.add(
    ids=[b["binding_id"] for b in new_bindings],
    embeddings=[b["embedding"] for b in new_bindings],
    documents=[build_doc(b) for b in new_bindings],
    metadatas=[build_meta(b) for b in new_bindings]
)
```

### 8.2 Manual/Tactical Bindings

For ad-hoc bindings not from OpenAPI specs:

```bash
cd /root/flintx
python3 herbert/inject_tactical_bindings_v4.py
```

This script clones an existing binding's embedding and modifies the intent dimension:

```python
# Clone donor binding, boost target intent
donor_vec = get_binding_vector("RESOURCE_CREATION", "/api/v1/users")
new_vec = donor_vec.copy()
new_vec[INTENTS.index("FILE_UPLOAD")] = 1.0  # Boost new intent
```

---

## 9. HOW BINDINGS ARE USED IN THE PIPELINE

### 9.1 In the AI Engine (Project Generation)

When generating a full-stack project:

1. **Eagle phase** designs the API endpoints
2. **Crow phase** generates the backend code
3. **UI Scaffold** (`ui_scaffold.py`) queries bindings for each endpoint:
   ```python
   for endpoint in extracted_endpoints:
       binding = await query_binding(endpoint["method"], endpoint["path"])
       component = build_component(endpoint, binding)
   ```
4. **Output:** A component map JSON describing every UI element needed

### 9.2 In the Groq Tool Engine

The `search_bindings` tool is available to the LLM:

```python
# When the LLM needs to know "what UI for POST /users?"
tool_call = {
    "name": "search_bindings",
    "arguments": {
        "intent": "RESOURCE_CREATION",
        "method": "POST",
        "path_fragment": "users"
    }
}
```

**Current status:** BROKEN (returns "No bindings found" due to dimension mismatch)

### 9.3 In the Neural Link Chat

When the operator asks "how do I build a form for X endpoint?", the system:
1. Queries bindings for the endpoint
2. Returns the exact UI invariant
3. LLM generates the component based on the invariant

**Current status:** BROKEN (same dimension mismatch)

---

## 10. REFERENCE: ALL 35 INTENT CATEGORIES

| Index | Intent | Description | Example Endpoint |
|-------|--------|-------------|------------------|
| 0 | `RESOURCE_CREATION` | Create a single resource | `POST /users` |
| 1 | `BULK_RESOURCE_CREATION` | Create multiple resources | `POST /users/bulk` |
| 2 | `AI_INFERENCE` | Run AI/ML inference | `POST /predict` |
| 3 | `RESOURCE_DELETION` | Delete a single resource | `DELETE /users/{id}` |
| 4 | `RESOURCE_UPDATE` | Full update of a resource | `PUT /users/{id}` |
| 5 | `USER_CREATION` | Create a user account | `POST /register` |
| 6 | `FILE_UPLOAD` | Upload a file | `POST /upload` |
| 7 | `AUTHENTICATION` | Login / authenticate | `POST /login` |
| 8 | `SEARCH_QUERY` | Search / filter resources | `GET /search?q=...` |
| 9 | `RESOURCE_PARTIAL_UPDATE` | Patch a resource | `PATCH /users/{id}` |
| 10 | `DEPLOYMENT` | Deploy an artifact | `POST /deploy` |
| 11 | `USER_UPDATE` | Update user profile | `PUT /profile` |
| 12 | `USER_DELETION` | Delete user account | `DELETE /account` |
| 13 | `COMMERCE_TRANSACTION` | Purchase / payment | `POST /checkout` |
| 14 | `BULK_RESOURCE_DELETION` | Delete multiple resources | `DELETE /users/bulk` |
| 15 | `COMMERCE_MANAGEMENT` | Manage commerce settings | `PUT /store/settings` |
| 16 | `COMMERCE_CANCELLATION` | Cancel order / subscription | `POST /cancel` |
| 17 | `FILE_SELECTION` | Select / browse files | `GET /files` |
| 18 | `UI_COMPONENT` | Generic UI component | `GET /components` |
| 19 | `UI_ELEMENT` | Specific UI element | `GET /buttons` |
| 20 | `FUNCTION_CALL` | Execute a function | `POST /invoke` |
| 21 | `ROUTE_HANDLER` | Generic route handler | `GET /{path}` |
| 22 | `MIDDLEWARE` | Middleware operation | `USE /auth` |
| 23 | `HOOK` | Lifecycle hook | `POST /hooks` |
| 24 | `EVENT` | Event / webhook | `POST /events` |
| 25 | `STATE_CHANGE` | Change system state | `PUT /state` |
| 26 | `DATA_FETCH` | Fetch external data | `GET /external/data` |
| 27 | `CACHE_OPERATION` | Cache read/write | `GET /cache/{key}` |
| 28 | `AUTH_MIDDLEWARE` | Auth middleware | `USE /verify` |
| 29 | `ERROR_HANDLER` | Error handling | `GET /error` |
| 30 | `UNKNOWN` | Unclassified | — |
| 31 | `PENDING` | Async job pending | `GET /jobs/{id}` |
| 32 | `PROCESSING` | Async job processing | `GET /jobs/{id}/status` |
| 33 | `COMPLETED` | Async job completed | `GET /jobs/{id}/result` |
| 34 | `FAILED` | Async job failed | `GET /jobs/{id}/error` |

---

## APPENDIX A: Verification Commands

```bash
# Check binding count in both databases
python3 -c "
import sqlite3
for path in ['/root/chroma-unified/chroma.sqlite3', '/root/flintx/chroma_db/chroma.sqlite3']:
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(\"SELECT name, dimension FROM collections WHERE name='bindings';\")
    print(path, cur.fetchall())
"

# Test the working API
curl -s "https://peacock.save-aichats.com/search?intent=RESOURCE_CREATION&n=3" | python3 -m json.tool

# Test the broken unified path
curl -s "http://localhost:8000/api/search?q=login&collections=bindings&n=3" | python3 -m json.tool
# → Returns: {"bindings": {"error": "Collection expecting embedding with dimension of 1000, got 384"}}

# List all unique intents in the database
python3 -c "
import chromadb, sqlite3
conn = sqlite3.connect('/root/flintx/chroma_db/chroma.sqlite3')
cur = conn.cursor()
cur.execute(\"SELECT string_value FROM embedding_metadata WHERE key='intent' GROUP BY string_value ORDER BY string_value;\")
for row in cur.fetchall():
    print(row[0])
"
```

## APPENDIX B: File Locations

| File | Purpose |
|------|---------|
| `/root/flintx/peacock_api.py` | Binding API server (port 7878) |
| `/root/flintx/chroma_ingest.py` | Ingestion script for bindings |
| `/root/flintx/peacock_cli.py` | CLI client for binding API |
| `/root/flintx/peacock_web.html` | Web UI for binding API |
| `/root/flintx/mega_1000_vectors.jsonl` | Source data (86,665 bindings) |
| `/root/flintx/herbert/adapter.py` | Herbert→Binding adapter |
| `/root/flintx/herbert/mapper.py` | UI invariant → component mapper |
| `/root/flintx/herbert/inject_tactical_bindings_v4.py` | Tactical binding injector |
| `/root/peacock_unified.py` | Unified app (bindings broken here) |
| `/root/hetzner/ai-engine/app/core/ui_scaffold.py` | Component map generator |
| `/root/hetzner/ai-engine/app/core/memory_engine.py` | Memory query engine |
| `/root/hetzner/ai-engine/app/core/groq_tool_engine.py` | LLM tool definitions |

---

**End of Document**
