"""
GROQ TOOL ENGINE — Native local tool calling for Groq models.

Implements the OpenAI-compatible function calling loop directly:
  1. Call Groq API with tool definitions
  2. Parse tool_calls from assistant response
  3. Execute tools locally (memory queries, project generation, etc.)
  4. Return results to Groq API
  5. Repeat until model returns final answer

Supports parallel tool use and multi-turn agentic loops.
"""

import json
import time
import asyncio
from typing import List, Dict, Optional, Any, Callable
from openai import AsyncOpenAI, RateLimitError

from app.core.key_manager import GroqPool, KeyPool, KeyAsset
from app.core.memory_engine import query_memory, get_memory_stats, fetch_document, browse_collection, PEACOCK_UNIFIED_URL
from app.core.project_engine import generate_project, ProjectConfig, project_result_to_json
from app.core.context_budget import ContextBudget
from app.core.ui_scaffold import generate_component_map, scaffold_frontend
from app.utils.formatter import CLIFormatter
from app.config import MODEL_REGISTRY
from app.db.database import ProjectBucketDB
import httpx

# ---------------------------------------------------------------------------
# TOOL SCHEMAS
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# TOOL SCHEMAS
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_peacock_memory",
            "description": "Search Peacock Unified memory vault for relevant documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Rephrase the user's intent for best vector similarity match."
                    },
                    "collections": {
                        "type": "array",
                        "items": {"type": "string", "enum": [
                            "agent_invariants", "app_invariants", "chat_conversations",
                            "tech_vault", "seed_vault", "case_files_vault",
                            "personal_vault", "bindings", "codebase_vault"
                        ]},
                        "description": "Which collections to search. Omit to search all."
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Number of results per collection (1-20). Default 5.",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_peacock_memory_status",
            "description": "Get statistics about all Peacock Unified memory collections (document counts).",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_chat_thread",
            "description": "Reconstruct a full chat thread by ID prefix.",
            "parameters": {
                "type": "object",
                "properties": {
                    "thread_id": {
                        "type": "string",
                        "description": "Thread ID prefix (e.g., '2024-11-04_chatgpt_project_x')."
                    }
                },
                "required": ["thread_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_bindings",
            "description": "Search API→UI binding invariants.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "description": "Intent keyword like RESOURCE_CREATION, RESOURCE_READ, etc."
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
                        "description": "HTTP method to filter by."
                    },
                    "path_fragment": {
                        "type": "string",
                        "description": "Partial API path to search, e.g., '/itemusages'"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_memory_document",
            "description": "Fetch a full document by collection + doc_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name (e.g., app_invariants, chat_conventions)"
                    },
                    "doc_id": {
                        "type": "string",
                        "description": "Document ID from a previous search result (e.g., app_invariants__16cf46817d4a768a)"
                    }
                },
                "required": ["collection", "doc_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "browse_memory_collection",
            "description": "Browse a collection with pagination.",
            "parameters": {
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection to browse"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Number of documents per page (max 100)",
                        "default": 20
                    },
                    "offset": {
                        "type": "integer",
                        "description": "Offset for pagination",
                        "default": 0
                    }
                },
                "required": ["collection"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_project_bucket",
            "description": "Create a named project bucket to collect documents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Unique bucket name (e.g., 'fastapi_agent_v2')"
                    },
                    "description": {
                        "type": "string",
                        "description": "What this project is about"
                    }
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_and_fill_bucket",
            "description": "Search memory and add all results to a bucket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bucket_name": {
                        "type": "string",
                        "description": "Target bucket name"
                    },
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "collections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Collections to search"
                    },
                    "n_results": {
                        "type": "integer",
                        "description": "Results per collection",
                        "default": 10
                    }
                },
                "required": ["bucket_name", "query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_project_bucket",
            "description": "Add a specific document to a bucket by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bucket_name": {
                        "type": "string",
                        "description": "Target bucket name"
                    },
                    "collection": {
                        "type": "string",
                        "description": "Document's collection"
                    },
                    "doc_id": {
                        "type": "string",
                        "description": "Document ID from search results"
                    },
                    "note": {
                        "type": "string",
                        "description": "Why you're saving this (e.g., 'critical invariant for auth')"
                    }
                },
                "required": ["bucket_name", "collection", "doc_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_project_bucket",
            "description": "List all documents in a project bucket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bucket_name": {
                        "type": "string",
                        "description": "Bucket name"
                    }
                },
                "required": ["bucket_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_from_project_bucket",
            "description": "Get full content of a document from a bucket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bucket_name": {
                        "type": "string",
                        "description": "Bucket name"
                    },
                    "doc_id": {
                        "type": "string",
                        "description": "Document ID"
                    }
                },
                "required": ["bucket_name", "doc_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_from_bucket",
            "description": "Generate a project from all documents in a bucket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bucket_name": {
                        "type": "string",
                        "description": "Bucket containing your research"
                    },
                    "description": {
                        "type": "string",
                        "description": "What to build"
                    },
                    "project_type_hint": {
                        "type": "string",
                        "description": "Optional: fastapi, react, cli, etc."
                    }
                },
                "required": ["bucket_name", "description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_project",
            "description": "Generate a deployable project from description. Pass prior research_context if available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "What to build. Be specific about features, stack, and architecture."
                    },
                    "project_type_hint": {
                        "type": "string",
                        "description": "Optional type hint: fastapi, react, cli, bot, etc."
                    },
                    "memory_collections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Memory collections to use for invariant lookup. Defaults to app_invariants, agent_invariants, tech_vault, bindings."
                    },
                    "research_context": {
                        "type": "string",
                        "description": "Optional: paste memory query results, chat logs, invariant citations, or any prior research you gathered. This feeds directly into the project architect."
                    }
                },
                "required": ["description"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "count_bucket_tokens",
            "description": "Analyze the token count of a project bucket and report context budget. Use this before generating to understand if the bucket fits in one LLM call or needs staged processing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "bucket_name": {
                        "type": "string",
                        "description": "Bucket to analyze"
                    }
                },
                "required": ["bucket_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_component_map",
            "description": "Analyze backend source code and generate a component map JSON that cross-references API endpoints with Peacock UI bindings. Use this AFTER generating backend code to plan the frontend.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_code": {
                        "type": "string",
                        "description": "Backend source code or API spec to analyze"
                    },
                    "framework": {
                        "type": "string",
                        "description": "Frontend framework: react, vue, svelte",
                        "default": "react"
                    },
                    "style_system": {
                        "type": "string",
                        "description": "CSS system: tailwind, bootstrap, css-modules",
                        "default": "tailwind"
                    },
                    "app_name": {
                        "type": "string",
                        "description": "Name of the application",
                        "default": "GeneratedApp"
                    }
                },
                "required": ["source_code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scaffold_frontend",
            "description": "Generate complete frontend code from a component map JSON. Use this AFTER generate_component_map to produce the actual UI files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "component_map_json": {
                        "type": "string",
                        "description": "JSON component map from generate_component_map"
                    },
                    "custom_css": {
                        "type": "string",
                        "description": "Optional CSS customization notes",
                        "default": ""
                    }
                },
                "required": ["component_map_json"]
            }
        }
    },
]


