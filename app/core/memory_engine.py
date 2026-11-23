"""
PEACOCK MEMORY ENGINE
Queries the Peacock Unified ChromaDB via its local API.
No chromadb import needed — pure HTTP to localhost:8000.
"""

import os
import json
import httpx
from typing import List, Optional, Dict, Any

PEACOCK_UNIFIED_URL = os.getenv("PEACOCK_UNIFIED_URL", "http://localhost:8000")

# Default collections the LLM can query
DEFAULT_COLLECTIONS = [
    "agent_invariants",
    "app_invariants",
    "chat_conversations",
    "tech_vault",
    "seed_vault",
    "case_files_vault",
    "personal_vault",
    "bindings",
]


async def query_memory(
    query: str,
    collections: Optional[List[str]] = None,
    n: int = 5,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Query Peacock Unified memory for relevant documents.
    Returns structured results by collection.
    """
    targets = collections or DEFAULT_COLLECTIONS
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(
                f"{PEACOCK_UNIFIED_URL}/api/search",
                params={
                    "q": query,
                    "collections": targets,
                    "n": n,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return _format_results(data, query)
        except Exception as e:
            return {
                "status": "error",
                "query": query,
                "error": str(e),
                "context": "",
            }


def _format_results(raw: Dict[str, Any], query: str) -> Dict[str, Any]:
    """Format raw API results into LLM-friendly context string."""
    lines = [
        f"=== PEACOCK MEMORY RETRIEVAL ===",
        f"Query: {query}",
        f"",
    ]
    total_hits = 0
    for coll_name, items in raw.items():
        if isinstance(items, dict) and "error" in items:
            continue
        if not isinstance(items, list) or not items:
            continue
        total_hits += len(items)
        lines.append(f"--- {coll_name} ({len(items)} hits) ---")
        for i, item in enumerate(items, 1):
            doc_id = item.get("id", "")
            doc = item.get("document", "")
            meta = item.get("metadata", {})
            dist = item.get("distance", "N/A")
            # Truncate long docs
            doc_preview = doc[:800] + "..." if len(doc) > 800 else doc
            lines.append(f"[{i}] id={doc_id} dist={dist}")
            lines.append(f"    {doc_preview}")
            if meta:
                meta_str = ", ".join(f"{k}={v}" for k, v in meta.items() if v)
                lines.append(f"    meta: {meta_str}")
            lines.append("")

    lines.append(f"=== END MEMORY ({total_hits} total hits) ===")
    return {
        "status": "ok",
        "query": query,
        "total_hits": total_hits,
        "context": "\n".join(lines),
        "results": raw,
    }


async def fetch_document(collection: str, doc_id: str, timeout: float = 10.0) -> Dict[str, Any]:
    """Fetch a single document by ID from a specific collection."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(
                f"{PEACOCK_UNIFIED_URL}/api/document/{collection}/{doc_id}",
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "status": "ok",
                "collection": collection,
                "document": data,
            }
        except httpx.HTTPStatusError as e:
            return {
                "status": "not_found" if e.response.status_code == 404 else "error",
                "collection": collection,
                "doc_id": doc_id,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": collection,
                "doc_id": doc_id,
                "error": str(e),
            }


async def browse_collection(
    collection: str,
    limit: int = 20,
    offset: int = 0,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """Browse documents in a collection with pagination."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(
                f"{PEACOCK_UNIFIED_URL}/browse/{collection}",
                params={"limit": limit, "offset": offset},
            )
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            lines = [
                f"=== BROWSE {collection} (offset={offset}, limit={limit}) ===",
                f"Total: {data.get('total', 'unknown')}",
                "",
            ]
            for item in items:
                doc_id = item.get("id", "")
                doc = item.get("document", "")[:300]
                meta = item.get("metadata", {})
                lines.append(f"id={doc_id}")
                lines.append(f"    {doc}{'...' if len(item.get('document','')) > 300 else ''}")
                if meta:
                    meta_str = ", ".join(f"{k}={v}" for k, v in meta.items() if v)
                    lines.append(f"    meta: {meta_str}")
                lines.append("")
            lines.append("=== END BROWSE ===")
            return {
                "status": "ok",
                "collection": collection,
                "context": "\n".join(lines),
                "total": data.get("total", 0),
                "returned": len(items),
            }
        except Exception as e:
            return {
                "status": "error",
                "collection": collection,
                "error": str(e),
                "context": "",
            }


async def get_memory_stats() -> Dict[str, Any]:
    """Get collection stats from Peacock Unified."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            resp = await client.get(f"{PEACOCK_UNIFIED_URL}/api/stats")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
