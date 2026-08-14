"""
PEACOCK ENGINE - Key Manager
Handles API key rotation, shuffling, and usage tracking.
"""

import os
import random
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
from pydantic import BaseModel

# Ensure environment is loaded
load_dotenv()

from app.utils.formatter import CLIFormatter, Colors, ARSENAL_BLOCKS
from rich.console import Console
from rich.text import Text

# Rich Console for arsenal banner rendering
console = Console()
from app.db.database import KeyUsageDB


import time

class KeyAsset(BaseModel):
    label: str
    account: str
    key: str
    cooldown_until: float = 0.0
    enabled: bool = True

    @property
    def on_cooldown(self) -> bool:
        return time.time() < self.cooldown_until

    @property
    def is_available(self) -> bool:
        return self.enabled and not self.on_cooldown


from abc import ABC, abstractmethod

class RotationStrategy(ABC):
    @abstractmethod
    def get_next(self, deck: List[KeyAsset], pointer: int) -> Tuple[KeyAsset, int]:
        pass

class ShuffleStrategy(RotationStrategy):
    """Original 'Deck of Cards' logic."""
    def get_next(self, deck: List[KeyAsset], pointer: int) -> Tuple[KeyAsset, int]:
        asset = deck[pointer]
        new_pointer = pointer + 1
        return asset, new_pointer

class RoundRobinStrategy(RotationStrategy):
    """Simple 1, 2, 3 rotation."""
    def get_next(self, deck: List[KeyAsset], pointer: int) -> Tuple[KeyAsset, int]:
        asset = deck[pointer]
        new_pointer = (pointer + 1) % len(deck)
        return asset, new_pointer

class KeyPool:
    def __init__(self, env_string: Optional[str], pool_type: str):
        self.deck: List[KeyAsset] = []
        self.pointer: int = 0
        self.pool_type: str = pool_type
        self.strategy: RotationStrategy = ShuffleStrategy()
        
        if not env_string:
            CLIFormatter.warning(f"NO KEYS LOADED FOR {pool_type}")
            return

        entries = env_string.split(',')
        for idx, entry in enumerate(entries):
            entry = entry.strip()
            if not entry:
                continue
            label = ""
            key = ""
            
            if ':' in entry:
                parts = entry.split(':')
                label = parts[0]
                key = parts[1]
            else:
                label = f"{pool_type}_DEALER_{str(idx + 1).zfill(2)}"
                key = entry
            
            self.deck.append(KeyAsset(
                label=label.strip(),
                account=label.strip(),
                key=key.strip()
            ))
        self.shuffle()
        CLIFormatter.success(f"{pool_type} POOL: {len(self.deck)} KEYS LOADED")

    def set_strategy(self, strategy_name: str):
        if strategy_name == "round_robin":
            self.strategy = RoundRobinStrategy()
        else:
            self.strategy = ShuffleStrategy()

    def shuffle(self):
        if not self.deck:
            return
        if os.getenv("PEACOCK_VERBOSE") == "true":
            style = CLIFormatter.get_gateway_style(self.pool_type)
            print(f"{style['color']}[🎲] {self.pool_type} DECK SHUFFLING...{Colors.RESET}")
        random.shuffle(self.deck)
        self.pointer = 0

    def mark_cooldown(self, account: str, duration: int = 60):
        """Mark a specific key as being on cooldown."""
        for asset in self.deck:
            if asset.account == account:
                asset.cooldown_until = time.time() + duration
                CLIFormatter.warning(f"KEY [{account}] marked on COOLDOWN for {duration}s")
                return

    def set_key_enabled(self, account: str, enabled: bool) -> bool:
        """Enable or disable a specific key. Returns True if the key was found."""
        for asset in self.deck:
            if asset.account == account:
                asset.enabled = enabled
                CLIFormatter.info(
                    f"KEY [{account}] {'ENABLED' if enabled else 'DISABLED'} in {self.pool_type}"
                )
                return True
        return False

    def get_next(self) -> KeyAsset:
        if not self.deck:
            raise Exception(f"NO AMMUNITION FOR {self.pool_type}")

        # Try to find an enabled key not on cooldown (up to a full deck rotation)
        for _ in range(len(self.deck)):
            asset, self.pointer = self.strategy.get_next(self.deck, self.pointer)

            # If we hit the end of a shuffle deck, reshuffle
            if isinstance(self.strategy, ShuffleStrategy) and self.pointer >= len(self.deck):
                self.shuffle()

            if asset.is_available:
                return asset

        # All keys are disabled or on cooldown!
        raise Exception(f"ALL KEYS DISABLED OR ON COOLDOWN FOR {self.pool_type.upper()}")

    async def get_next_intelligent(self, model_id: str, estimated_tokens: int = 1) -> KeyAsset:
        """
        TB-007: Intelligent Key Selector.
        Scores every key by real-time rate-limit headroom and picks the best.
        
        Scoring weights:
          • TPM headroom : 50% (most common bottleneck)
          • RPM headroom : 30% (request velocity)
          • RPD headroom : 10% (daily budget)
          • TPD headroom : 10% (daily token budget)
        
        Args:
            model_id: Groq model ID to evaluate against
            estimated_tokens: Expected token burn for the upcoming request
        
        Returns:
            KeyAsset with the highest composite score
        """
        if not self.deck:
            raise Exception(f"NO AMMUNITION FOR {self.pool_type}")

        # Lazy import to avoid circular dependency at module load time
        from app.core.rate_limit_tracker import GroqRateTracker

        best_asset: Optional[KeyAsset] = None
        best_score = -1.0

        for asset in self.deck:
            if not asset.is_available:
                continue

            # Ask the tracker if this key can handle the request
            result = await GroqRateTracker.can_consume(asset.account, model_id, estimated_tokens)
            if not result.allowed:
                continue

            # Composite score: weighted headroom
            score = 0.0
            if result.remaining_tpm > 0:
                score += result.remaining_tpm * 0.50
            if result.remaining_rpm > 0:
                score += result.remaining_rpm * 0.30
            if result.remaining_rpd > 0:
                score += result.remaining_rpd * 0.10
            if result.remaining_tpd > 0:
                score += result.remaining_tpd * 0.10

            if score > best_score:
                best_score = score
                best_asset = asset

        if best_asset is None:
            raise Exception(
                f"NO HEALTHY KEYS FOR {self.pool_type.upper()} | model={model_id} | tokens={estimated_tokens}"
            )

        if os.getenv("PEACOCK_VERBOSE") == "true":
            style = CLIFormatter.get_gateway_style(self.pool_type)
            print(
                f"{style['color']}[🧠] INTELLIGENT SELECT → {best_asset.account} "
                f"(score={best_score:.0f}){Colors.RESET}"
            )

        return best_asset

    def dump(self):
        style = CLIFormatter.get_gateway_style(self.pool_type)
        gw_color = style["color"].replace("\033[", "").replace("m", "")
        color_map = {"96": "cyan", "94": "blue", "92": "green", "95": "magenta", "97": "white", "93": "yellow"}
        base_color = color_map.get(gw_color, "white")

        console.print()
        console.print(Text(f".:::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::.", style=f"dim {base_color}"))
        console.print(Text(f":: [ {self.pool_type.upper()} ARSENAL LOADED ] ::::::::::::::::::::::::::::::::::::::::::::::::::::", style=f"bold {base_color}"))
        console.print(Text(":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::", style=f"dim {base_color}"))

        # ASCII Art Banner — resolve sub-gateways to shared parent block
        gw_key = self.pool_type.lower()
        if gw_key not in ARSENAL_BLOCKS:
            gw_key = gw_key.split("-")[0]
        block = ARSENAL_BLOCKS.get(gw_key, [])
        if block:
            banner_colors = ["green3", "spring_green3", "spring_green2", "spring_green1"]
            for i, line in enumerate(block):
                console.print(Text(line, style=banner_colors[i % len(banner_colors)]))

        console.print(Text(":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::", style=f"dim {base_color}"))

        if not self.deck:
            console.print(Text(f"  ::  [!] NO {self.pool_type.upper()} KEYS ENROLLED.", style="bold red"))
        else:
            for i, a in enumerate(self.deck):
                masked = f"{a.key[:8]}..." if len(a.key) > 8 else "INVALID"
                row = f"  ::  [{str(i+1).zfill(2)}]  {a.account.ljust(20)}  | ID: {masked}"
                console.print(Text(row, style=f"bold {base_color}"))

        console.print(Text("':::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::'", style=f"dim {base_color}"))
        console.print()

    @staticmethod
    def record_usage(gateway: str, account: str, usage: dict):
        """Record usage for a key to the database."""
        try:
            KeyUsageDB.record_usage(gateway, account, usage)
        except Exception as e:
            CLIFormatter.warning(f"Failed to record key usage: {e}")