# ---------------------------------------------------------------------------
# SYSTEM PROMPT
# ---------------------------------------------------------------------------

HEREDOC_TOOL_SYSTEM_PROMPT = """You are PEACOCK NEURAL LINK with access to 149K+ documents across 8 collections. Use tools to retrieve memory and build projects. Call multiple tools in parallel when independent.

COLLECTIONS: agent_invariants (agent frameworks), app_invariants (architecture), chat_conversations (past chats), tech_vault (code/how-to), seed_vault (ideas), case_files_vault (research), personal_vault (preferences), bindings (API→UI), codebase_vault (analyzed codebases).

MEMORY: Rephrase user intent into conceptual queries. Target specific collections. Increase n_results if thin. Cite: "Per {collection} [law_id:X, conf:Y]".

CODE: ALWAYS output as bash heredoc — cat > /path/file << 'EOF' ... EOF. No markdown backticks. No placeholders. chmod +x for executables.

PROJECT WORKFLOW (STEPS IN ORDER):
1. create_project_bucket(name)
2. search_and_fill_bucket(query, collections) — parallel calls OK
3. list_project_bucket — review what you captured
4. count_bucket_tokens — check if context fits or needs staging
5. generate_from_bucket(description) — ONLY after steps 1-4 are complete

WEB APP WORKFLOW (for fullstack builds):
1. generate_from_bucket(description) — backend code + deploy.sh
2. generate_component_map(source_code) — analyze backend, cross-reference bindings
3. scaffold_frontend(component_map_json) — generate React/Vue frontend with proper API bindings

RECALL: query → note IDs → fetch_memory_document for critical docs.

STOP: Once you have the information you need, STOP calling tools and answer. Do not repeat the same tool+args.
FAILURE: Say honestly if memory returns nothing. Never hallucinate citations.
"""


# ---------------------------------------------------------------------------
# TOOL IMPLEMENTATIONS
# ---------------------------------------------------------------------------

async def _tool_query_peacock_memory(arguments: dict) -> str:
    result = await query_memory(
        query=arguments.get("query", ""),
        collections=arguments.get("collections"),
        n=arguments.get("n_results", 5),
    )
    return result.get("context", "No memory results found.")


async def _tool_get_peacock_memory_status(arguments: dict) -> str:
    stats = await get_memory_stats()
    lines = ["=== PEACOCK MEMORY STATUS ==="]
    total = 0
    for name, info in stats.items():
        if isinstance(info, dict):
            count = info.get("count", 0)
            total += count
            lines.append(f"  {name}: {count:,} docs")
    lines.append(f"  TOTAL: {total:,} documents")
    lines.append("=== END STATUS ===")
    return "\n".join(lines)


async def _tool_get_chat_thread(arguments: dict) -> str:
    thread_id = arguments.get("thread_id", "")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"{PEACOCK_UNIFIED_URL}/api/thread/{thread_id}")
            resp.raise_for_status()
            data = resp.json()
            docs = data.get("documents", [])
            if not docs:
                return f"No thread found for ID: {thread_id}"
            lines = [f"=== THREAD: {thread_id} ==="]
            for d in docs:
                meta = d.get("metadata", {})
                content = d.get("document", "")[:600]
                lines.append(f"\n[{meta.get('entry', '?')}] {meta.get('timestamp', '')} | {meta.get('platform', '')}")
                lines.append(content)
            lines.append("\n=== END THREAD ===")
            return "\n".join(lines)
        except Exception as e:
            return f"Error retrieving thread: {e}"


async def _tool_fetch_memory_document(arguments: dict) -> str:
    collection = arguments.get("collection", "")
    doc_id = arguments.get("doc_id", "")
    result = await fetch_document(collection=collection, doc_id=doc_id)
    if result.get("status") == "ok":
        doc = result.get("document", {})
        lines = [
            f"=== FULL DOCUMENT: {doc_id} ===",
            f"Collection: {collection}",
            f"",
            doc.get("document", ""),
            f"",
            f"Metadata: {doc.get('metadata', {})}",
            f"=== END DOCUMENT ===",
        ]
        return "\n".join(lines)
    else:
        return f"Error fetching document: {result.get('error', 'unknown')}"


