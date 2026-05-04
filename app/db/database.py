"""
PEACOCK ENGINE - SQLite Database Module
Handles key usage tracking and conversation storage.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# Database location - dynamically find project root
DB_PATH = Path(__file__).parent.parent.parent.resolve() / "peacock.db"


def init_db():
    """Initialize database with all tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    with get_db() as conn:
        # Key usage tracking
        conn.execute("""
            CREATE TABLE IF NOT EXISTS key_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gateway TEXT NOT NULL,
                account TEXT NOT NULL,
                last_used TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                total_prompt_tokens INTEGER DEFAULT 0,
                total_completion_tokens INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(gateway, account)
            )
        """)
        
        # App registrations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS apps (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                default_models TEXT,  -- JSON array
                webhook_url TEXT,
                api_secret TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP
            )
        """)
        
        # Conversations for chat UI
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                title TEXT,
                model_id TEXT NOT NULL,
                key_account TEXT,
                gateway TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Messages within conversations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,  -- 'user' or 'assistant'
                content TEXT NOT NULL,
                tokens_used INTEGER DEFAULT 0,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                model_id TEXT,
                key_account TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        
        # Rich conversation turns (verbatim logging for tool mode + memory mode)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                turn_number INTEGER DEFAULT 1,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                model_id TEXT,
                mode TEXT,  -- 'tools', 'memory', 'raw'
                user_prompt TEXT,
                assistant_response TEXT,
                tool_calls_json TEXT,
                memory_queries_json TEXT,
                usage_json TEXT,
                cost REAL DEFAULT 0.0,
                latency_ms INTEGER DEFAULT 0,
                key_account TEXT,
                gateway TEXT,
                error TEXT,
                metadata_json TEXT,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
            )
        """)
        
        # Batch Missions (Refinery)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS batches (
                id TEXT PRIMARY KEY,
                name TEXT,
                prompt_path TEXT,
                model_id TEXT,
                temperature REAL DEFAULT 0.3,
                output_format TEXT DEFAULT 'markdown',
                status TEXT DEFAULT 'PENDING',  -- PENDING, RUNNING, PAUSED, COMPLETED, ABORTED
                total_items INTEGER DEFAULT 0,
                processed_items INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Individual Strike Items within a batch
        conn.execute("""
            CREATE TABLE IF NOT EXISTS batch_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',  -- PENDING, PROCESSING, SUCCESS, ERROR
                output_path TEXT,
                error_message TEXT,
                tokens_used INTEGER DEFAULT 0,
                latency REAL DEFAULT 0.0,
                raw_output TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
            )
        """)
        
        # Project buckets (persistent working memory for tool-mode builds)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_buckets (
                name TEXT PRIMARY KEY,
                description TEXT,
                items_json TEXT NOT NULL DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Memory retrieval feedback (manual thumbs up/down for learning signal)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT,
                query TEXT,
                doc_id TEXT,
                collection TEXT,
                rating INTEGER NOT NULL,  -- +1 thumbs up, -1 thumbs down
                note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Projects — named working contexts that reference buckets + conversations
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                bucket_name TEXT,
                conversation_id TEXT,
                metadata_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Codebase scans — ingestion jobs for directory analysis
        conn.execute("""
            CREATE TABLE IF NOT EXISTS codebase_scans (
                id TEXT PRIMARY KEY,
                source_path TEXT NOT NULL,
                project_name TEXT,
                status TEXT DEFAULT 'pending',
                progress_pct REAL DEFAULT 0.0,
                total_files INTEGER DEFAULT 0,
                total_lines INTEGER DEFAULT 0,
                languages_json TEXT DEFAULT '{}',
                entry_points_json TEXT DEFAULT '[]',
                manifests_json TEXT DEFAULT '[]',
                file_summaries_json TEXT DEFAULT '[]',
                architecture_doc TEXT,
                dependency_graph TEXT,
                invariant_doc TEXT,
                docs_ingested INTEGER DEFAULT 0,
                error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print(f"[✅ DB] Initialized at {DB_PATH}")


@contextmanager
def get_db():
    """Get database connection context manager."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class KeyUsageDB:
    """Database operations for key usage tracking."""
    
    @staticmethod
    def record_usage(gateway: str, account: str, usage: Dict[str, int]):
        """Record a key usage event."""
        with get_db() as conn:
            # Check if record exists
            existing = conn.execute(
                "SELECT * FROM key_usage WHERE gateway = ? AND account = ?",
                (gateway, account)
            ).fetchone()
            
            if existing:
                conn.execute("""
                    UPDATE key_usage 
                    SET last_used = CURRENT_TIMESTAMP,
                        usage_count = usage_count + 1,
                        total_tokens = total_tokens + ?,
                        total_prompt_tokens = total_prompt_tokens + ?,
                        total_completion_tokens = total_completion_tokens + ?
                    WHERE gateway = ? AND account = ?
                """, (
                    usage.get('total_tokens', 0),
                    usage.get('prompt_tokens', 0),
                    usage.get('completion_tokens', 0),
                    gateway, account
                ))
            else:
                conn.execute("""
                    INSERT INTO key_usage 
                    (gateway, account, last_used, usage_count, total_tokens, 
                     total_prompt_tokens, total_completion_tokens)
                    VALUES (?, ?, CURRENT_TIMESTAMP, 1, ?, ?, ?)
                """, (
                    gateway, account,
                    usage.get('total_tokens', 0),
                    usage.get('prompt_tokens', 0),
                    usage.get('completion_tokens', 0)
                ))
            conn.commit()
    
    @staticmethod
    def get_all_usage() -> Dict[str, List[Dict]]:
        """Get usage stats for all keys, grouped by gateway."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM key_usage ORDER BY gateway, account"
            ).fetchall()
            
            result = {}
            for row in rows:
                gateway = row['gateway']
                if gateway not in result:
                    result[gateway] = []
                
                result[gateway].append({
                    'account': row['account'],
                    'last_used': row['last_used'],
                    'usage_count': row['usage_count'],
                    'total_tokens': row['total_tokens'],
                    'total_prompt_tokens': row['total_prompt_tokens'],
                    'total_completion_tokens': row['total_completion_tokens']
                })
            
            return result
    
    @staticmethod
    def get_gateway_usage(gateway: str) -> List[Dict]:
        """Get usage stats for a specific gateway."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM key_usage WHERE gateway = ? ORDER BY account",
                (gateway,)
            ).fetchall()
            
            return [{
                'account': row['account'],
                'last_used': row['last_used'],
                'usage_count': row['usage_count'],
                'total_tokens': row['total_tokens'],
                'total_prompt_tokens': row['total_prompt_tokens'],
                'total_completion_tokens': row['total_completion_tokens']
            } for row in rows]


