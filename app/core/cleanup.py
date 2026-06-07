"""
PEACOCK ENGINE — Automated Cleanup / TTL (TB-023a / TB-024)
Non-destructive deletion of old plans and stress reports based on retention policy.

Scope:
  • Delete plan files older than plan_retention_days
  • Delete stress reports older than stress_retention_days
  • Delete history audit files older than history_retention_days
  • Run on startup and on a periodic schedule
  • Log every deletion for auditability
  • Purge orphaned SQLite index entries
  • Storage stats for dashboard

References:
  • app.core.plan_manager    (TB-014) — plans/ directory
  • app.core.stress_runner   (TB-022) — stress/ directory
  • app.core.history         (TB-020) — history/ directory
  • app.core.index_store     (TB-023b) — SQLite index
  • app.core.config_store    (TB-024) — runtime TTL config
"""

import os
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any

logger = logging.getLogger("peacock.cleanup")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(name)s] %(message)s"))
    logger.addHandler(handler)

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION (lazy load from config_store to avoid import-time dependency)
# ═══════════════════════════════════════════════════════════════════════════════

PLANS_DIR = Path(__file__).resolve().parent.parent.parent / "plans"
STRESS_DIR = Path(__file__).resolve().parent.parent.parent / "stress"
HISTORY_DIR = Path(__file__).resolve().parent.parent.parent / "history"