async def _tool_browse_memory_collection(arguments: dict) -> str:
    collection = arguments.get("collection", "")
    limit = arguments.get("limit", 20)
    offset = arguments.get("offset", 0)
    result = await browse_collection(collection=collection, limit=limit, offset=offset)
    return result.get("context", f"Browse failed: {result.get('error', 'unknown')}")


async def _tool_search_bindings(arguments: dict) -> str:
    params = {"n": 10}
    intent = arguments.get("intent")
    method = arguments.get("method")
    path_fragment = arguments.get("path_fragment")
    query_parts = []
    if intent:
        query_parts.append(intent)
    if method:
        query_parts.append(method)
    if path_fragment:
        query_parts.append(path_fragment)

    # Use the binding search API if available, otherwise fallback to generic memory query
    mem_query = " ".join(query_parts) if query_parts else "API bindings"
    result = await query_memory(query=mem_query, collections=["bindings"], n=10)
    ctx = result.get("context", "")
    if not ctx or ctx.strip().endswith("=== END MEMORY"):
        return f"No bindings found for: {mem_query}"
    return ctx


async def _tool_generate_project(arguments: dict) -> str:
    description = arguments.get("description", "")
    hint = arguments.get("project_type_hint")
    collections = arguments.get("memory_collections")
    research_context = arguments.get("research_context", "")

    # If the model already gathered memory context, prepend it to the description
    enriched_description = description
    if research_context:
        enriched_description = f"=== PRIOR RESEARCH CONTEXT ===\n{research_context}\n\n=== PROJECT REQUEST ===\n{description}"

    config = ProjectConfig(
        name="generated_project",
        description=enriched_description,
        model="llama-3.3-70b-versatile",
        gateway="groq",
        temperature=0.3,
        max_iterations=2,
        files_per_batch=3,
        enable_memory=True,
        memory_collections=collections or ["app_invariants", "agent_invariants", "tech_vault", "bindings"],
        project_type_hint=hint,
        research_context=research_context if research_context else None,
    )

    try:
        result = await generate_project(config)
        data = project_result_to_json(result)
        files = data.get("files", [])
        deploy = data.get("deploy_script", "")

        # Build full heredoc output for every file so user can copy/paste deploy
        heredoc_lines = ["=== GENERATED FILES ===", ""]
        for f in files:
            path = f.get("path", "")
            content = f.get("content", "")
            mode = f.get("mode", "create")
            executable = f.get("executable", False)
            heredoc_lines.append(f"# --- {path} ---")
            if mode == "append":
                heredoc_lines.append(f"cat >> {path} << 'EOF'")
            else:
                heredoc_lines.append(f"cat > {path} << 'EOF'")
            heredoc_lines.append(content)
            heredoc_lines.append("EOF")
            if executable:
                heredoc_lines.append(f"chmod +x {path}")
            heredoc_lines.append("")

        heredoc_lines.append("=== DEPLOY SCRIPT ===")
        heredoc_lines.append(deploy)

        summary = [
            f"=== PROJECT GENERATION COMPLETE ===",
            f"Status: {data['status']}",
            f"Project: {data['architecture']['project_name'] if data['architecture'] else 'N/A'}",
            f"Files: {len(files)}",
            f"Iterations: {data['metrics']['iterations']}",
            f"Tokens: {data['metrics']['total_tokens']}",
            f"Duration: {data['metrics']['total_duration_ms']}ms",
            f"Validation Errors: {sum(r.get('errors', 0) for r in data.get('validation', {}).get('results', []))}",
            "",
            "\n".join(heredoc_lines),
            "",
            "=== END PROJECT ===",
        ]
        return "\n".join(summary)
    except Exception as e:
        return f"Project generation failed: {e}"


# ---------------------------------------------------------------------------
# PROJECT BUCKETS — Session-scoped working memory for builds
# ---------------------------------------------------------------------------

PROJECT_BUCKETS: Dict[str, Dict[str, Any]] = {}


def _load_buckets_from_db():
    """Hydrate in-memory buckets from SQLite on startup."""
    global PROJECT_BUCKETS
    PROJECT_BUCKETS = ProjectBucketDB.load_all_buckets()
    if PROJECT_BUCKETS:
        CLIFormatter.info(f"[BUCKETS] Loaded {len(PROJECT_BUCKETS)} persistent buckets from DB")


def _ensure_bucket(name: str) -> Dict[str, Any]:
    if name not in PROJECT_BUCKETS:
        # Try DB first
        db_bucket = ProjectBucketDB.load_bucket(name)
        if db_bucket:
            PROJECT_BUCKETS[name] = {
                "created_at": time.time(),
                "description": db_bucket["description"],
                "items": db_bucket["items"],
            }
        else:
            PROJECT_BUCKETS[name] = {
                "created_at": time.time(),
                "description": "",
                "items": {},  # doc_id -> {collection, content, metadata, note}
            }
    return PROJECT_BUCKETS[name]


def _save_bucket(name: str):
    """Persist a bucket to SQLite."""
    bucket = PROJECT_BUCKETS.get(name)
    if bucket:
        ProjectBucketDB.save_bucket(name, bucket.get("description", ""), bucket.get("items", {}))


