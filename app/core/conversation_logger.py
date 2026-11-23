"""
CONVERSATION LOGGER — Verbatim disk + DB logging for every chat turn.

Saves structured markdown to disk for easy ChromaDB ingestion later.
Format is frontmatter + sections so chunking pipelines can parse it.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.db.database import ConversationTurnDB

# Base directory for conversation exports
LOG_DIR = Path(__file__).parent.parent.parent.resolve() / "logs" / "conversations"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def log_turn(
    conversation_id: str,
    model_id: str,
    mode: str,  # 'tools', 'memory', 'raw'
    user_prompt: str,
    assistant_response: str,
    tool_calls: List[Dict] = None,
    memory_queries: List[Dict] = None,
    usage: Dict[str, int] = None,
    cost: float = 0.0,
    latency_ms: int = 0,
    key_account: str = None,
    gateway: str = None,
    error: str = None,
    metadata: Dict = None,
) -> int:
    """
    Log a complete turn to both SQLite and disk.
    Returns the turn database row ID.
    """
    # Get next turn number
    turn_number = ConversationTurnDB.get_latest_turn_number(conversation_id) + 1
    
    # Save to DB
    row_id = ConversationTurnDB.create_turn(
        conversation_id=conversation_id,
        turn_number=turn_number,
        model_id=model_id,
        mode=mode,
        user_prompt=user_prompt,
        assistant_response=assistant_response,
        tool_calls=tool_calls,
        memory_queries=memory_queries,
        usage=usage,
        cost=cost,
        latency_ms=latency_ms,
        key_account=key_account,
        gateway=gateway,
        error=error,
        metadata=metadata,
    )
    
    # Save to disk as markdown
    _write_to_disk(
        conversation_id=conversation_id,
        turn_number=turn_number,
        model_id=model_id,
        mode=mode,
        user_prompt=user_prompt,
        assistant_response=assistant_response,
        tool_calls=tool_calls,
        memory_queries=memory_queries,
        usage=usage,
        cost=cost,
        latency_ms=latency_ms,
        key_account=key_account,
        gateway=gateway,
        error=error,
        metadata=metadata,
    )
    
    return row_id


def _write_to_disk(**kwargs) -> Path:
    """Write a single turn to disk as markdown."""
    today = datetime.now().strftime("%Y-%m-%d")
    day_dir = LOG_DIR / today
    day_dir.mkdir(exist_ok=True)
    
    conv_id = kwargs["conversation_id"]
    turn_num = kwargs["turn_number"]
    filename = day_dir / f"{conv_id}_turn_{turn_num:03d}.md"
    
    lines = [
        "---",
        f"conversation_id: {conv_id}",
        f"turn: {turn_num}",
        f"timestamp: {datetime.now().isoformat()}",
        f"model: {kwargs.get('model_id', '')}",
        f"mode: {kwargs.get('mode', '')}",
        f"gateway: {kwargs.get('gateway', '')}",
        f"key_account: {kwargs.get('key_account', '')}",
        f"cost: {kwargs.get('cost', 0)}",
        f"latency_ms: {kwargs.get('latency_ms', 0)}",
        f"platform: PEACOCK",
        f"project: {kwargs.get('metadata', {}).get('project_bucket', 'unknown') if kwargs.get('metadata') else 'unknown'}",
        "has_code_blocks: 'true'",
        "---",
        "",
        f"# Turn {turn_num} — {kwargs.get('mode', 'chat').upper()}",
        "",
        "## User",
        f"{kwargs.get('user_prompt', '')}",
        "",
    ]
    
    tool_calls = kwargs.get("tool_calls") or []
    if tool_calls:
        lines.extend([
            "## Tool Calls",
            "",
        ])
        for tc in tool_calls:
            tool_name = tc.get("tool", "unknown")
            args = tc.get("args", {})
            result = str(tc.get("result", ""))
            lines.extend([
                f"### {tool_name}",
                f"```json",
                f"{json.dumps(args, indent=2)}",
                f"```",
                f"**Result:**",
                f"```",
                f"{result[:2000]}{'...' if len(result) > 2000 else ''}",
                f"```",
                "",
            ])
    
    memory_queries = kwargs.get("memory_queries") or []
    if memory_queries:
        lines.extend([
            "## Memory Queries",
            "",
        ])
        for mq in memory_queries:
            lines.append(f"- **Query:** `{mq.get('query', '')}` | Collections: {mq.get('collections', [])} | Hits: {mq.get('hits', 0)}")
        lines.append("")
    
    usage = kwargs.get("usage") or {}
    if usage:
        lines.extend([
            "## Usage",
            f"- Prompt tokens: {usage.get('prompt_tokens', 0)}",
            f"- Completion tokens: {usage.get('completion_tokens', 0)}",
            f"- Total tokens: {usage.get('total_tokens', 0)}",
            "",
        ])
    
    lines.extend([
        "## Assistant",
        f"{kwargs.get('assistant_response', '')}",
        "",
        "---",
        "",
    ])
    
    filename.write_text("\n".join(lines), encoding="utf-8")
    return filename


def export_conversation_markdown(conv_id: str) -> str:
    """Export an entire conversation as a single markdown string."""
    turns = ConversationTurnDB.get_turns(conv_id)
    if not turns:
        return ""
    
    sections = [
        "---",
        f"conversation_id: {conv_id}",
        f"exported_at: {datetime.now().isoformat()}",
        f"turn_count: {len(turns)}",
        "platform: PEACOCK",
        "---",
        "",
        f"# Conversation: {conv_id}",
        "",
    ]
    
    for turn in turns:
        sections.append(ConversationTurnDB.export_turn_to_markdown(turn))
    
    return "\n".join(sections)


def get_conversation_log_path(conv_id: str) -> Optional[Path]:
    """Find the disk log directory for a conversation."""
    for day_dir in LOG_DIR.iterdir():
        if day_dir.is_dir():
            matches = list(day_dir.glob(f"{conv_id}_turn_*.md"))
            if matches:
                return day_dir
    return None