# Desired providers (plus hidden zai/zai-coding for future use)
_POOL_SPECS: List[Tuple[str, str]] = [
    ("GROQ_KEYS", "groq"),
    ("OPENCODE_GO_KEYS", "opencode-go"),
    ("OPENCODE_ZEN_KEYS", "opencode-zen"),
    ("OPENROUTER_KEYS", "openrouter"),
    ("OLLAMA_KEYS", "ollama"),
    ("HETZNER_KEYS", "hetzner"),
    ("ZAI_KEYS", "zai"),
    ("ZAI_CODING_KEYS", "zai-coding"),
]

# Build pools dynamically; hidden providers are created empty if no env var
# so they can be enabled later without code changes.
_pools: Dict[str, KeyPool] = {}
for _env_key, _pool_type in _POOL_SPECS:
    _pools[_pool_type] = KeyPool(os.getenv(_env_key), _pool_type)

GroqPool = _pools["groq"]
OpencodeGoPool = _pools["opencode-go"]
OpencodeZenPool = _pools["opencode-zen"]
OpenrouterPool = _pools["openrouter"]
OllamaPool = _pools["ollama"]
HetznerPool = _pools["hetzner"]
ZaiPool = _pools["zai"]
ZaiCodingPool = _pools["zai-coding"]

# Deprecated standalone providers: exposed as empty pools so existing imports
# in striker.py don't break while their branches are removed in a follow-up slice.
GooglePool = KeyPool(None, "google")
DeepSeekPool = KeyPool(None, "deepseek")
MistralPool = KeyPool(None, "mistral")


def get_pool(gateway: str) -> Optional[KeyPool]:
    """Look up a key pool by gateway name."""
    return _pools.get(gateway.lower())


def list_pools() -> Dict[str, KeyPool]:
    """Return a shallow copy of the pool registry."""
    return _pools.copy()


if os.getenv("PEACOCK_DEBUG") == "true":
    for _pool in _pools.values():
        _pool.dump()