def _bucket_summary(name: str) -> str:
    bucket = _ensure_bucket(name)
    items = bucket["items"]
    lines = [
        f"=== PROJECT BUCKET: {name} ===",
        f"Description: {bucket['description']}",
        f"Items: {len(items)}",
        "",
    ]
    for doc_id, item in items.items():
        coll = item.get("collection", "?")
        note = item.get("note", "")
        preview = item.get("content", "")[:120].replace("\n", " ")
        lines.append(f"  {doc_id} | {coll} | {preview}...")
        if note:
            lines.append(f"      note: {note}")
    lines.append("=== END BUCKET ===")
    return "\n".join(lines)


async def _add_search_to_bucket(name: str, query: str, collections: Optional[List[str]], n: int) -> str:
    """Run a memory query and add ALL results to the bucket."""
    bucket = _ensure_bucket(name)
    result = await query_memory(query=query, collections=collections, n=n)
    if result.get("status") != "ok":
        return f"Search failed: {result.get('error', 'unknown')}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{PEACOCK_UNIFIED_URL}/api/search",
            params={"q": query, "collections": collections or [], "n": n},
        )
        raw = resp.json()

    added = 0
    for coll_name, items in raw.items():
        if not isinstance(items, list):
            continue
        for item in items:
            doc_id = item.get("id")
            if not doc_id or doc_id in bucket["items"]:
                continue
            bucket["items"][doc_id] = {
                "collection": coll_name,
                "content": item.get("document", ""),
                "metadata": item.get("metadata", {}),
                "distance": item.get("distance", "N/A"),
                "note": f"Auto-added from search: '{query}'",
            }
            added += 1
    _save_bucket(name)
    return f"Added {added} documents to bucket '{name}' from query '{query}'."


async def _add_doc_to_bucket(name: str, collection: str, doc_id: str, note: str) -> str:
    bucket = _ensure_bucket(name)
    if doc_id in bucket["items"]:
        return f"Document {doc_id} already in bucket '{name}'."
    result = await fetch_document(collection=collection, doc_id=doc_id)
    if result.get("status") != "ok":
        return f"Failed to fetch {doc_id}: {result.get('error', 'unknown')}"
    doc = result.get("document", {})
    bucket["items"][doc_id] = {
        "collection": collection,
        "content": doc.get("document", ""),
        "metadata": doc.get("metadata", {}),
        "note": note or "",
    }
    _save_bucket(name)
    return f"Added {doc_id} to bucket '{name}'."


async def _get_bucket_item(name: str, doc_id: str) -> str:
    bucket = _ensure_bucket(name)
    item = bucket["items"].get(doc_id)
    if not item:
        return f"Document {doc_id} not found in bucket '{name}'."
    lines = [
        f"=== BUCKET ITEM: {doc_id} ===",
        f"Collection: {item['collection']}",
        f"Note: {item.get('note', '')}",
        f"Metadata: {item.get('metadata', {})}",
        f"",
        item.get("content", ""),
        f"",
        "=== END ITEM ===",
    ]
    return "\n".join(lines)


