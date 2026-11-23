"""
PEACOCK ENGINE — Runtime Config Store (TB-021)
Centralized, persistent configuration for provider state and burn-mode pacing.

Scope:
  • JSON-backed config that survives restarts
  • Hot-reload: core modules read values at decision time
  • API surface for read / update / reset

Storage:
  • config/runtime_config.json

References:
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
    "performance_mode": "balanced",
    "providers": {
        "groq": {"enabled": True, "visible": True, "label": "Groq"},
        "opencode-go": {"enabled": True, "visible": True, "label": "OpenCode Go"},
        "opencode-zen": {"enabled": True, "visible": True, "label": "OpenCode Zen"},
        "openrouter": {"enabled": True, "visible": True, "label": "OpenRouter"},
        "ollama": {"enabled": True, "visible": True, "label": "Ollama Cloud"},
        "hetzner": {"enabled": True, "visible": True, "label": "Hetzner"},
        "zai": {"enabled": False, "visible": False, "label": "Z.ai"},
        "zai-coding": {"enabled": False, "visible": False, "label": "Z.ai Coding"},
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

        concurrency = config_store.get("pacer.default_concurrency")
        config_store.set("pacer.default_concurrency", 4)
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
    def pacer(self) -> Dict[str, Any]:
        return self._data.get("pacer", DEFAULT_CONFIG["pacer"]).copy()

    @property
    def cleanup(self) -> Dict[str, Any]:
        return self._data.get("cleanup", DEFAULT_CONFIG["cleanup"]).copy()

    @property
    def performance_mode(self) -> Literal["stealth", "balanced", "apex"]:
        """Get the current Hellcat Protocol performance mode."""
        mode = self._data.get("performance_mode", "balanced")
        if mode not in ("stealth", "balanced", "apex"):
            return "balanced"
        return mode

    def set_performance_mode(self, mode: Literal["stealth", "balanced", "apex"]) -> None:
        """Set the Hellcat Protocol performance mode."""
        if mode not in ("stealth", "balanced", "apex"):
            raise ValueError(f"Invalid performance mode: {mode}. Must be one of: stealth, balanced, apex")
        self._data["performance_mode"] = mode
        self.save()

    def get_performance_mode_info(self) -> Dict[str, Any]:
        """Get full information about the current performance mode."""
        from app.config import PERFORMANCE_MODES
        mode = self.performance_mode
        mode_cfg = PERFORMANCE_MODES.get(mode, PERFORMANCE_MODES["balanced"])
        return {
            "mode": mode,
            "name": mode_cfg["name"],
            "multiplier": mode_cfg["multiplier"],
            "description": self._get_mode_description(mode)
        }

    def _get_mode_description(self, mode: str) -> str:
        descriptions = {
            "stealth": "Maximum safety - 3.0x slower, conservative rate limiting",
            "balanced": "Standard operation - 1.15x buffer for normal workloads",
            "apex": "Maximum throughput - 1.02x at the edge (risk of 429s)"
        }
        return descriptions.get(mode, "Unknown mode")

    @property
    def providers(self) -> Dict[str, Any]:
        """Return the provider state map (enabled + visible flags)."""
        return self._data.get("providers", DEFAULT_CONFIG["providers"]).copy()

    def is_provider_enabled(self, gateway: str) -> bool:
        """Check if a provider is enabled for use."""
        cfg = self._data.get("providers", DEFAULT_CONFIG["providers"]).get(gateway, {})
        return bool(cfg.get("enabled", False)) and bool(cfg.get("visible", False))

    def is_provider_visible(self, gateway: str) -> bool:
        """Check if a provider should be shown in the UI."""
        cfg = self._data.get("providers", DEFAULT_CONFIG["providers"]).get(gateway, {})
        return bool(cfg.get("visible", False))

    def set_provider_state(
        self,
        gateway: str,
        *,
        enabled: Optional[bool] = None,
        visible: Optional[bool] = None,
        label: Optional[str] = None,
    ) -> None:
        """Update the state of a single provider and persist."""
        providers = self._data.setdefault("providers", DEFAULT_CONFIG["providers"].copy())
        if gateway not in providers:
            providers[gateway] = {"enabled": False, "visible": False, "label": gateway}
        if enabled is not None:
            providers[gateway]["enabled"] = enabled
        if visible is not None:
            providers[gateway]["visible"] = visible
        if label is not None:
            providers[gateway]["label"] = label
        self.save()


# Global singleton
config_store = RuntimeConfigStore()