class ConversationDB:
    """Database operations for chat conversations."""
    
    @staticmethod
    def create(title: str, model_id: str, key_account: Optional[str] = None, 
               gateway: Optional[str] = None, conv_id: Optional[str] = None) -> str:
        """Create a new conversation. Returns conversation ID."""
        import uuid
        conv_id = conv_id or str(uuid.uuid4())[:8]
        
        with get_db() as conn:
            conn.execute("""
                INSERT INTO conversations (id, title, model_id, key_account, gateway)
                VALUES (?, ?, ?, ?, ?)
            """, (conv_id, title or f"Chat {conv_id}", model_id, key_account, gateway))
            conn.commit()
        
        return conv_id
    
    @staticmethod
    def add_message(conv_id: str, role: str, content: str, 
                    tokens_used: int = 0, prompt_tokens: int = 0,
                    completion_tokens: int = 0, model_id: Optional[str] = None,
                    key_account: Optional[str] = None):
        """Add a message to a conversation."""
        with get_db() as conn:
            conn.execute("""
                INSERT INTO messages 
                (conversation_id, role, content, tokens_used, prompt_tokens,
                 completion_tokens, model_id, key_account)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (conv_id, role, content, tokens_used, prompt_tokens,
                  completion_tokens, model_id, key_account))
            
            # Update conversation timestamp
            conn.execute("""
                UPDATE conversations 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (conv_id,))
            
            conn.commit()
    
    @staticmethod
    def get_conversations(limit: int = 50) -> List[Dict]:
        """Get all conversations, most recent first."""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT * FROM conversations 
                ORDER BY updated_at DESC 
                LIMIT ?
            """, (limit,)).fetchall()
            
            return [dict(row) for row in rows]
    
    @staticmethod
    def get_messages(conv_id: str) -> List[Dict]:
        """Get all messages for a conversation."""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT * FROM messages 
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
            """, (conv_id,)).fetchall()
            
            return [dict(row) for row in rows]
    
    @staticmethod
    def delete_conversation(conv_id: str):
        """Delete a conversation and all its messages."""
        with get_db() as conn:
            conn.execute("DELETE FROM conversations WHERE id = ?", (conv_id,))
            conn.commit()