async def _generate_from_bucket(name: str, description: str, hint: Optional[str]) -> str:
    """Run project generation using bucket contents as research context.
    
    Uses ContextBudget to decide between single-call generation (small bucket)
    or staged generation (large bucket that exceeds TPM limits).
    """
    bucket = _ensure_bucket(name)
    if not bucket["items"]:
        return f"Bucket '{name}' is empty. Add documents before generating."

    # Analyze context budget
    budget = ContextBudget(model_id="llama-3.3-70b-versatile")
    analysis = budget.count_bucket(bucket["items"])
    safe_budget = budget.safe_prompt_budget("generate")

    # If bucket fits in a single generation call, use fast path
    if analysis["total_tokens"] <= safe_budget:
        research_lines = [f"=== PROJECT BUCKET RESEARCH: {name} ===", ""]
        for doc_id, item in bucket["items"].items():
            research_lines.append(f"--- {doc_id} ({item['collection']}) ---")
            research_lines.append(item.get("content", ""))
            research_lines.append("")
        research_lines.append("=== END BUCKET RESEARCH ===")
        return await _tool_generate_project({
            "description": description,
            "project_type_hint": hint,
            "research_context": "\n".join(research_lines),
        })

    # --- STAGED GENERATION: bucket is too large for single call ---
    CLIFormatter.info(f"[STAGED GEN] Bucket {name} has {analysis['total_tokens']:,} tokens. Running map-reduce pipeline.")
    
    # MAP PHASE: Extract invariants from every doc in token-sized batches
    s1_budget = budget.safe_prompt_budget("invariant_extract")
    s1_system = """You are an Architecture Analyst. Read the provided research documents and extract ONLY architectural invariants, patterns, constraints, and stack recommendations.

Output format (JSON only):
{"invariants": [{"text": "...", "source": "doc_id"}], "patterns": [{"text": "...", "source": "doc_id"}], "constraints": [{"text": "...", "source": "doc_id"}], "stack_recommendations": ["..."]}

Rules:
- Be concise. 1-2 sentences per item.
- Only extract items relevant to the project.
- Do NOT write code."""
    
    all_invariants = []
    all_patterns = []
    all_constraints = []
    all_stacks = []
    batch_num = 0
    
    # Pack docs into batches that fit the Stage 1 budget
    packed = budget.pack_bucket_items(bucket["items"], s1_budget - budget._count(s1_system) - 200)
    
    # If pack fits everything in one batch, great. If not, we need multiple batches.
    # pack_bucket_items returns what fits. For the rest, we loop.
    remaining_items = dict(bucket["items"])
    while remaining_items:
        packed = budget.pack_bucket_items(remaining_items, s1_budget - budget._count(s1_system) - 200)
        if not packed["included_docs"]:
            # Even one doc is too big — truncate it
            first_doc_id = list(remaining_items.keys())[0]
            first_item = remaining_items[first_doc_id]
            truncated = budget.truncate_for_budget(
                first_item.get("content", ""),
                s1_budget - budget._count(s1_system) - 300
            )
            packed = {
                "text": f"--- {first_doc_id} ({first_item.get('collection', '?')}) ---\n{first_item.get('note', '')}\n{truncated}",
                "included_docs": [first_doc_id],
                "used_tokens": 0,
                "remaining_budget": 0,
            }
        
        batch_num += 1
        s1_user = f"Project: {description}\nType: {hint}\n\n=== DOCUMENTS ===\n{packed['text']}\n\nExtract invariants as JSON only."
        s1_result = await _run_groq_stage(
            system=s1_system,
            user=s1_user,
            max_tokens=1500,
        )
        
        # Parse JSON result (best effort)
        try:
            parsed = json.loads(s1_result[s1_result.find('{'):s1_result.rfind('}')+1])
            all_invariants.extend(parsed.get("invariants", []))
            all_patterns.extend(parsed.get("patterns", []))
            all_constraints.extend(parsed.get("constraints", []))
            all_stacks.extend(parsed.get("stack_recommendations", []))
        except Exception:
            # If parse fails, store raw text as a single invariant
            all_invariants.append({"text": s1_result[:500], "source": "batch_parse_failed"})
        
        # Remove processed docs from remaining
        for doc_id in packed["included_docs"]:
            remaining_items.pop(doc_id, None)
        
        CLIFormatter.info(f"[STAGED GEN] Batch {batch_num}: processed {len(packed['included_docs'])} docs. Remaining: {len(remaining_items)}")
    
    # Deduplicate stack recommendations
    all_stacks = list(dict.fromkeys(all_stacks))
    
    combined_invariants = json.dumps({
        "invariants": all_invariants,
        "patterns": all_patterns,
        "constraints": all_constraints,
        "stack_recommendations": all_stacks,
    }, indent=2)
    
    # STAGE 2: Architecture Plan
    s2_system = """You are a Solutions Architect. Produce a precise architecture plan from the provided invariants.

Output format:
1. FILE TREE — Every file with full paths
2. DEPENDENCIES — pip packages
3. ARCHITECTURE DECISIONS — Bullets with rationale
4. INVARIANT COMPLIANCE MAP — Which invariant → which file

Rules:
- Be specific. No hand-waving.
- Every decision traces back to an invariant."""
    s2_user = f"Project: {description}\nType: {hint}\n\n=== INVARIANTS ===\n{combined_invariants}\n\nProduce the architecture plan."
    s2_result = await _run_groq_stage(system=s2_system, user=s2_user, max_tokens=2000)
    
    # STAGE 3: Code Generation
    s3_system = """You are a Senior Engineer. Generate complete, runnable code files as bash heredoc commands.

Output format (MANDATORY):
cat > /path/to/file.py << 'EOF'
# complete file content
EOF
chmod +x /path/to/file.py

Rules:
1. EVERY file must be complete — no TODOs, no placeholders.
2. Use full absolute paths or clear relative paths.
3. Quote EOF: 'EOF'
4. NEVER use markdown triple backticks around heredoc blocks.
5. Include chmod +x for executables."""
    s3_user = f"Project: {description}\nType: {hint}\n\n=== PLAN ===\n{s2_result}\n\n=== INVARIANTS ===\n{combined_invariants}\n\nGenerate ALL files as heredoc bash blocks."
    s3_result = await _run_groq_stage(system=s3_system, user=s3_user, max_tokens=3000)
    
    return (
        f"=== STAGED PROJECT GENERATION ===\n"
        f"Bucket: {name} | Docs: {analysis['doc_count']} | Total tokens: {analysis['total_tokens']:,}\n"
        f"Map batches: {batch_num} | Invariants extracted: {len(all_invariants)}\n"
        f"Patterns: {len(all_patterns)} | Constraints: {len(all_constraints)} | Stack: {all_stacks}\n\n"
        f"=== GENERATED OUTPUT ===\n{s3_result}\n"
        f"=== END GENERATION ==="
    )


async def _groq_call_with_retry(
    call_fn: Callable,
    max_retries: int = 3,
    base_delay: float = 2.0,
) -> Any:
    """
    Execute a Groq API call with 429 retry + key failover.
    On RateLimitError: marks key on cooldown, swaps to next key, backs off.
    """
    last_error = None
    asset: Optional[KeyAsset] = None
    client: Optional[AsyncOpenAI] = None

    for attempt in range(max_retries):
        try:
            if client is None:
                asset = GroqPool.get_next()
                client = AsyncOpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=asset.key,
                )
            return await call_fn(client)
        except RateLimitError as e:
            last_error = e
            if asset:
                # Cooldown duration grows with attempt: 30s, 60s, 120s
                cooldown = 30 * (2 ** attempt)
                GroqPool.mark_cooldown(asset.account, cooldown)
                CLIFormatter.warning(f"429 on key [{asset.account}] — cooling down {cooldown}s (attempt {attempt + 1}/{max_retries})")
            # Close old client, force new key on next loop
            if client:
                await client.close()
                client = None
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                CLIFormatter.info(f"Backing off {delay}s before retry...")
                await asyncio.sleep(delay)
            else:
                break
        except Exception as e:
            last_error = e
            break
        finally:
            if client and attempt == max_retries - 1:
                await client.close()

    raise last_error or Exception("Groq call failed after retries")


