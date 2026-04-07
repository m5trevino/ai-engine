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
               gateway: Optional[str] = None) -> str:
        """Create a new conversation. Returns conversation ID."""
        import uuid
        conv_id = str(uuid.uuid4())[:8]
        
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


# Initialize on import
init_db()
