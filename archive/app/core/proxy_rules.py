"""
PEACOCK ENGINE — Proxy Decision Rules Engine (TB-012)
Configurable, composable rules that decide direct vs proxy routing per chunk.

Scope:
  • Define individual rules as pluggable evaluators
  • Provide default rule set (TPM threshold, RPM threshold, recent 429s, chunk size)
  • Allow runtime add/remove/override without changing the planner
  • Produce a clear route + rationale + triggered rule list for every chunk

References:
  • app.core.rate_limit_tracker (TB-001)

Usage:
    engine = ProxyRulesEngine()
    engine.add_rule(TPMThresholdRule(threshold_pct=90.0))
    engine.remove_rule("chunk_size")
    engine.set_override("chunk_3", "proxy")

    decision = engine.evaluate(
        key_label="G_I7AT",
        model_id="llama-3.3-70b-versatile",
        chunk_tokens=5000,
        chunk_id="chunk_7",
    )
    # decision = {"route": "proxy", "rationale": "...", "triggered_rules": [...]}
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Literal
from abc import ABC, abstractmethod

from app.core.rate_limit_tracker import GroqRateTracker, KeyModelTelemetry
from app.core.config_store import config_store


# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY / PLANNER CONFIG
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RoutingConfig:
    """
    Backward-compatible configuration dataclass for the plan generator.

    Internally converted into a ProxyRulesEngine by PlanGenerator.
    """
    proxy_when_tpm_pct_above: float = 75.0
    proxy_when_rpm_pct_above: float = 70.0
    proxy_on_recent_429s: bool = True
    proxy_chunk_size_threshold: int = 4000
    default_route: Literal["direct", "proxy"] = "direct"
    completion_headroom: int = 1000   # Tokens reserved for model completion
    system_prompt_tokens: int = 100    # Estimated system prompt overhead


# ═══════════════════════════════════════════════════════════════════════════════
# RULE RESULT
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class RuleResult:
    """Outcome of evaluating a single rule."""
    triggered: bool
    rule_name: str
    reason: str


# ═══════════════════════════════════════════════════════════════════════════════
# BASE RULE
# ═══════════════════════════════════════════════════════════════════════════════

class ProxyRule(ABC):
    """
    Abstract base class for proxy routing rules.

    Subclasses implement `evaluate()` and return a RuleResult.
    Rules are stateless and reusable across chunks.
    """

    name: str = "abstract"
    description: str = "Base proxy rule"

    @abstractmethod
    def evaluate(
        self,
        key_label: str,
        model_id: str,
        chunk_tokens: int,
        telemetry: KeyModelTelemetry,
    ) -> RuleResult:
        """Return RuleResult(triggered=True) if this chunk should go via proxy."""
        ...


# ═══════════════════════════════════════════════════════════════════════════════
# BUILT-IN RULES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class TPMThresholdRule(ProxyRule):
    """Proxy when key's TPM utilization percentage exceeds threshold."""
    name: str = "tpm_threshold"
    description: str = "Route via proxy when key TPM utilization exceeds threshold"
    threshold_pct: float = 85.0

    def evaluate(
        self, key_label: str, model_id: str, chunk_tokens: int, telemetry: KeyModelTelemetry
    ) -> RuleResult:
        if telemetry.tpm_limit and telemetry.tpm_pct > self.threshold_pct:
            return RuleResult(
                triggered=True,
                rule_name=self.name,
                reason=f"TPM {telemetry.tpm_pct:.0f}% > {self.threshold_pct:.0f}%",
            )
        return RuleResult(triggered=False, rule_name=self.name, reason="")


@dataclass
class RPMThresholdRule(ProxyRule):
    """Proxy when key's RPM utilization percentage exceeds threshold."""
    name: str = "rpm_threshold"
    description: str = "Route via proxy when key RPM utilization exceeds threshold"
    threshold_pct: float = 80.0

    def evaluate(
        self, key_label: str, model_id: str, chunk_tokens: int, telemetry: KeyModelTelemetry
    ) -> RuleResult:
        if telemetry.rpm_limit and telemetry.rpm_pct > self.threshold_pct:
            return RuleResult(
                triggered=True,
                rule_name=self.name,
                reason=f"RPM {telemetry.rpm_pct:.0f}% > {self.threshold_pct:.0f}%",
            )
        return RuleResult(triggered=False, rule_name=self.name, reason="")


@dataclass
class Recent429Rule(ProxyRule):
    """Proxy when key has recent consecutive 429 errors."""
    name: str = "recent_429s"
    description: str = "Route via proxy when key has recent 429 errors"
    min_consecutive: int = 2

    def evaluate(
        self, key_label: str, model_id: str, chunk_tokens: int, telemetry: KeyModelTelemetry
    ) -> RuleResult:
        if telemetry.consecutive_429s >= self.min_consecutive:
            return RuleResult(
                triggered=True,
                rule_name=self.name,
                reason=f"recent 429s×{telemetry.consecutive_429s} (threshold ≥{self.min_consecutive})",
            )
        return RuleResult(triggered=False, rule_name=self.name, reason="")


