"""
PEACOCK ENGINE — Runtime Config Store (TB-021)
Centralized, persistent configuration for proxy rules, guard thresholds,
and burn-mode pacing behavior.

Scope:
  • JSON-backed config that survives restarts
  • Hot-reload: core modules read values at decision time
  • API surface for read / update / reset

Storage:
  • config/runtime_config.json

References:
  • app.core.proxy_rules     (TB-012)
  • app.core.pre_flight_guard (TB-004)
  • app.core.global_pacer    (TB-009)
"""

import json
from pathlib import Path
from typing import Dict, Any, Literal, Optional


CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "runtime_config.json"


# ═══════════════════════════════════════════════════════════════════════════════
# DEFAULTS
# ═══════════════════════════════════════════════════════════════════════════════

DEFAULT_CONFIG: Dict[str, Any] = {
    "proxy_rules": {
        "tpm_threshold_pct": 85.0,
        "rpm_threshold_pct": 80.0,
        "chunk_size_threshold": 8000,
        "recent_429_min_consecutive": 2,
        "status_rule_enabled": True,
    },
    "guard": {
        "warn_threshold": 0.80,
        "block_threshold": 0.95,
    },
    "pacer": {
        "burn_mode": "BALANCED",
        "tpm_backpressure_pct": 90,
        "default_concurrency": 2,
    },
    "cleanup": {
        "plan_retention_days": 7,
        "stress_retention_days": 3,
        "history_retention_days": 30,
        "interval_hours": 6,
        "storage_warning_mb": 50,
        "storage_critical_mb": 200,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# STORE
# ═══════════════════════════════════════════════════════════════════════════════

class RuntimeConfigStore:
    """
    Thread-safe(ish) singleton-style config store.

    Usage:
        from app.core.config_store import config_store

        tpm = config_store.get("proxy_rules.tpm_threshold_pct")
        config_store.set("proxy_rules.tpm_threshold_pct", 75.0)
        config_store.save()
    """

    _instance: Optional["RuntimeConfigStore"] = None

    def __new__(cls) -> "RuntimeConfigStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data: Dict[str, Any] = {}
            cls._instance._load()
        return cls._instance

    # ─────────────────────────── INTERNAL ───────────────────────────

    def _load(self) -> None:
        if CONFIG_PATH.exists():
            try:
                self._data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}
        # Merge with defaults so missing keys are backfilled
        self._data = self._deep_merge(DEFAULT_CONFIG.copy(), self._data)
        self.save()

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                base[key] = RuntimeConfigStore._deep_merge(base[key].copy(), value)
            else:
                base[key] = value
        return base

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def _get_path(self, dot_path: str) -> Any:
        parts = dot_path.split(".")
        node = self._data
        for part in parts:
            if not isinstance(node, dict) or part not in node:
                raise KeyError(f"Config path not found: {dot_path}")
            node = node[part]
        return node

    def _set_path(self, dot_path: str, value: Any) -> None:
        parts = dot_path.split(".")
        node = self._data
        for part in parts[:-1]:
            if part not in node:
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value

    # ─────────────────────────── PUBLIC API ───────────────────────────

    def get(self, dot_path: str, default: Any = None) -> Any:
        try:
            return self._get_path(dot_path)
        except KeyError:
            return default

    def set(self, dot_path: str, value: Any) -> None:
        self._set_path(dot_path, value)
        self.save()

    def update(self, patch: Dict[str, Any]) -> None:
        self._data = self._deep_merge(self._data, patch)
        self.save()

    def reset(self) -> None:
        self._data = DEFAULT_CONFIG.copy()
        self.save()

    def to_dict(self) -> Dict[str, Any]:
        return self._data.copy()

    # ─────────────────────────── CONVENIENCE ───────────────────────────

    @property
    def burn_mode(self) -> Literal["CONSERVATIVE", "BALANCED", "ULTRA"]:
        mode = self._data.get("pacer", {}).get("burn_mode", "BALANCED")
        if mode not in ("CONSERVATIVE", "BALANCED", "ULTRA"):
            return "BALANCED"
        return mode

    @property
    def proxy_rules(self) -> Dict[str, Any]:
        return self._data.get("proxy_rules", DEFAULT_CONFIG["proxy_rules"]).copy()

    @property
    def guard(self) -> Dict[str, Any]:
        return self._data.get("guard", DEFAULT_CONFIG["guard"]).copy()

    @property
    def pacer(self) -> Dict[str, Any]:
        return self._data.get("pacer", DEFAULT_CONFIG["pacer"]).copy()

    @property
    def cleanup(self) -> Dict[str, Any]:
        return self._data.get("cleanup", DEFAULT_CONFIG["cleanup"]).copy()


# Global singleton
config_store = RuntimeConfigStore()
