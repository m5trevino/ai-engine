"""
PEACOCK ENGINE - Key Manager
Handles API key rotation, shuffling, and usage tracking.
"""

import os
import random
from typing import List, Optional, Tuple
from dotenv import load_dotenv
from pydantic import BaseModel

# Ensure environment is loaded
load_dotenv()

from app.utils.formatter import CLIFormatter, Colors
from app.db.database import KeyUsageDB


import time

class KeyAsset(BaseModel):
    label: str
    account: str
    key: str
    cooldown_until: float = 0.0

    @property
    def on_cooldown(self) -> bool:
        return time.time() < self.cooldown_until


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

    def get_next(self) -> KeyAsset:
        if not self.deck:
            raise Exception(f"NO AMMUNITION FOR {self.pool_type}")
        
        # Try to find a key not on cooldown (up to a full deck rotation)
        for _ in range(len(self.deck)):
            asset, self.pointer = self.strategy.get_next(self.deck, self.pointer)
            
            # If we hit the end of a shuffle deck, reshuffle
            if isinstance(self.strategy, ShuffleStrategy) and self.pointer >= len(self.deck):
                self.shuffle()
            
            if not asset.on_cooldown:
                return asset
                
        # All keys are on cooldown!
        raise Exception(f"ALL KEYS ON COOLDOWN FOR {self.pool_type.upper()}")

    def dump(self):
        style = CLIFormatter.get_gateway_style(self.pool_type)
        print(f"\n{style['color']}--- [ {self.pool_type} ARSENAL LOADED ] ---{Colors.RESET}")
        for i, a in enumerate(self.deck):
            masked = f"{a.key[:8]}..." if len(a.key) > 8 else "INVALID"
            print(f"{style['color']}[{str(i+1).zfill(2)}]{Colors.RESET} {Colors.YELLOW}{a.account.ljust(20)}{Colors.RESET} | ID: {masked}")

    @staticmethod
    def record_usage(gateway: str, account: str, usage: dict):
        """Record usage for a key to the database."""
        try:
            KeyUsageDB.record_usage(gateway, account, usage)
        except Exception as e:
            CLIFormatter.warning(f"Failed to record key usage: {e}")


# Load pools from Environment Variables
GroqPool = KeyPool(os.getenv("GROQ_KEYS"), "groq")
GooglePool = KeyPool(os.getenv("GOOGLE_KEYS"), "google")
DeepSeekPool = KeyPool(os.getenv("DEEPSEEK_KEYS"), "deepseek")
MistralPool = KeyPool(os.getenv("MISTRAL_KEYS"), "mistral")

if os.getenv("PEACOCK_DEBUG") == "true":
    GroqPool.dump()
    GooglePool.dump()
    DeepSeekPool.dump()
    MistralPool.dump()

