"""
SOMA COUNTER — session + stage ID assignment for the Dendritic Factory.

Single source of truth for the human-readable session and stage IDs that
link a pipeline run to the dashboard logs.

- Session IDs: ``SES-001``, ``SES-002``, ... — one counter, never resets.
- Stage IDs:   ``DI-01``, ``IB-03``, ... — short code + per-stage counter,
               never resets.

Counters persist to ``soma_counters.json`` beside the DB so they survive
engine restarts. The module is thread-safe (a lock guards read-modify-write).
"""

import json
import threading
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATE_PATH = BASE_DIR / "soma_counters.json"

# Stage short codes, keyed by the stage slug the pipeline uses (lowercase,
# non-alnum stripped). The pipeline sends these slugs; the engine maps them
# to a short code and a running counter.
STAGE_CODES = {
    "distiller": "DI",
    "introbeaver": "IB",
    "planbeaver": "PB",
    "outrobeaver": "OB",
    "nexus": "NX",
    "spark": "SP",
    "falcon": "FA",
    "drafter": "DR",
    "axonhillock": "AX",
    "scout": "SC",
    "myelinator": "MY",
    "terminalplayer": "TP",
    "saltatorygate": "SG",
    "codepublisher": "CP",
    "seeder": "SE",
}

_lock = threading.Lock()


def _load() -> dict:
    """Load counter state; return a fresh dict when absent or corrupt."""
    if STATE_PATH.exists():
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
        except (OSError, ValueError):
            pass
    return {"session": 0, "stages": {}}


def _save(state: dict) -> None:
    """Atomically persist counter state."""
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(STATE_PATH)


def assign_session() -> str:
    """Return the next session ID, e.g. ``SES-014``."""
    with _lock:
        state = _load()
        state["session"] = state.get("session", 0) + 1
        _save(state)
        return f"SES-{state['session']:03d}"


def stage_code(stage_name: str) -> str:
    """Map a stage slug to its short code (fallback: first 2 letters upper)."""
    slug = (stage_name or "").strip().lower()
    return STAGE_CODES.get(slug, slug[:2].upper() or "XX")


def assign_stage(stage_name: str) -> str:
    """Return the next stage ID for a stage, e.g. ``DI-02``."""
    slug = (stage_name or "").strip().lower() or "unknown"
    code = stage_code(slug)
    with _lock:
        state = _load()
        stages = state.setdefault("stages", {})
        stages[slug] = stages.get(slug, 0) + 1
        _save(state)
        return f"{code}-{stages[slug]:02d}"
