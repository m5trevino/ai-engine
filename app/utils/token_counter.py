"""
PEACOCK ENGINE - Unified Token Counter
Coordinates provider-specific counters for accurate usage and cost tracking.
"""

from typing import List, Dict, Any, Optional
from app.config import MODEL_REGISTRY
from app.utils.gemini_token_counter import GeminiTokenCounter
from app.utils.groq_token_counter import GroqTokenCounter
from app.utils.logger import HighSignalLogger

class PeacockTokenCounter:
    """Unified coordinator for token counting across all gateways."""
    
    @staticmethod
    def get_model_config(model_id: str):
        """Find model configuration in the registry."""
        return next((m for m in MODEL_REGISTRY if m.id == model_id), None)

    @classmethod
    def count_prompt_tokens(cls, model_id: str, prompt: str, files: List[str] = []) -> int:
        """
        Count tokens for a prompt in the context of a specific model.
        Supports text, file context, and multimodal estimation.
        """
        config = cls.get_model_config(model_id)
        if not config:
            return 0
            
        try:
            if config.gateway == "google":
                return GeminiTokenCounter.count_tokens(model_id, prompt, files)
            elif config.gateway == "groq":
                # For Groq, we assume OpenAI message format overhead
                messages = [{"role": "user", "content": prompt}]
                return GroqTokenCounter.count_messages(messages, model_id)
            else:
                # Fallback for deepseek/mistral if specific counters not yet implemented
                return len(prompt) // 4
        except Exception as e:
            HighSignalLogger.error(f"Unified counter failure for {model_id}: {e}")
            return len(prompt) // 4

    @classmethod
    def calculate_cost(cls, model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Calculate cost in USD based on model registry pricing.
        """
        config = cls.get_model_config(model_id)
        if not config:
            return 0.0
            
        input_cost = (prompt_tokens / 1_000_000) * config.input_price_1m
        output_cost = (completion_tokens / 1_000_000) * config.output_price_1m
        
        return round(input_cost + output_cost, 6)

    @classmethod
    def get_token_limit(cls, model_id: str) -> Optional[int]:
        """Get the TPM limit for a model."""
        config = cls.get_model_config(model_id)
        return config.tpm if config else None
