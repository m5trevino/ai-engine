#!/usr/bin/env python3
"""
Google/Gemini API Key and Model Validator.
Tests all keys and models, auto-freezes broken/discontinued ones.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import MODEL_REGISTRY, FROZEN_FILE, FROZEN_IDS
from app.core.key_manager import GooglePool


@dataclass
class KeyValidationResult:
    """Result of validating a single key."""
    label: str
    valid: bool
    error: Optional[str] = None
    models_available: List[str] = None
    latency_ms: float = 0.0


@dataclass
class ModelValidationResult:
    """Result of validating a single model."""
    model_id: str
    key_used: str
    working: bool
    error: Optional[str] = None
    latency_ms: float = 0.0
    tokens_used: int = 0
    freeze_reason: Optional[str] = None


class GoogleValidator:
    """Validates Google API keys and models."""
    
    TEST_PROMPT = "Say 'PEACOCK_TEST_OK' and nothing else."
    TEST_TIMEOUT = 30.0
    
    # Models to test (all Google models from registry)
    MODELS_TO_TEST = [
        m.id for m in MODEL_REGISTRY 
        if m.gateway == "google" and m.status == "active"
    ]
    
    # Error patterns that indicate model is discontinued
    DISCONTINUED_PATTERNS = [
        "model not found",
        "deprecated",
        "discontinued", 
        "not supported",
        "404",
        "invalid model"
    ]
    
    # Error patterns that indicate key issue (not model issue)
    KEY_ERROR_PATTERNS = [
        "api key not valid",
        "invalid api key",
        "authentication",
        "permission denied",
        "401"
    ]
    
    def __init__(self):
        self.results: List[ModelValidationResult] = []
        self.key_results: List[KeyValidationResult] = []
        
    async def validate_key(self, key: str, label: str) -> KeyValidationResult:
        """Test a single API key for basic auth."""
        start = datetime.now()
        
        try:
            from google import genai
            client = genai.Client(api_key=key)
            
            # Try to list models (lightweight auth check)
            models = client.models.list()
            available = [m.name for m in models]
            
            latency = (datetime.now() - start).total_seconds() * 1000
            
            return KeyValidationResult(
                label=label,
                valid=True,
                models_available=available,
                latency_ms=latency
            )
            
        except Exception as e:
            latency = (datetime.now() - start).total_seconds() * 1000
            error_str = str(e).lower()
            
            return KeyValidationResult(
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
    ) -> ModelValidationResult:
        """Test a specific model with a specific key."""
        start = datetime.now()
        
        try:
            from google import genai
            client = genai.Client(api_key=key)
            
            # Clean model ID
            clean_model = model.replace("models/", "")
            
            # Try to generate content
            response = client.models.generate_content(
                model=clean_model,
                contents=self.TEST_PROMPT
            )
            
            latency = (datetime.now() - start).total_seconds() * 1000
            
            # Check if response is valid
            text = response.text if hasattr(response, 'text') else ""
            
            # Get token usage if available
            tokens = 0
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                tokens = response.usage_metadata.total_token_count
            
            return ModelValidationResult(
                model_id=model,
                key_used=label,
                working=True,
                latency_ms=latency,
                tokens_used=tokens
            )
            
        except Exception as e:
            latency = (datetime.now() - start).total_seconds() * 1000
            error_str = str(e).lower()
            
            # Determine if model should be frozen
            freeze_reason = None
            if any(p in error_str for p in self.DISCONTINUED_PATTERNS):
                freeze_reason = "DISCONTINUED"
            elif "429" in error_str or "quota" in error_str:
                freeze_reason = "QUOTA_EXCEEDED"
            elif "rate limit" in error_str:
                freeze_reason = "RATE_LIMITED"
            
            return ModelValidationResult(
                model_id=model,
                key_used=label,
                working=False,
                error=str(e),
                latency_ms=latency,
                freeze_reason=freeze_reason
            )
    
    async def validate_all(
        self, 
        freeze_broken: bool = True,
        specific_key: Optional[str] = None,
        specific_model: Optional[str] = None
    ) -> Dict:
        """
        Run full validation on all keys and models.
        
        Args:
            freeze_broken: Auto-freeze models that are discontinued
            specific_key: Only test this key (if None, test all)
            specific_model: Only test this model (if None, test all)
        """
        print("🦚 GOOGLE VALIDATOR")
        print("=" * 60)
        
        # Filter keys if specific requested
        keys_to_test = GooglePool.deck
        if specific_key:
            keys_to_test = [k for k in keys_to_test if k.account == specific_key]
            if not keys_to_test:
                print(f"❌ Key '{specific_key}' not found")
                return {"keys": [], "models": [], "frozen": []}
        
        # Test all keys
        print(f"\n🔑 Testing {len(keys_to_test)} Google API Key(s)...")
        
        key_tasks = []
        for asset in keys_to_test:
            key_tasks.append(self.validate_key(asset.key, asset.account))
        
        self.key_results = await asyncio.gather(*key_tasks, return_exceptions=True)
        self.key_results = [
            r if not isinstance(r, Exception) else KeyValidationResult(
                label="unknown", valid=False, error=str(r)
            )
            for r in self.key_results
        ]
        
        # Print key results
        for result in self.key_results:
            status = "✅" if result.valid else "❌"
            print(f"  {status} {result.label}: {result.latency_ms:.0f}ms")
            if result.error:
                print(f"     Error: {result.error[:80]}")
        
        # Filter to working keys for model testing
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
        
        # Test all models with first working key
        print(f"\n🤖 Testing {len(models_to_test)} Model(s)...")
        
        test_key, test_label = working_keys[0]
        model_tasks = [
            self.validate_model(test_key, model, test_label)
            for model in models_to_test
        ]
        
        self.results = await asyncio.gather(*model_tasks, return_exceptions=True)
        self.results = [
            r if not isinstance(r, Exception) else ModelValidationResult(
                model_id="unknown", key_used=test_label, working=False, error=str(r)
            )
            for r in self.results
        ]
        
        # Print model results
        for result in self.results:
            if result.working:
                print(f"  ✅ {result.model_id}: {result.latency_ms:.0f}ms, {result.tokens_used} tokens")
            else:
                status = "❄️" if result.freeze_reason else "❌"
                print(f"  {status} {result.model_id}: {result.error[:60]}")
        
        # Auto-freeze broken models
        frozen_models = []
        if freeze_broken:
            for result in self.results:
                if not result.working and result.freeze_reason:
                    frozen_models.append({
                        "model": result.model_id,
                        "reason": result.freeze_reason,
                        "error": result.error
                    })
                    self._freeze_model(result.model_id)
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print(f"  Keys Valid: {sum(1 for r in self.key_results if r.valid)}/{len(self.key_results)}")
        print(f"  Models Working: {sum(1 for r in self.results if r.working)}/{len(self.results)}")
        if frozen_models:
            print(f"  ❄️  Frozen: {len(frozen_models)} models")
        
        return {
            "keys": [asdict(r) for r in self.key_results],
            "models": [asdict(r) for r in self.results],
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
    """CLI entry point."""
    import argparse
    parser = argparse.ArgumentParser(description="Validate Google API keys and models")
    parser.add_argument("--no-freeze", action="store_true", help="Don't auto-freeze broken models")
    parser.add_argument("--key", help="Test specific key only")
    parser.add_argument("--model", help="Test specific model only")
    parser.add_argument("--output", "-o", help="Save report to JSON file")
    args = parser.parse_args()
    
    validator = GoogleValidator()
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
        sys.exit(1)  # Error if no working keys


if __name__ == "__main__":
    asyncio.run(main())
