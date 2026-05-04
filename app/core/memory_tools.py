"""
PEACOCK MEMORY TOOLS for pydantic-ai Agent
Registers tools that let the LLM query the unified ChromaDB.
"""

from typing import List, Optional
from app.core.memory_engine import query_memory, get_memory_stats


async def query_peacock_memory(
    query: str,
    collections: Optional[List[str]] = None,
    n_results: int = 5,
) -> str:
    """
    Search the Peacock Unified memory vault for relevant information.

    Use this when the user asks about:
    - Past conversations, chat logs, or interactions
    - Technical knowledge, code patterns, or experiments
    - Agent frameworks, app architecture, or design invariants
    - API bindings, UI patterns, or integration mappings
    - Personal notes, research, or case studies

    Args:
        query: The search query (rephrase the user's question for best vector match)
        collections: Which vaults to search. Options:
            agent_invariants - Agent framework laws & patterns
            app_invariants - Application architecture rules
            chat_conversations - Past chat logs & conversations
            tech_vault - Technical experiments & knowledge
            seed_vault - Early ideas & prototypes
            case_files_vault - Research & case studies
            personal_vault - Personal notes
            bindings - API-to-UI mapping invariants
            If omitted, searches all collections.
        n_results: Number of results per collection (1-20)

    Returns:
        Formatted search results with document previews and metadata.
    """
    result = await query_memory(
        query=query,
        collections=collections,
        n=n_results,
    )
    return result.get("context", "No results found.")


async def get_peacock_memory_status() -> str:
    """
    Get statistics about the Peacock Unified memory database.
    Use to report how much knowledge is available.
    """
    stats = await get_memory_stats()
    lines = ["=== PEACOCK MEMORY STATUS ==="]
    for name, info in stats.items():
        if isinstance(info, dict):
            count = info.get("count", 0)
            label = info.get("label", name)
            lines.append(f"  {label}: {count:,} documents")
    lines.append("=== END STATUS ===")
    return "\n".join(lines)