async def _run_groq_stage(system: str, user: str, max_tokens: int = 2000) -> str:
    """Run a single Groq LLM stage using the tool engine's client pattern."""
    try:
        response = await _groq_call_with_retry(
            lambda client: client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.3,
                max_tokens=max_tokens,
            )
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        return f"Stage failed: {e}"


async def _tool_count_bucket_tokens(arguments: dict) -> str:
    """Analyze token count of a project bucket."""
    name = arguments.get("bucket_name", "")
    bucket = _ensure_bucket(name)
    if not bucket["items"]:
        return f"Bucket '{name}' is empty."
    budget = ContextBudget(model_id="llama-3.3-70b-versatile")
    return budget.report(bucket["items"])


async def _tool_create_project_bucket(arguments: dict) -> str:
    name = arguments.get("name", "")
    desc = arguments.get("description", "")
    bucket = _ensure_bucket(name)
    bucket["description"] = desc
    _save_bucket(name)
    return f"Created project bucket '{name}'. Description: {desc}. Ready to add documents."


async def _tool_search_and_fill_bucket(arguments: dict) -> str:
    return await _add_search_to_bucket(
        name=arguments.get("bucket_name", ""),
        query=arguments.get("query", ""),
        collections=arguments.get("collections"),
        n=arguments.get("n_results", 10),
    )


async def _tool_add_to_project_bucket(arguments: dict) -> str:
    return await _add_doc_to_bucket(
        name=arguments.get("bucket_name", ""),
        collection=arguments.get("collection", ""),
        doc_id=arguments.get("doc_id", ""),
        note=arguments.get("note", ""),
    )


async def _tool_list_project_bucket(arguments: dict) -> str:
    return _bucket_summary(arguments.get("bucket_name", ""))


async def _tool_get_from_project_bucket(arguments: dict) -> str:
    return await _get_bucket_item(
        name=arguments.get("bucket_name", ""),
        doc_id=arguments.get("doc_id", ""),
    )


async def _tool_generate_from_bucket(arguments: dict) -> str:
    return await _generate_from_bucket(
        name=arguments.get("bucket_name", ""),
        description=arguments.get("description", ""),
        hint=arguments.get("project_type_hint"),
    )


TOOL_MAP = {
    "query_peacock_memory": _tool_query_peacock_memory,
    "get_peacock_memory_status": _tool_get_peacock_memory_status,
    "get_chat_thread": _tool_get_chat_thread,
    "fetch_memory_document": _tool_fetch_memory_document,
    "browse_memory_collection": _tool_browse_memory_collection,
    "search_bindings": _tool_search_bindings,
    "create_project_bucket": _tool_create_project_bucket,
    "search_and_fill_bucket": _tool_search_and_fill_bucket,
    "add_to_project_bucket": _tool_add_to_project_bucket,
    "list_project_bucket": _tool_list_project_bucket,
    "get_from_project_bucket": _tool_get_from_project_bucket,
    "generate_from_bucket": _tool_generate_from_bucket,
    "generate_project": _tool_generate_project,
    "count_bucket_tokens": _tool_count_bucket_tokens,
    "generate_component_map": generate_component_map,
    "scaffold_frontend": scaffold_frontend,
}


# ---------------------------------------------------------------------------
# EXECUTION ENGINE
# ---------------------------------------------------------------------------

COMPOUND_MODELS = {"groq/compound", "groq/compound-mini"}

# Per-conversation token burn tracker (conversation_id -> total_tokens_used)
CONVERSATION_TOKEN_TRACKER: Dict[str, int] = {}
DEFAULT_CONVERSATION_TOKEN_CAP = 5_000  # Hard cap per conversation in tool mode


def _is_compound_model(model_id: str) -> bool:
    return model_id in COMPOUND_MODELS


def _calculate_cost(model_id: str, usage: dict) -> float:
    model_cfg = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    if not model_cfg:
        return 0.0
    in_tokens = usage.get("prompt_tokens", 0)
    out_tokens = usage.get("completion_tokens", 0)
    cost = (in_tokens / 1_000_000 * model_cfg.input_price_1m) + \
           (out_tokens / 1_000_000 * model_cfg.output_price_1m)
    return round(cost, 6)