def _get_cleanup_config() -> Dict[str, int]:
    """Read TTL settings from config_store at call time."""
    try:
        from app.core.config_store import config_store
        return config_store.cleanup
    except Exception:
        return {
            "plan_retention_days": 7,
            "stress_retention_days": 3,
            "history_retention_days": 30,
            "interval_hours": 6,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CLEANUP MANAGER
# ═══════════════════════════════════════════════════════════════════════════════

class CleanupManager:
    """
    Non-destructive TTL cleanup for plan and stress storage.

    Usage:
        mgr = CleanupManager()
        summary = mgr.run_now()
        asyncio.create_task(mgr.start_scheduler())
    """

    def __init__(self):
        self._task: asyncio.Task | None = None
        self._stop = False

    # ─────────────────────────── CORE CLEANUP ───────────────────────────

    def run_now(self) -> Dict[str, int]:
        """
        Execute cleanup immediately. Returns summary of deletions.
        """
        cfg = _get_cleanup_config()
        summary: Dict[str, int] = {"plans": 0, "stress": 0, "history": 0, "bytes_freed": 0}
        deleted_plan_ids: List[str] = []
        deleted_history_ids: List[str] = []
        deleted_stress_ids: List[str] = []

        now = time.time()

        # Plans
        plan_cutoff = now - (cfg["plan_retention_days"] * 86400)
        for path in PLANS_DIR.glob("*.json"):
            try:
                mtime = path.stat().st_mtime
                if mtime < plan_cutoff:
                    size = path.stat().st_size
                    path.unlink()
                    summary["plans"] += 1
                    summary["bytes_freed"] += size
                    deleted_plan_ids.append(path.stem)
                    logger.info(f"Deleted old plan: {path.name} (age={(now - mtime)/86400:.1f}d)")
            except OSError as e:
                logger.warning(f"Failed to delete plan {path.name}: {e}")

        # Stress reports
        stress_cutoff = now - (cfg["stress_retention_days"] * 86400)
        for path in STRESS_DIR.glob("*.json"):
            try:
                mtime = path.stat().st_mtime
                if mtime < stress_cutoff:
                    size = path.stat().st_size
                    path.unlink()
                    summary["stress"] += 1
                    summary["bytes_freed"] += size
                    deleted_stress_ids.append(path.stem)
                    logger.info(f"Deleted old stress report: {path.name} (age={(now - mtime)/86400:.1f}d)")
            except OSError as e:
                logger.warning(f"Failed to delete stress report {path.name}: {e}")

        # History audit files
        history_cutoff = now - (cfg["history_retention_days"] * 86400)
        for path in HISTORY_DIR.glob("*.json"):
            try:
                mtime = path.stat().st_mtime
                if mtime < history_cutoff:
                    size = path.stat().st_size
                    path.unlink()
                    summary["history"] += 1
                    summary["bytes_freed"] += size
                    deleted_history_ids.append(path.stem)
                    logger.info(f"Deleted old history entry: {path.name} (age={(now - mtime)/86400:.1f}d)")
            except OSError as e:
                logger.warning(f"Failed to delete history entry {path.name}: {e}")

        # Purge orphaned index entries
        self._purge_index(deleted_plan_ids, deleted_history_ids, deleted_stress_ids)

        if summary["plans"] + summary["stress"] + summary["history"] > 0:
            logger.info(
                f"Cleanup complete: {summary['plans']} plans, "
                f"{summary['stress']} stress reports, {summary['history']} history entries removed. "
                f"Freed {summary['bytes_freed'] / 1024:.1f} KB"
            )
        else:
            logger.info("Cleanup complete: nothing to delete")

        return summary

    def _purge_index(self, plan_ids: List[str], history_ids: List[str], stress_ids: List[str]) -> None:
        """Remove deleted items from the SQLite index."""
        try:
            from app.core.index_store import index_store
            for pid in plan_ids:
                index_store.delete_plan(pid)
            if history_ids:
                placeholders = ",".join("?" * len(history_ids))
                index_store._conn.execute(f"DELETE FROM history_runs WHERE run_id IN ({placeholders})", history_ids)
                index_store._conn.commit()
            if stress_ids:
                placeholders = ",".join("?" * len(stress_ids))
                index_store._conn.execute(f"DELETE FROM stress_reports WHERE run_id IN ({placeholders})", stress_ids)
                index_store._conn.commit()
            if plan_ids or history_ids or stress_ids:
                logger.info(f"Index purge: {len(plan_ids)} plans, {len(history_ids)} history, {len(stress_ids)} stress")
        except Exception as e:
            logger.warning(f"Index purge failed: {e}")

    # ─────────────────────────── SCHEDULER ───────────────────────────

    async def start_scheduler(self) -> None:
        """
        Background task that runs cleanup every N hours.
        Call stop_scheduler() to halt.
        """
        cfg = _get_cleanup_config()
        interval_seconds = cfg.get("interval_hours", 6) * 3600
        while not self._stop:
            await asyncio.sleep(interval_seconds)
            if not self._stop:
                self.run_now()

    def stop_scheduler(self) -> None:
        """Signal the scheduler to stop after the next sleep."""
        self._stop = True
        if self._task and not self._task.done():
            self._task.cancel()

    def run_on_startup(self) -> Dict[str, int]:
        """Convenience wrapper for startup-time cleanup."""
        cfg = _get_cleanup_config()
        logger.info(
            f"Startup cleanup starting (plans={cfg['plan_retention_days']}d, "
            f"stress={cfg['stress_retention_days']}d, history={cfg['history_retention_days']}d)"
        )
        return self.run_now()

    # ─────────────────────────── STORAGE STATS ───────────────────────────

    @staticmethod
    def storage_stats() -> Dict[str, Any]:
        """
        Return current storage statistics for dashboard.
        """
        stats = {
            "plans": {"count": 0, "bytes": 0, "oldest_mtime": None},
            "stress": {"count": 0, "bytes": 0, "oldest_mtime": None},
            "history": {"count": 0, "bytes": 0, "oldest_mtime": None},
            "total_bytes": 0,
        }
        for key, directory in [("plans", PLANS_DIR), ("stress", STRESS_DIR), ("history", HISTORY_DIR)]:
            if not directory.exists():
                continue
            for path in directory.glob("*.json"):
                try:
                    st = path.stat()
                    stats[key]["count"] += 1
                    stats[key]["bytes"] += st.st_size
                    if stats[key]["oldest_mtime"] is None or st.st_mtime < stats[key]["oldest_mtime"]:
                        stats[key]["oldest_mtime"] = st.st_mtime
                except OSError:
                    continue
            stats["total_bytes"] += stats[key]["bytes"]
        return stats


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE
# ═══════════════════════════════════════════════════════════════════════════════

def run_cleanup_now() -> Dict[str, int]:
    return CleanupManager().run_now()