class ConversationTurnDB:
    """Rich verbatim logging for every chat turn (tool calls, memory, responses)."""
    
    @staticmethod
    def create_turn(
        conversation_id: str,
        turn_number: int,
        model_id: str,
        mode: str,
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
        """Log a complete conversation turn. Returns turn row id."""
        with get_db() as conn:
            cursor = conn.execute("""
                INSERT INTO conversation_turns 
                (conversation_id, turn_number, model_id, mode, user_prompt,
                 assistant_response, tool_calls_json, memory_queries_json,
                 usage_json, cost, latency_ms, key_account, gateway, error, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id,
                turn_number,
                model_id,
                mode,
                user_prompt,
                assistant_response,
                json.dumps(tool_calls or []),
                json.dumps(memory_queries or []),
                json.dumps(usage or {}),
                cost,
                latency_ms,
                key_account,
                gateway,
                error,
                json.dumps(metadata or {}),
            ))
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def get_turns(conv_id: str) -> List[Dict]:
        """Get all turns for a conversation in order."""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT * FROM conversation_turns 
                WHERE conversation_id = ? 
                ORDER BY turn_number ASC
            """, (conv_id,)).fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    def get_latest_turn_number(conv_id: str) -> int:
        """Get the highest turn number for a conversation."""
        with get_db() as conn:
            row = conn.execute("""
                SELECT MAX(turn_number) as max_turn FROM conversation_turns 
                WHERE conversation_id = ?
            """, (conv_id,)).fetchone()
            return row['max_turn'] or 0
    
    @staticmethod
    def list_conversations(limit: int = 50) -> List[Dict]:
        """Get distinct conversations with aggregate metadata from conversation_turns."""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT 
                    conversation_id,
                    COUNT(*) as turn_count,
                    MAX(timestamp) as last_active,
                    MIN(timestamp) as created_at,
                    MAX(model_id) as model_id,
                    GROUP_CONCAT(DISTINCT mode) as modes,
                    SUM(cost) as total_cost,
                    SUM(latency_ms) as total_latency_ms
                FROM conversation_turns
                GROUP BY conversation_id
                ORDER BY last_active DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    def get_conversation_turns(conv_id: str) -> List[Dict]:
        """Get full turn data for a conversation (with parsed JSON fields)."""
        with get_db() as conn:
            rows = conn.execute("""
                SELECT * FROM conversation_turns 
                WHERE conversation_id = ? 
                ORDER BY turn_number ASC
            """, (conv_id,)).fetchall()
            result = []
            for row in rows:
                turn = dict(row)
                turn["tool_calls"] = json.loads(turn.get("tool_calls_json") or "[]")
                turn["memory_queries"] = json.loads(turn.get("memory_queries_json") or "[]")
                turn["usage"] = json.loads(turn.get("usage_json") or "{}")
                turn["metadata"] = json.loads(turn.get("metadata_json") or "{}")
                result.append(turn)
            return result
    
    @staticmethod
    def export_turn_to_markdown(turn: Dict) -> str:
        """Convert a turn dict to markdown format for disk export."""
        lines = [
            f"---",
            f"conversation_id: {turn.get('conversation_id', '')}",
            f"turn: {turn.get('turn_number', '')}",
            f"timestamp: {turn.get('timestamp', '')}",
            f"model: {turn.get('model_id', '')}",
            f"mode: {turn.get('mode', '')}",
            f"gateway: {turn.get('gateway', '')}",
            f"key_account: {turn.get('key_account', '')}",
            f"cost: {turn.get('cost', 0)}",
            f"latency_ms: {turn.get('latency_ms', 0)}",
            f"---",
            f"",
            f"## User",
            f"{turn.get('user_prompt', '')}",
            f"",
        ]
        
        tool_calls = json.loads(turn.get('tool_calls_json') or '[]')
        if tool_calls:
            lines.append("## Tool Calls")
            for tc in tool_calls:
                lines.append(f"### {tc.get('tool', 'unknown')}")
                lines.append(f"- Arguments: `{json.dumps(tc.get('args', {}))}`")
                lines.append(f"- Result preview: {str(tc.get('result', ''))[:500]}")
                lines.append("")
        
        memory_queries = json.loads(turn.get('memory_queries_json') or '[]')
        if memory_queries:
            lines.append("## Memory Queries")
            for mq in memory_queries:
                lines.append(f"- Query: `{mq.get('query', '')}` | Collections: {mq.get('collections', [])} | Hits: {mq.get('hits', 0)}")
            lines.append("")
        
        lines.extend([
            f"## Assistant",
            f"{turn.get('assistant_response', '')}",
            f"",
            f"---",
            f"",
        ])
        return "\n".join(lines)


class BatchDB:
    """Database operations for Refinery Batch missions."""

    @staticmethod
    def create_batch(batch_id: str, name: str, prompt_path: str, model_id: str, 
                     total_items: int, settings: Dict[str, Any] = None) -> str:
        """Create a new mission batch."""
        settings = settings or {}
        with get_db() as conn:
            conn.execute("""
                INSERT INTO batches (id, name, prompt_path, model_id, temperature, output_format, total_items)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id, 
                name, 
                prompt_path, 
                model_id, 
                settings.get('temperature', 0.3),
                settings.get('output_format', 'markdown'),
                total_items
            ))
            conn.commit()
        return batch_id

    @staticmethod
    def add_items(batch_id: str, file_paths: List[str]):
        """Add multiple items to a batch in bulk."""
        with get_db() as conn:
            conn.executemany(
                "INSERT INTO batch_items (batch_id, file_path) VALUES (?, ?)",
                [(batch_id, path) for path in file_paths]
            )
            conn.commit()

    @staticmethod
    def update_item(item_id: int, status: str, output_path: str = None, 
                    error: str = None, tokens: int = 0, latency: float = 0.0,
                    raw: str = None):
        """Update the status of an individual item strike."""
        with get_db() as conn:
            conn.execute("""
                UPDATE batch_items 
                SET status = ?, output_path = ?, error_message = ?, 
                    tokens_used = ?, latency = ?, raw_output = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, output_path, error, tokens, latency, raw, item_id))
            
            # Update batch progress
            batch_id = conn.execute(
                "SELECT batch_id FROM batch_items WHERE id = ?", (item_id,)
            ).fetchone()['batch_id']
            
            processed = conn.execute(
                "SELECT COUNT(*) as cnt FROM batch_items WHERE batch_id = ? AND status IN ('SUCCESS', 'ERROR')",
                (batch_id,)
            ).fetchone()['cnt']
            
            errors = conn.execute(
                "SELECT COUNT(*) as cnt FROM batch_items WHERE batch_id = ? AND status = 'ERROR'",
                (batch_id,)
            ).fetchone()['cnt']
            
            conn.execute("""
                UPDATE batches 
                SET processed_items = ?, error_count = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (processed, errors, batch_id))
            
            conn.commit()

    @staticmethod
    def get_batch(batch_id: str) -> Optional[Dict]:
        """Get full batch data and its items."""
        with get_db() as conn:
            batch = conn.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
            if not batch:
                return None
            
            items = conn.execute(
                "SELECT * FROM batch_items WHERE batch_id = ? ORDER BY id ASC", 
                (batch_id,)
            ).fetchall()
            
            res = dict(batch)
            res['items'] = [dict(item) for item in items]
            return res

    @staticmethod
    def update_batch_status(batch_id: str, status: str):
        """Update global status of a mission."""
        with get_db() as conn:
            conn.execute(
                "UPDATE batches SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (status, batch_id)
            )
            conn.commit()

    @staticmethod
    def get_history(limit: int = 20) -> List[Dict]:
        """Get recent missions."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM batches ORDER BY created_at DESC LIMIT ?", 
                (limit,)
            ).fetchall()
            return [dict(row) for row in rows]