async def _tool_loop_events(
    model_id: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    max_iterations: int = 10,
    files: Optional[List[str]] = None,
    conversation_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
):
    """
    Core tool loop as an async generator.
    Yields real-time events for SSE streaming.
    """
    start_time = time.time()
    asset = GroqPool.get_next()
    client = AsyncOpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=asset.key,
    )

    conv_budget_key = conversation_id or f"anonymous_{id(user_prompt)}"
    tokens_so_far = CONVERSATION_TOKEN_TRACKER.get(conv_budget_key, 0)
    token_cap = DEFAULT_CONVERSATION_TOKEN_CAP

    system_msg = {"role": "system", "content": HEREDOC_TOOL_SYSTEM_PROMPT}
    messages: List[Dict[str, Any]] = [system_msg]
    if history:
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})

    user_content = user_prompt
    if files:
        from app.core.striker import _inject_file_context
        user_content = _inject_file_context(user_prompt, files)
    messages.append({"role": "user", "content": user_content})

    total_tokens = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    tool_trace: List[Dict[str, Any]] = []
    seen_calls: set = set()

    try:
        for iteration in range(min(max_iterations, 3)):
            CLIFormatter.info(f"[TOOL LOOP] Iteration {iteration + 1}/3 | model={model_id}")
            yield {"type": "status", "status": "iteration_started", "iteration": iteration + 1, "total": min(max_iterations, 3)}

            # Token budget circuit breaker
            current_total = tokens_so_far + total_tokens["total_tokens"]
            if current_total >= token_cap:
                warning = f"CONVERSATION TOKEN CAP REACHED: {current_total}/{token_cap}. Forcing final answer."
                CLIFormatter.warning(warning)
                yield {"type": "status", "status": "token_cap_reached", "current": current_total, "cap": token_cap}
                messages.append({
                    "role": "system",
                    "content": f"Token budget exhausted ({current_total}/{token_cap}). Synthesize your final answer immediately without calling any more tools."
                })
                try:
                    final_resp = await _groq_call_with_retry(
                        lambda client: client.chat.completions.create(
                            model=model_id, messages=messages,
                            temperature=min(temperature, 0.5), max_tokens=max_tokens,
                        )
                    )
                    if final_resp.usage:
                        total_tokens["prompt_tokens"] += getattr(final_resp.usage, "prompt_tokens", 0)
                        total_tokens["completion_tokens"] += getattr(final_resp.usage, "completion_tokens", 0)
                        total_tokens["total_tokens"] += getattr(final_resp.usage, "total_tokens", 0)
                    final_content = final_resp.choices[0].message.content or ""
                except Exception as e:
                    final_content = f"Token cap reached. Error: {e}"
                cost = _calculate_cost(model_id, total_tokens)
                KeyPool.record_usage("groq", asset.account, total_tokens)
                CONVERSATION_TOKEN_TRACKER[conv_budget_key] = current_total + total_tokens["total_tokens"]
                for word in final_content.split(" "):
                    yield {"type": "content", "content": word + " "}
                yield {"type": "metadata", "usage": total_tokens, "cost": cost,
                       "tool_calls_made": len(tool_trace), "tool_trace": tool_trace,
                       "duration_ms": int((time.time() - start_time) * 1000),
                       "conversation_id": conversation_id,
                       "error": f"Token cap reached: {token_cap}"}
                return

            effective_temp = min(temperature, 0.5)
            response = await _groq_call_with_retry(
                lambda client: client.chat.completions.create(
                    model=model_id, messages=messages, tools=TOOLS, tool_choice="auto",
                    temperature=effective_temp, max_tokens=max_tokens, parallel_tool_calls=True,
                )
            )

            message = response.choices[0].message
            if response.usage:
                total_tokens["prompt_tokens"] += getattr(response.usage, "prompt_tokens", 0)
                total_tokens["completion_tokens"] += getattr(response.usage, "completion_tokens", 0)
                total_tokens["total_tokens"] += getattr(response.usage, "total_tokens", 0)

            if message.tool_calls:
                tool_calls_serializable = []
                for tc in message.tool_calls:
                    tool_calls_serializable.append({
                        "id": tc.id, "type": tc.type,
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                    })
                    yield {"type": "tool_call", "tool": tc.function.name, "args": tc.function.arguments}

                messages.append({
                    "role": "assistant", "content": message.content or "",
                    "tool_calls": tool_calls_serializable,
                })

                execute_tasks = []
                for tc in message.tool_calls:
                    tool_name = tc.function.name
                    tool_fn = TOOL_MAP.get(tool_name)
                    if not tool_fn:
                        tool_trace.append({"tool": tool_name, "error": "Unknown tool"})
                        yield {"type": "tool_result", "tool": tool_name, "result": "ERROR: Unknown tool"}
                        messages.append({"role": "tool", "tool_call_id": tc.id,
                                         "content": json.dumps({"error": f"Tool {tool_name} not found"})})
                        continue
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError as e:
                        tool_trace.append({"tool": tool_name, "error": f"Invalid JSON args: {e}"})
                        yield {"type": "tool_result", "tool": tool_name, "result": f"ERROR: Invalid args: {e}"}
                        messages.append({"role": "tool", "tool_call_id": tc.id,
                                         "content": json.dumps({"error": f"Invalid arguments: {e}"})})
                        continue

                    call_key = (tool_name, json.dumps(args, sort_keys=True))
                    if call_key in seen_calls:
                        warning = f"WARNING: Duplicate call to {tool_name}"
                        tool_trace.append({"tool": tool_name, "args": args, "result": warning})
                        yield {"type": "tool_result", "tool": tool_name, "result": warning}
                        messages.append({"role": "tool", "tool_call_id": tc.id, "content": warning})
                        continue
                    seen_calls.add(call_key)

                    tool_trace.append({"tool": tool_name, "args": args})
                    execute_tasks.append((tc.id, tool_fn, args, tool_name))

                for tc_id, tool_fn, args, name in execute_tasks:
                    if name == "generate_from_bucket":
                        bucket_name = args.get("bucket_name", "")
                        bucket = PROJECT_BUCKETS.get(bucket_name)
                        if not bucket or not bucket.get("items"):
                            warning = f"Bucket '{bucket_name}' is empty. Call create_project_bucket and search_and_fill_bucket first."
                            tool_trace.append({"tool": name, "args": args, "result": warning})
                            yield {"type": "tool_result", "tool": name, "result": warning}
                            messages.append({"role": "tool", "tool_call_id": tc_id, "content": warning})
                            continue

                    try:
                        result = await tool_fn(args)
                    except Exception as e:
                        result = e

                    if isinstance(result, Exception):
                        content = json.dumps({"error": str(result)})
                        for tt in tool_trace:
                            if tt.get("tool") == name and tt.get("result") is None:
                                tt["result"] = f"ERROR: {result}"
                                break
                        yield {"type": "tool_result", "tool": name, "result": f"ERROR: {result}"}
                    else:
                        content = str(result) if isinstance(result, str) else json.dumps(result)
                        for tt in tool_trace:
                            if tt.get("tool") == name and tt.get("result") is None:
                                tt["result"] = content[:2000]
                                break
                        yield {"type": "tool_result", "tool": name, "result": content[:500]}

                    messages.append({"role": "tool", "tool_call_id": tc_id, "content": content})

                yield {"type": "status", "status": "iteration_completed", "iteration": iteration + 1}
                await asyncio.sleep(2)
                continue

            else:
                # Final answer
                cost = _calculate_cost(model_id, total_tokens)
                KeyPool.record_usage("groq", asset.account, total_tokens)
                CONVERSATION_TOKEN_TRACKER[conv_budget_key] = tokens_so_far + total_tokens["total_tokens"]
                yield {"type": "status", "status": "synthesizing"}
                final_content = message.content or ""
                for word in final_content.split(" "):
                    yield {"type": "content", "content": word + " "}
                yield {"type": "metadata", "usage": total_tokens, "cost": cost,
                       "tool_calls_made": len(tool_trace), "tool_trace": tool_trace,
                       "duration_ms": int((time.time() - start_time) * 1000),
                       "conversation_id": conversation_id}
                return

        # Max iterations
        CLIFormatter.warning(f"[TOOL LOOP] Max iterations reached. Forcing final answer.")
        yield {"type": "status", "status": "max_iterations_reached"}
        messages.append({
            "role": "system",
            "content": "You have used the maximum number of tool calls. Synthesize what you have learned and provide your final answer to the user now. Do not call any more tools."
        })
        try:
            final_resp = await _groq_call_with_retry(
                lambda client: client.chat.completions.create(
                    model=model_id, messages=messages,
                    temperature=min(temperature, 0.5), max_tokens=max_tokens,
                )
            )
            if final_resp.usage:
                total_tokens["prompt_tokens"] += getattr(final_resp.usage, "prompt_tokens", 0)
                total_tokens["completion_tokens"] += getattr(final_resp.usage, "completion_tokens", 0)
                total_tokens["total_tokens"] += getattr(final_resp.usage, "total_tokens", 0)
            final_content = final_resp.choices[0].message.content or ""
        except Exception as e:
            final_content = f"Max iterations reached. Error: {e}"

        cost = _calculate_cost(model_id, total_tokens)
        KeyPool.record_usage("groq", asset.account, total_tokens)
        CONVERSATION_TOKEN_TRACKER[conv_budget_key] = tokens_so_far + total_tokens["total_tokens"]
        for word in final_content.split(" "):
            yield {"type": "content", "content": word + " "}
        yield {"type": "metadata", "usage": total_tokens, "cost": cost,
               "tool_calls_made": len(tool_trace), "tool_trace": tool_trace,
               "duration_ms": int((time.time() - start_time) * 1000),
               "conversation_id": conversation_id,
               "error": "Max iterations reached"}

    except Exception as e:
        CLIFormatter.error(f"Groq Tool Engine failure: {e}")
        yield {"type": "error", "error": str(e)}
    finally:
        await client.close()