@dataclass
class ChunkSizeRule(ProxyRule):
    """Proxy when the chunk itself exceeds a token size threshold."""
    name: str = "chunk_size"
    description: str = "Route via proxy when chunk token count exceeds threshold"
    threshold_tokens: int = 8000

    def evaluate(
        self, key_label: str, model_id: str, chunk_tokens: int, telemetry: KeyModelTelemetry
    ) -> RuleResult:
        if chunk_tokens > self.threshold_tokens:
            return RuleResult(
                triggered=True,
                rule_name=self.name,
                reason=f"chunk {chunk_tokens} tokens > {self.threshold_tokens}",
            )
        return RuleResult(triggered=False, rule_name=self.name, reason="")


@dataclass
class StatusRule(ProxyRule):
    """Proxy when key status is red or exhausted."""
    name: str = "status"
    description: str = "Route via proxy when key telemetry status is red/exhausted"

    def evaluate(
        self, key_label: str, model_id: str, chunk_tokens: int, telemetry: KeyModelTelemetry
    ) -> RuleResult:
        if telemetry.status in ("red", "exhausted"):
            return RuleResult(
                triggered=True,
                rule_name=self.name,
                reason=f"key status is {telemetry.status}",
            )
        return RuleResult(triggered=False, rule_name=self.name, reason="")


# ═══════════════════════════════════════════════════════════════════════════════
# RULES ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def default_rules() -> List[ProxyRule]:
    """Factory for the production default rule set. Reads from runtime config."""
    cfg = config_store.proxy_rules
    rules: List[ProxyRule] = [
        TPMThresholdRule(threshold_pct=cfg.get("tpm_threshold_pct", 85.0)),
        RPMThresholdRule(threshold_pct=cfg.get("rpm_threshold_pct", 80.0)),
        Recent429Rule(min_consecutive=cfg.get("recent_429_min_consecutive", 2)),
        ChunkSizeRule(threshold_tokens=cfg.get("chunk_size_threshold", 8000)),
    ]
    if cfg.get("status_rule_enabled", True):
        rules.append(StatusRule())
    return rules


class ProxyRulesEngine:
    """
    Evaluates a configurable list of ProxyRules and produces a routing decision.

    Supports:
      • Adding/removing rules at runtime
      • Manual per-chunk overrides
      • Rationale generation for auditability
    """

    def __init__(self, rules: Optional[List[ProxyRule]] = None):
        self.rules: List[ProxyRule] = rules if rules is not None else default_rules()
        # chunk_id -> "direct" | "proxy"
        self.overrides: Dict[str, Literal["direct", "proxy"]] = {}

    # ─────────────────────────── RULE MANAGEMENT ───────────────────────────

    def add_rule(self, rule: ProxyRule) -> "ProxyRulesEngine":
        """Add a rule to the engine (chainable)."""
        self.rules.append(rule)
        return self

    def remove_rule(self, name: str) -> bool:
        """Remove the first rule with the given name. Returns True if removed."""
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                self.rules.pop(i)
                return True
        return False

    def list_rules(self) -> List[Dict[str, str]]:
        """Return a human-readable list of active rules."""
        return [{"name": r.name, "description": r.description} for r in self.rules]

    # ─────────────────────────── OVERRIDES ───────────────────────────

    def set_override(
        self, chunk_id: str, route: Literal["direct", "proxy"]
    ) -> "ProxyRulesEngine":
        """Force a specific route for a chunk regardless of rules."""
        self.overrides[chunk_id] = route
        return self

    def clear_override(self, chunk_id: str) -> "ProxyRulesEngine":
        """Remove a manual override."""
        self.overrides.pop(chunk_id, None)
        return self

    def clear_all_overrides(self) -> "ProxyRulesEngine":
        """Remove all manual overrides."""
        self.overrides.clear()
        return self

    # ─────────────────────────── EVALUATION ───────────────────────────

    def evaluate(
        self,
        key_label: str,
        model_id: str,
        chunk_tokens: int,
        chunk_id: str = "",
    ) -> Dict[str, Any]:
        """
        Evaluate all rules and return a structured routing decision.

        Returns:
            {
                "route": "direct" | "proxy",
                "rationale": str,
                "triggered_rules": [{"name": str, "reason": str}, ...],
            }
        """
        # Manual override wins
        if chunk_id and chunk_id in self.overrides:
            return {
                "route": self.overrides[chunk_id],
                "rationale": f"Manual override → {self.overrides[chunk_id]}",
                "triggered_rules": [],
            }

        telemetry = GroqRateTracker.get_telemetry(key_label, model_id)
        triggered: List[RuleResult] = []

        for rule in self.rules:
            result = rule.evaluate(key_label, model_id, chunk_tokens, telemetry)
            if result.triggered:
                triggered.append(result)

        if triggered:
            route: Literal["direct", "proxy"] = "proxy"
            rationale = "Proxy: " + "; ".join(t.reason for t in triggered)
        else:
            route = "direct"
            rationale = "Direct: all rules passed"

        return {
            "route": route,
            "rationale": rationale,
            "triggered_rules": [
                {"name": t.rule_name, "reason": t.reason} for t in triggered
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE
# ═══════════════════════════════════════════════════════════════════════════════

def evaluate_rules(
    key_label: str,
    model_id: str,
    chunk_tokens: int,
    chunk_id: str = "",
    rules: Optional[List[ProxyRule]] = None,
) -> Dict[str, Any]:
    """One-shot rule evaluation using default or custom rules."""
    engine = ProxyRulesEngine(rules=rules)
    return engine.evaluate(key_label, model_id, chunk_tokens, chunk_id)
