"""
PEACOCK ENGINE - Unified Token Engine
High-precision local tokenization using Vertex AI and Tiktoken.
"""

import logging
from typing import Optional
from functools import lru_cache
from app.config import MODEL_REGISTRY
from app.utils.logger import HighSignalLogger

# Setup logging
logger = logging.getLogger("TokenEngine")

class UnifiedTokenEngine:
    """Unified engine for high-precision local token counting."""
    
    _gemini_tokenizers = {}
    _tiktoken_encodings = {}

    @classmethod
    def get_gemini_tokenizer(cls, model_id: str):
        """Lazy load Vertex AI tokenizer for Gemini models."""
        # Map generic ids to specific versions if needed for the tokenizer
        tk_model_id = model_id
        if "flash-lite" in model_id:
            tk_model_id = "gemini-2.0-flash-lite-preview-02-05"
            
        if tk_model_id not in cls._gemini_tokenizers:
            try:
                from vertexai.preview.tokenization import get_tokenizer_for_model
                logger.info(f"Initializing Vertex tokenizer for {tk_model_id}...")
                cls._gemini_tokenizers[tk_model_id] = get_tokenizer_for_model(tk_model_id)
            except Exception as e:
                logger.warning(f"Vertex tokenizer unavailable for {tk_model_id}: {e}")
                return None
        return cls._gemini_tokenizers.get(tk_model_id)

    @classmethod
    def get_tiktoken_encoding(cls, model_id: str):
        """Lazy load Tiktoken encoding for OpenAI/Groq models."""
        import tiktoken
        if model_id not in cls._tiktoken_encodings:
            try:
                # Map common models to known encodings
                if "llama" in model_id.lower() or "mixtral" in model_id.lower():
                    cls._tiktoken_encodings[model_id] = tiktoken.get_encoding("cl100k_base")
                else:
                    cls._tiktoken_encodings[model_id] = tiktoken.encoding_for_model(model_id)
            except Exception:
                cls._tiktoken_encodings[model_id] = tiktoken.get_encoding("cl100k_base")
        return cls._tiktoken_encodings[model_id]

    @classmethod
    def count_tokens(cls, model_id: str, text: str) -> int:
        """precision count tokens locally."""
        if not text:
            return 0
            
        # Find gateway
        config = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
        gateway = config.gateway if config else "google"

        try:
            if gateway == "google":
                tokenizer = cls.get_gemini_tokenizer(model_id)
                if tokenizer:
                    return tokenizer.count_tokens(text).total_tokens
                
                # Fallback to high-fidelity regex estimation if library fails
                try:
                    from app.utils.gemini_token_counter import GeminiTokenCounter
                    return GeminiTokenCounter().estimate_tokens(text)
                except ImportError:
                    return len(text) // 4
            
            # OpenAI/Groq/Mistral patterns (Tiktoken)
            encoding = cls.get_tiktoken_encoding(model_id)
            return len(encoding.encode(text))
            
        except Exception as e:
            HighSignalLogger.error(f"Unified token count failure: {e}")
            return len(text) // 4

def count_tokens_local(text: str, model_id: str = "models/gemini-2.0-flash-lite-001") -> int:
    """Convenience wrapper for the unified engine."""
    return UnifiedTokenEngine.count_tokens(model_id, text)

if __name__ == "__main__":
    # Smoke test
    test_text = "Syndicate Payload Deck: Kinetic Pulse Activated."
    print(f"Testing local count for {test_text}")
    print(f"Gemini: {count_tokens_local(test_text, 'gemini-1.5-flash')}")
    print(f"Llama (Tiktoken Fallback): {count_tokens_local(test_text, 'llama-3.3-70b-versatile')}")
