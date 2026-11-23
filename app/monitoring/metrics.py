import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class EngineMetrics:
    total_tokens: int = 0
    total_cost: float = 0.0
    strikes_initiated: int = 0
    strikes_secured: int = 0
    cache_hits: int = 0
    start_time: float = field(default_factory=time.time)

    # Proxy vs Direct bifurcation (TB-018)
    proxy_tokens: int = 0
    proxy_cost: float = 0.0
    proxy_strikes: int = 0
    direct_tokens: int = 0
    direct_cost: float = 0.0
    direct_strikes: int = 0

    # Running plans (TB-018)
    running_plans: int = 0
    queued_plans: int = 0

    # Internal buffers for sliding windows (last 60 seconds)
    _strike_window: list = field(default_factory=list)  # [(timestamp, tokens)]
    _proxy_window: list = field(default_factory=list)   # [(timestamp, tokens)]
    _direct_window: list = field(default_factory=list)  # [(timestamp, tokens)]

    def record_strike(self, tokens: int, cost: float, success: bool, route: str = "direct"):
        """Record a single strike with route awareness."""
        now = time.time()
        self.total_tokens += tokens
        self.total_cost += cost
        self.strikes_initiated += 1

        if route == "proxy":
            self.proxy_tokens += tokens
            self.proxy_cost += cost
            self.proxy_strikes += 1
            self._proxy_window.append((now, tokens))
        else:
            self.direct_tokens += tokens
            self.direct_cost += cost
            self.direct_strikes += 1
            self._direct_window.append((now, tokens))

        if success:
            self.strikes_secured += 1
            self._strike_window.append((now, tokens))

        self._prune_windows(now)

    def record_execution_result(self, result):
        """
        Record a full PlanExecutionResult, bifurcating by route.

        Args:
            result: PlanExecutionResult from plan_executor
        """
        for chunk in result.chunks:
            if chunk.status == "completed":
                tokens = chunk.usage.get("total_tokens", 0)
                cost = chunk.cost
                route = chunk.route or "direct"
                self.record_strike(tokens, cost, success=True, route=route)

    def update_queue_state(self, running: int = 0, queued: int = 0):
        """Update running/queued plan counts for dashboard visibility."""
        self.running_plans = running
        self.queued_plans = queued

    def _prune_windows(self, now: float):
        cutoff = now - 60
        self._strike_window = [s for s in self._strike_window if s[0] > cutoff]
        self._proxy_window = [s for s in self._proxy_window if s[0] > cutoff]
        self._direct_window = [s for s in self._direct_window if s[0] > cutoff]

    def get_realtime_stats(self) -> Dict[str, Any]:
        now = time.time()
        self._prune_windows(now)

        rpm = len(self._strike_window)
        tps = sum(s[1] for s in self._strike_window) / 60.0
        proxy_rpm = len(self._proxy_window)
        proxy_tps = sum(s[1] for s in self._proxy_window) / 60.0
        direct_rpm = len(self._direct_window)
        direct_tps = sum(s[1] for s in self._direct_window) / 60.0

        total_strikes = self.proxy_strikes + self.direct_strikes
        proxy_pct = (self.proxy_strikes / total_strikes * 100) if total_strikes > 0 else 0.0

        return {
            "tokens": self.total_tokens,
            "cost": float(f"{self.total_cost:.6f}"),
            "success_rate": f"{(self.strikes_secured / self.strikes_initiated) * 100:.1f}%" if self.strikes_initiated > 0 else "0%",
            "uptime_seconds": int(now - self.start_time),
            "rpm": rpm,
            "tps": round(tps, 1),
            # TB-018 proxy/direct bifurcation
            "proxy_tokens": self.proxy_tokens,
            "proxy_cost": float(f"{self.proxy_cost:.6f}"),
            "proxy_rpm": proxy_rpm,
            "proxy_tps": round(proxy_tps, 1),
            "proxy_pct": round(proxy_pct, 1),
            "direct_tokens": self.direct_tokens,
            "direct_cost": float(f"{self.direct_cost:.6f}"),
            "direct_rpm": direct_rpm,
            "direct_tps": round(direct_tps, 1),
            # TB-018 queue state
            "running_plans": self.running_plans,
            "queued_plans": self.queued_plans,
        }

    def get_summary(self) -> Dict[str, Any]:
        return self.get_realtime_stats()


# Global Metrics instance
global_metrics = EngineMetrics()
