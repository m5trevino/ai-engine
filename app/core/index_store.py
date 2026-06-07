"""
PEACOCK ENGINE — SQLite Indexing Layer (TB-023b / TB-025)
Lightweight SQLite index on top of JSON file storage for fast listing.

Design:
  • JSON files remain the source of truth
  • SQLite indexes are rebuilt automatically when empty or missing
  • Indexes are updated on every write operation
  • Listing queries hit SQLite exclusively (no JSON fallback)
  • Pagination via LIMIT + OFFSET

Tables:
  plans          → fast listPlans() with status/model_id filter, pagination
  history_runs   → fast HistoryStore.list_runs() with filters, pagination
  stress_reports → fast StressRunner.list_reports() with pagination

References:
  • app.core.plan_manager  (TB-014)
  • app.core.history       (TB-020)
  • app.core.stress_runner (TB-022)
"""

import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any


INDEX_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "peacock_index.sqlite"
PLANS_DIR = Path(__file__).resolve().parent.parent.parent / "plans"
HISTORY_DIR = Path(__file__).resolve().parent.parent.parent / "history"
STRESS_DIR = Path(__file__).resolve().parent.parent.parent / "stress"


class IndexStore:
    """
    SQLite-backed index for fast listing of plans, history, and stress reports.

    Usage:
        store = IndexStore()
        store.index_plan(plan_id, plan_data_dict)
        plans = store.list_plans(status="pending", model_id="llama-...", limit=50, offset=0)
    """

    def __init__(self):
        INDEX_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(INDEX_DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._ensure_tables()
        self._auto_rebuild_if_empty()

    # ─────────────────────────── SCHEMA ───────────────────────────

    def _ensure_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS plans (
                plan_id TEXT PRIMARY KEY,
                file_path TEXT,
                model_id TEXT,
                status TEXT,
                total_chunks INTEGER DEFAULT 0,
                completed_chunks INTEGER DEFAULT 0,
                overridden_chunks INTEGER DEFAULT 0,
                estimated_total_seconds REAL DEFAULT 0.0,
                makespan_seconds REAL DEFAULT 0.0,
                created_at REAL,
                completed_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_plans_status ON plans(status);
            CREATE INDEX IF NOT EXISTS idx_plans_model_id ON plans(model_id);
            CREATE INDEX IF NOT EXISTS idx_plans_created ON plans(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_plans_status_created ON plans(status, created_at DESC);

            CREATE TABLE IF NOT EXISTS history_runs (
                run_id TEXT PRIMARY KEY,
                plan_id TEXT,
                file_path TEXT,
                model_id TEXT,
                status TEXT,
                total_tokens INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                duration_ms INTEGER DEFAULT 0,
                proxy_chunks INTEGER DEFAULT 0,
                direct_chunks INTEGER DEFAULT 0,
                failed_chunks INTEGER DEFAULT 0,
                skipped_chunks INTEGER DEFAULT 0,
                error_summary TEXT,
                executed_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_history_plan ON history_runs(plan_id);
            CREATE INDEX IF NOT EXISTS idx_history_executed ON history_runs(executed_at DESC);
            CREATE INDEX IF NOT EXISTS idx_history_status ON history_runs(status);
            CREATE INDEX IF NOT EXISTS idx_history_model_id ON history_runs(model_id);
            CREATE INDEX IF NOT EXISTS idx_history_status_executed ON history_runs(status, executed_at DESC);

            CREATE TABLE IF NOT EXISTS stress_reports (
                run_id TEXT PRIMARY KEY,
                status TEXT,
                total_plans INTEGER DEFAULT 0,
                completed_plans INTEGER DEFAULT 0,
                failed_plans INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                total_cost REAL DEFAULT 0.0,
                duration_ms INTEGER DEFAULT 0,
                created_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_stress_created ON stress_reports(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_stress_status ON stress_reports(status);
            CREATE INDEX IF NOT EXISTS idx_stress_status_created ON stress_reports(status, created_at DESC);
        """)
        self._conn.commit()
        self._migrate_tables()

    def _migrate_tables(self) -> None:
        """Add missing columns to existing tables (idempotent)."""
        migrations = [
            ("history_runs", "failed_chunks", "INTEGER DEFAULT 0"),
            ("history_runs", "skipped_chunks", "INTEGER DEFAULT 0"),
            ("history_runs", "error_summary", "TEXT"),
        ]
        for table, column, col_type in migrations:
            try:
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
                self._conn.commit()
            except sqlite3.OperationalError:
                pass  # Column already exists

    def _auto_rebuild_if_empty(self) -> None:
        """If any table is empty, rebuild it from JSON files."""
        counts = self._conn.execute(
            "SELECT (SELECT COUNT(*) FROM plans) AS plans, "
            "(SELECT COUNT(*) FROM history_runs) AS history, "
            "(SELECT COUNT(*) FROM stress_reports) AS stress"
        ).fetchone()
        if counts["plans"] == 0:
            self._rebuild_plans()
        if counts["history"] == 0:
            self._rebuild_history()
        if counts["stress"] == 0:
            self._rebuild_stress()

    def rebuild_all(self) -> None:
        """Force a full rebuild of all indexes from JSON files."""
        self._conn.execute("DELETE FROM plans")
        self._conn.execute("DELETE FROM history_runs")
        self._conn.execute("DELETE FROM stress_reports")
        self._conn.commit()
        self._rebuild_plans()
        self._rebuild_history()
        self._rebuild_stress()

    # ─────────────────────────── REBUILDERS ───────────────────────────

    def _rebuild_plans(self) -> None:
        if not PLANS_DIR.exists():
            return
        for path in PLANS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            self._upsert_plan(data, path.stem)

    def _rebuild_history(self) -> None:
        if not HISTORY_DIR.exists():
            return
        for path in HISTORY_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            self._upsert_history_run(data)

    def _rebuild_stress(self) -> None:
        if not STRESS_DIR.exists():
            return
        for path in STRESS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            self._upsert_stress_report(data)

    # ─────────────────────────── UPSERTS ───────────────────────────

    def _upsert_plan(self, data: Dict[str, Any], plan_id: str) -> None:
        chunks = data.get("chunks", [])
        completed_chunks = sum(1 for c in chunks if c.get("status") == "completed")
        overridden_chunks = sum(1 for c in chunks if c.get("manual_override") is not None)
        self._conn.execute(
            """INSERT INTO plans (plan_id, file_path, model_id, status, total_chunks,
                completed_chunks, overridden_chunks, estimated_total_seconds,
                makespan_seconds, created_at, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(plan_id) DO UPDATE SET
                file_path=excluded.file_path,
                model_id=excluded.model_id,
                status=excluded.status,
                total_chunks=excluded.total_chunks,
                completed_chunks=excluded.completed_chunks,
                overridden_chunks=excluded.overridden_chunks,
                estimated_total_seconds=excluded.estimated_total_seconds,
                makespan_seconds=excluded.makespan_seconds,
                created_at=excluded.created_at,
                completed_at=excluded.completed_at""",
            (
                plan_id,
                data.get("file_path", ""),
                data.get("model_id", ""),
                data.get("status", "pending"),
                data.get("total_chunks", len(chunks)),
                completed_chunks,
                overridden_chunks,
                data.get("estimated_total_seconds", 0.0),
                data.get("makespan_seconds", 0.0),
                data.get("created_at"),
                data.get("completed_at"),
            ),
        )
        self._conn.commit()

    def _upsert_history_run(self, data: Dict[str, Any]) -> None:
        self._conn.execute(
            """INSERT INTO history_runs (run_id, plan_id, file_path, model_id, status,
                total_tokens, total_cost, duration_ms, proxy_chunks, direct_chunks,
                failed_chunks, skipped_chunks, error_summary, executed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                plan_id=excluded.plan_id,
                file_path=excluded.file_path,
                model_id=excluded.model_id,
                status=excluded.status,
                total_tokens=excluded.total_tokens,
                total_cost=excluded.total_cost,
                duration_ms=excluded.duration_ms,
                proxy_chunks=excluded.proxy_chunks,
                direct_chunks=excluded.direct_chunks,
                failed_chunks=excluded.failed_chunks,
                skipped_chunks=excluded.skipped_chunks,
                error_summary=excluded.error_summary,
                executed_at=excluded.executed_at""",
            (
                data.get("run_id", ""),
                data.get("plan_id", ""),
                data.get("file_path", ""),
                data.get("model_id", ""),
                data.get("status", ""),
                data.get("total_tokens", 0),
                data.get("total_cost", 0.0),
                data.get("duration_ms", 0),
                data.get("proxy_chunks", 0),
                data.get("direct_chunks", 0),
                data.get("failed_chunks", 0),
                data.get("skipped_chunks", 0),
                data.get("error_summary"),
                data.get("executed_at", 0.0),
            ),
        )
        self._conn.commit()

    def _upsert_stress_report(self, data: Dict[str, Any]) -> None:
        self._conn.execute(
            """INSERT INTO stress_reports (run_id, status, total_plans, completed_plans,
                failed_plans, total_tokens, total_cost, duration_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                status=excluded.status,
                total_plans=excluded.total_plans,
                completed_plans=excluded.completed_plans,
                failed_plans=excluded.failed_plans,
                total_tokens=excluded.total_tokens,
                total_cost=excluded.total_cost,
                duration_ms=excluded.duration_ms,
                created_at=excluded.created_at""",
            (
                data.get("run_id", ""),
                data.get("status", ""),
                data.get("total_plans", 0),
                data.get("completed_plans", 0),
                data.get("failed_plans", 0),
                data.get("total_tokens", 0),
                data.get("total_cost", 0.0),
                data.get("duration_ms", 0),
                data.get("created_at", 0.0),
            ),
        )
        self._conn.commit()

    # ─────────────────────────── PUBLIC INDEX API ───────────────────────────

    def index_plan(self, plan_id: str, data: Dict[str, Any]) -> None:
        self._upsert_plan(data, plan_id)

    def index_history_run(self, data: Dict[str, Any]) -> None:
        self._upsert_history_run(data)

    def index_stress_report(self, data: Dict[str, Any]) -> None:
        self._upsert_stress_report(data)

    def delete_plan(self, plan_id: str) -> None:
        self._conn.execute("DELETE FROM plans WHERE plan_id = ?", (plan_id,))
        self._conn.commit()

    # ─────────────────────────── LIST QUERIES ───────────────────────────

    def list_plans(
        self,
        status: Optional[str] = None,
        model_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        conditions: List[str] = []
        params: List[Any] = []
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if model_id is not None:
            conditions.append("model_id = ?")
            params.append(model_id)
        sql = "SELECT * FROM plans"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def list_history_runs(
        self,
        limit: int = 50,
        offset: int = 0,
        plan_id: Optional[str] = None,
        status: Optional[str] = None,
        model_id: Optional[str] = None,
        start_date: Optional[float] = None,
        end_date: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        conditions: List[str] = []
        params: List[Any] = []
        if plan_id is not None:
            conditions.append("plan_id = ?")
            params.append(plan_id)
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if model_id is not None:
            conditions.append("model_id = ?")
            params.append(model_id)
        if start_date is not None:
            conditions.append("executed_at >= ?")
            params.append(start_date)
        if end_date is not None:
            conditions.append("executed_at <= ?")
            params.append(end_date)
        sql = "SELECT * FROM history_runs"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY executed_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def list_stress_reports(
        self,
        limit: int = 50,
        offset: int = 0,
        status: Optional[str] = None,
        start_date: Optional[float] = None,
        end_date: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        conditions: List[str] = []
        params: List[Any] = []
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if start_date is not None:
            conditions.append("created_at >= ?")
            params.append(start_date)
        if end_date is not None:
            conditions.append("created_at <= ?")
            params.append(end_date)
        sql = "SELECT * FROM stress_reports"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def count_plans(self, status: Optional[str] = None, model_id: Optional[str] = None) -> int:
        conditions: List[str] = []
        params: List[Any] = []
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if model_id is not None:
            conditions.append("model_id = ?")
            params.append(model_id)
        sql = "SELECT COUNT(*) FROM plans"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        row = self._conn.execute(sql, params).fetchone()
        return row[0] if row else 0

    def count_history_runs(
        self,
        plan_id: Optional[str] = None,
        status: Optional[str] = None,
        model_id: Optional[str] = None,
        start_date: Optional[float] = None,
        end_date: Optional[float] = None,
    ) -> int:
        conditions: List[str] = []
        params: List[Any] = []
        if plan_id is not None:
            conditions.append("plan_id = ?")
            params.append(plan_id)
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if model_id is not None:
            conditions.append("model_id = ?")
            params.append(model_id)
        if start_date is not None:
            conditions.append("executed_at >= ?")
            params.append(start_date)
        if end_date is not None:
            conditions.append("executed_at <= ?")
            params.append(end_date)
        sql = "SELECT COUNT(*) FROM history_runs"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        row = self._conn.execute(sql, params).fetchone()
        return row[0] if row else 0

    def count_stress_reports(
        self,
        status: Optional[str] = None,
        start_date: Optional[float] = None,
        end_date: Optional[float] = None,
    ) -> int:
        conditions: List[str] = []
        params: List[Any] = []
        if status is not None:
            conditions.append("status = ?")
            params.append(status)
        if start_date is not None:
            conditions.append("created_at >= ?")
            params.append(start_date)
        if end_date is not None:
            conditions.append("created_at <= ?")
            params.append(end_date)
        sql = "SELECT COUNT(*) FROM stress_reports"
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        row = self._conn.execute(sql, params).fetchone()
        return row[0] if row else 0


# Global singleton
index_store = IndexStore()
