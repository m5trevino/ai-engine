import time
from typing import Dict, Any
from dataclasses import dataclass, field

@dataclass
class EngineMetrics:
    total_tokens: int = 0
    total_cost: float = 0.0
    strikes_initiated: int = 0
    strikes_secured: int = 0
    cache_hits: int = 0
    start_time: float = field(default_factory=time.time)
    
    # Internal buffers for sliding windows (last 60 seconds)
    _strike_window: list = field(default_factory=list) # [(timestamp, tokens)]

    def record_strike(self, tokens: int, cost: float, success: bool):
        now = time.time()
        self.total_tokens += tokens
        self.total_cost += cost
        self.strikes_initiated += 1
        if success:
            self.strikes_secured += 1
            self._strike_window.append((now, tokens))
        
        # Prune old data
        self._prune_windows(now)

    def _prune_windows(self, now: float):
        cutoff = now - 60
        self._strike_window = [s for s in self._strike_window if s[0] > cutoff]

    def get_realtime_stats(self) -> Dict[str, Any]:
        now = time.time()
        self._prune_windows(now)
        
        rpm = len(self._strike_window)
        tps = sum(s[1] for s in self._strike_window) / 60.0
        
        return {
            "tokens": self.total_tokens,
            "cost": float(f"{self.total_cost:.6f}"),
            "success_rate": f"{(self.strikes_secured/self.strikes_initiated)*100:.1f}%" if self.strikes_initiated > 0 else "0%",
            "uptime_seconds": int(now - self.start_time),
            "rpm": rpm,
            "tps": round(tps, 1)
        }

    def get_summary(self) -> Dict[str, Any]:
        return self.get_realtime_stats()

# Global Metrics instance
global_metrics = EngineMetrics()