class ProjectBucketDB:
    """Persistent storage for project buckets (tool-mode working memory)."""
    
    @staticmethod
    def save_bucket(name: str, description: str, items: Dict[str, Any]):
        """Upsert a bucket to SQLite."""
        with get_db() as conn:
            conn.execute("""
                INSERT INTO project_buckets (name, description, items_json, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(name) DO UPDATE SET
                    description = excluded.description,
                    items_json = excluded.items_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (name, description or '', json.dumps(items)))
            conn.commit()
    
    @staticmethod
    def load_bucket(name: str) -> Optional[Dict]:
        """Load a single bucket from SQLite."""
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM project_buckets WHERE name = ?", (name,)
            ).fetchone()
            if not row:
                return None
            return {
                "name": row["name"],
                "description": row["description"],
                "items": json.loads(row["items_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
    
    @staticmethod
    def load_all_buckets() -> Dict[str, Dict]:
        """Load all buckets into memory dict format."""
        with get_db() as conn:
            rows = conn.execute("SELECT * FROM project_buckets").fetchall()
            result = {}
            for row in rows:
                result[row["name"]] = {
                    "description": row["description"] or "",
                    "items": json.loads(row["items_json"]),
                }
            return result
    
    @staticmethod
    def delete_bucket(name: str):
        """Remove a bucket from persistent storage."""
        with get_db() as conn:
            conn.execute("DELETE FROM project_buckets WHERE name = ?", (name,))
            conn.commit()
    
    @staticmethod
    def list_buckets() -> List[Dict]:
        """List all buckets with metadata."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT name, description, created_at, updated_at FROM project_buckets ORDER BY updated_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]


class MemoryFeedbackDB:
    """Manual feedback on memory retrieval quality."""
    
    @staticmethod
    def record_feedback(conversation_id: str, query: str, doc_id: str, collection: str, rating: int, note: str = ""):
        """Record a thumbs up (+1) or thumbs down (-1) for a retrieved doc."""
        with get_db() as conn:
            conn.execute("""
                INSERT INTO memory_feedback (conversation_id, query, doc_id, collection, rating, note)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (conversation_id or '', query or '', doc_id or '', collection or '', rating, note or ''))
            conn.commit()
    
    @staticmethod
    def get_feedback_for_doc(doc_id: str, collection: str) -> List[Dict]:
        """Get all feedback for a specific document."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_feedback WHERE doc_id = ? AND collection = ? ORDER BY created_at DESC",
                (doc_id, collection)
            ).fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    def get_recent_feedback(limit: int = 50) -> List[Dict]:
        """Get recent feedback entries."""
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM memory_feedback ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
    
    @staticmethod
    def get_stats() -> Dict:
        """Get aggregate feedback stats."""
        with get_db() as conn:
            total = conn.execute("SELECT COUNT(*) as c FROM memory_feedback").fetchone()["c"]
            positive = conn.execute("SELECT COUNT(*) as c FROM memory_feedback WHERE rating = 1").fetchone()["c"]
            negative = conn.execute("SELECT COUNT(*) as c FROM memory_feedback WHERE rating = -1").fetchone()["c"]
            return {"total": total, "positive": positive, "negative": negative}


class ProjectDB:
    """Named projects that wrap buckets + conversation context."""
    
    @staticmethod
    def create(project_id: str, name: str, description: str = "", bucket_name: str = "",
               conversation_id: str = "", metadata: Dict = None) -> str:
        with get_db() as conn:
            conn.execute("""
                INSERT INTO projects (id, name, description, bucket_name, conversation_id, metadata_json, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    bucket_name = excluded.bucket_name,
                    conversation_id = excluded.conversation_id,
                    metadata_json = excluded.metadata_json,
                    updated_at = CURRENT_TIMESTAMP
            """, (project_id, name, description or '', bucket_name or '', conversation_id or '',
                  json.dumps(metadata or {})))
            conn.commit()
        return project_id
    
    @staticmethod
    def list_projects(limit: int = 100) -> List[Dict]:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT * FROM projects ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
            result = []
            for row in rows:
                d = dict(row)
                d["metadata"] = json.loads(d.get("metadata_json") or "{}")
                del d["metadata_json"]
                result.append(d)
            return result
    
    @staticmethod
    def get_project(project_id: str) -> Optional[Dict]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["metadata"] = json.loads(d.get("metadata_json") or "{}")
            del d["metadata_json"]
            return d
    
    @staticmethod
    def delete_project(project_id: str):
        with get_db() as conn:
            conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()


class CodebaseScanDB:
    """Track codebase analysis scan jobs."""
    
    @staticmethod
    def create(scan_id: str, source_path: str, project_name: str = ""):
        with get_db() as conn:
            conn.execute("""
                INSERT INTO codebase_scans (id, source_path, project_name, status, progress_pct)
                VALUES (?, ?, ?, 'pending', 0.0)
            """, (scan_id, source_path, project_name or ""))
            conn.commit()
    
    @staticmethod
    def update(scan):
        """Persist a CodebaseScan object (duck-typed)."""
        with get_db() as conn:
            conn.execute("""
                UPDATE codebase_scans SET
                    status = ?,
                    progress_pct = ?,
                    total_files = ?,
                    total_lines = ?,
                    languages_json = ?,
                    entry_points_json = ?,
                    manifests_json = ?,
                    file_summaries_json = ?,
                    architecture_doc = ?,
                    dependency_graph = ?,
                    invariant_doc = ?,
                    docs_ingested = ?,
                    error = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                scan.status,
                scan.progress_pct,
                scan.total_files,
                scan.total_lines,
                json.dumps(scan.languages),
                json.dumps(scan.entry_points),
                json.dumps(scan.manifests),
                json.dumps(scan.file_summaries),
                scan.architecture_doc,
                scan.dependency_graph,
                scan.invariant_doc,
                scan.docs_ingested,
                scan.error,
                scan.scan_id,
            ))
            conn.commit()
    
    @staticmethod
    def get(scan_id: str) -> Optional[Dict]:
        with get_db() as conn:
            row = conn.execute("SELECT * FROM codebase_scans WHERE id = ?", (scan_id,)).fetchone()
            if not row:
                return None
            d = dict(row)
            d["languages"] = json.loads(d.get("languages_json") or "{}")
            d["entry_points"] = json.loads(d.get("entry_points_json") or "[]")
            d["manifests"] = json.loads(d.get("manifests_json") or "[]")
            d["file_summaries"] = json.loads(d.get("file_summaries_json") or "[]")
            del d["languages_json"]
            del d["entry_points_json"]
            del d["manifests_json"]
            del d["file_summaries_json"]
            return d
    
    @staticmethod
    def list_scans(limit: int = 50) -> List[Dict]:
        with get_db() as conn:
            rows = conn.execute("""
                SELECT id, source_path, project_name, status, progress_pct,
                       total_files, total_lines, docs_ingested, error,
                       created_at, updated_at
                FROM codebase_scans
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]


# Initialize on import
init_db()