async def execute_groq_tool_chat(
    model_id: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    max_iterations: int = 10,
    files: Optional[List[str]] = None,
    conversation_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Execute a Groq chat with local tool calling loop.
    Returns final content, usage, cost, and tool execution trace.
    """
    content_parts = []
    final_metadata = None
    async for event in _tool_loop_events(
        model_id=model_id, user_prompt=user_prompt, temperature=temperature,
        max_tokens=max_tokens, max_iterations=max_iterations, files=files,
        conversation_id=conversation_id, history=history,
    ):
        if event["type"] == "content":
            content_parts.append(event["content"])
        elif event["type"] == "metadata":
            final_metadata = event
        elif event["type"] == "error":
            raise Exception(event.get("error", "Tool loop failed"))

    full_content = "".join(content_parts)
    if final_metadata:
        return {
            "content": full_content,
            "gateway": "groq",
            "model": model_id,
            "key_used": final_metadata.get("key_used", "unknown"),
            "usage": final_metadata.get("usage", {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}),
            "cost": final_metadata.get("cost", 0.0),
            "duration_ms": final_metadata.get("duration_ms", 0),
            "tool_calls_made": final_metadata.get("tool_calls_made", 0),
            "tool_trace": final_metadata.get("tool_trace", []),
            "error": final_metadata.get("error"),
        }
    return {"content": full_content, "gateway": "groq", "model": model_id, "key_used": "unknown",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            "cost": 0.0, "duration_ms": 0, "tool_calls_made": 0, "tool_trace": []}


async def execute_groq_tool_chat_stream(
    model_id: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: Optional[int] = None,
    max_iterations: int = 10,
    files: Optional[List[str]] = None,
    conversation_id: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
):
    """
    TRUE streaming tool chat.
    Yields SSE-compatible events in real-time as the tool loop executes.
    """
    async for event in _tool_loop_events(
        model_id=model_id, user_prompt=user_prompt, temperature=temperature,
        max_tokens=max_tokens, max_iterations=max_iterations, files=files,
        conversation_id=conversation_id, history=history,
    ):
        yield event


# ---------------------------------------------------------------------------
# MODULE INIT: Hydrate buckets from persistent storage
# ---------------------------------------------------------------------------
try:
    _load_buckets_from_db()
except Exception as e:
    CLIFormatter.warning(f"[BUCKETS] Failed to load from DB: {e}")
