#!/usr/bin/env python3
"""
Groq API Key and Model Validator.
Tests all keys and models, auto-freezes broken/discontinued ones.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import MODEL_REGISTRY, FROZEN_FILE, FROZEN_IDS
from app.core.key_manager import GroqPool


@dataclass
class GroqKeyResult:
    """Result of validating a Groq key."""
    label: str
    valid: bool
    error: Optional[str] = None
    rate_limit: Optional[Dict] = None
    latency_ms: float = 0.0


@dataclass
class GroqModelResult:
    """Result of validating a Groq model."""
    model_id: str
    key_used: str
    working: bool
    error: Optional[str] = None
    latency_ms: float = 0.0
    tokens_used: int = 0
    freeze_reason: Optional[str] = None
    queue_status: Optional[str] = None  # Groq-specific: at capacity, etc.


class GroqValidator:
    """Validates Groq API keys and models."""
    
    TEST_PROMPT = "Say 'PEACOCK_TEST_OK' and nothing else."
    TEST_TIMEOUT = 30.0
    
    MODELS_TO_TEST = [
        m.id for m in MODEL_REGISTRY 
        if m.gateway == "groq" and m.status == "active"
    ]
    
    # Patterns that indicate model is removed/discontinued
    DISCONTINUED_PATTERNS = [
        "model not found",
        "404",
        "not found",
        "deprecated",
        "removed"
    ]
    
    # Patterns for key issues
    KEY_ERROR_PATTERNS = [
        "invalid api key",
        "authentication",
        "401",
        "403"
    ]
    
    # Groq-specific capacity issues (temporary, don't freeze)
    CAPACITY_PATTERNS = [
        "at capacity",
        "503",
        "temporarily unavailable"
    ]
    
    def __init__(self):
        self.key_results: List[GroqKeyResult] = []
        self.model_results: List[GroqModelResult] = []
    
    async def validate_key(self, key: str, label: str) -> GroqKeyResult:
        """Test a single Groq API key."""
        start = datetime.now()
        
        try:
            async with httpx.AsyncClient(timeout=self.TEST_TIMEOUT, trust_env=False) as client:
                response = await client.get(
                    "https://api.groq.com/openai/v1/models",
                    headers={"Authorization": f"Bearer {key}"}
                )
                
                latency = (datetime.now() - start).total_seconds() * 1000
                
                if response.status_code == 200:
                    # Extract rate limits from headers
                    headers = response.headers
                    rate_limit = {
                        "rpm_limit": headers.get("x-ratelimit-limit-requests"),
                        "rpm_remaining": headers.get("x-ratelimit-remaining-requests"),
                        "tpm_limit": headers.get("x-ratelimit-limit-tokens"),
                        "tpm_remaining": headers.get("x-ratelimit-remaining-tokens"),
                    }
                    
                    return GroqKeyResult(
                        label=label,
                        valid=True,
                        rate_limit=rate_limit,
                        latency_ms=latency
                    )
                else:
                    error_text = response.text
                    return GroqKeyResult(
                        label=label,
                        valid=False,
                        error=f"HTTP {response.status_code}: {error_text[:100]}",
                        latency_ms=latency
                    )
                    
        except Exception as e:
            latency = (datetime.now() - start).total_seconds() * 1000
            return GroqKeyResult(
                label=label,
                valid=False,
                error=str(e),
                latency_ms=latency
            )
    
    async def validate_model(
        self,
        key: str,
        model: str,
        label: str
    ) -> GroqModelResult:
        """Test a specific Groq model."""
        start = datetime.now()
        
        try:
            async with httpx.AsyncClient(timeout=self.TEST_TIMEOUT, trust_env=False) as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": self.TEST_PROMPT}],
                        "max_tokens": 10
                    }
                )
                
                latency = (datetime.now() - start).total_seconds() * 1000
                
                if response.status_code == 200:
                    data = response.json()
                    usage = data.get("usage", {})
                    
                    return GroqModelResult(
                        model_id=model,
                        key_used=label,
                        working=True,
                        latency_ms=latency,
                        tokens_used=usage.get("total_tokens", 0)
                    )
                else:
                    error_text = response.text.lower()
                    
                    # Determine freeze reason
                    freeze_reason = None
                    queue_status = None
                    
                    if any(p in error_text for p in self.DISCONTINUED_PATTERNS):
                        freeze_reason = "DISCONTINUED"
                    elif any(p in error_text for p in self.CAPACITY_PATTERNS):
                        queue_status = "AT_CAPACITY"
                    elif "429" in error_text or "rate limit" in error_text:
                        freeze_reason = "RATE_LIMITED"
                    
                    return GroqModelResult(
                        model_id=model,
                        key_used=label,
                        working=False,
                        error=f"HTTP {response.status_code}: {response.text[:100]}",
                        latency_ms=latency,
                        freeze_reason=freeze_reason,
                        queue_status=queue_status
                    )
                    
        except Exception as e:
            latency = (datetime.now() - start).total_seconds() * 1000
            return GroqModelResult(
                model_id=model,
                key_used=label,
                working=False,
                error=str(e),
                latency_ms=latency
            )
    
    async def validate_all(
        self,
        freeze_broken: bool = True,
        specific_key: Optional[str] = None,
        specific_model: Optional[str] = None
    ) -> Dict:
        """Run full validation."""
        print("⚡ GROQ VALIDATOR")
        print("=" * 60)
        
        # Filter keys if specific requested
        keys_to_test = GroqPool.deck
        if specific_key:
            keys_to_test = [k for k in keys_to_test if k.account == specific_key]
            if not keys_to_test:
                print(f"❌ Key '{specific_key}' not found")
                return {"keys": [], "models": [], "frozen": []}
        
        # Test all keys
        print(f"\n🔑 Testing {len(keys_to_test)} Groq API Key(s)...")
        
        key_tasks = [
            self.validate_key(asset.key, asset.account)
            for asset in keys_to_test
        ]
        self.key_results = await asyncio.gather(*key_tasks)
        
        # Print key results
        for result in self.key_results:
            status = "✅" if result.valid else "❌"
            rpm = result.rate_limit.get("rpm_remaining", "?") if result.rate_limit else "?"
            print(f"  {status} {result.label}: {result.latency_ms:.0f}ms (RPM: {rpm})")
            if result.error:
                print(f"     Error: {result.error[:80]}")
        
        # Filter working keys
        working_keys = [
            (asset.key, asset.account)
            for asset, result in zip(keys_to_test, self.key_results)
            if result.valid
        ]
        
        if not working_keys:
            print("\n❌ No working keys found!")
            return {"keys": [], "models": [], "frozen": []}
        
        # Filter models if specific requested
        models_to_test = self.MODELS_TO_TEST
        if specific_model:
            models_to_test = [m for m in models_to_test if m == specific_model]
            if not models_to_test:
                print(f"\n❌ Model '{specific_model}' not found or not active")
                return {"keys": [], "models": [], "frozen": []}
        
        # Test models
        print(f"\n⚡ Testing {len(models_to_test)} Model(s)...")
        
        test_key, test_label = working_keys[0]
        model_tasks = [
            self.validate_model(test_key, model, test_label)
            for model in models_to_test
        ]
        self.model_results = await asyncio.gather(*model_tasks)
        
        # Print model results
        for result in self.model_results:
            if result.working:
                print(f"  ✅ {result.model_id}: {result.latency_ms:.0f}ms, {result.tokens_used} tokens")
            elif result.queue_status:
                print(f"  ⏳ {result.model_id}: AT CAPACITY")
            else:
                status = "❄️" if result.freeze_reason else "❌"
                print(f"  {status} {result.model_id}: {result.error[:60]}")
        
        # Auto-freeze
        frozen_models = []
        if freeze_broken:
            for result in self.model_results:
                if not result.working and result.freeze_reason:
                    frozen_models.append({
                        "model": result.model_id,
                        "reason": result.freeze_reason
                    })
                    self._freeze_model(result.model_id)
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print(f"  Keys Valid: {sum(1 for r in self.key_results if r.valid)}/{len(self.key_results)}")
        print(f"  Models Working: {sum(1 for r in self.model_results if r.working)}/{len(self.model_results)}")
        if frozen_models:
            print(f"  ❄️  Frozen: {len(frozen_models)} models")
        
        return {
            "keys": [asdict(r) for r in self.key_results],
            "models": [asdict(r) for r in self.model_results],
            "frozen": frozen_models
        }
    
    def _freeze_model(self, model_id: str):
        """Add model to frozen list."""
        global FROZEN_IDS
        if model_id not in FROZEN_IDS:
            FROZEN_IDS.append(model_id)
            try:
                FROZEN_FILE.write_text(json.dumps(FROZEN_IDS))
                print(f"  ❄️  Frozen: {model_id}")
            except Exception as e:
                print(f"  ⚠️  Failed to freeze {model_id}: {e}")


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate Groq API keys and models")
    parser.add_argument("--no-freeze", action="store_true", help="Don't auto-freeze broken models")
    parser.add_argument("--key", help="Test specific key only")
    parser.add_argument("--model", help="Test specific model only")
    parser.add_argument("--output", "-o", help="Save report to JSON file")
    args = parser.parse_args()
    
    validator = GroqValidator()
    results = await validator.validate_all(
        freeze_broken=not args.no_freeze,
        specific_key=args.key,
        specific_model=args.model
    )
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Report saved to {args.output}")
    
    # Return exit code
    working_keys = sum(1 for r in validator.key_results if r.valid)
    if working_keys == 0:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
