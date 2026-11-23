"""
Groq Token Counter using tiktoken.
Based on: CustomGroqChat repo

Groq uses the tokenizer from the original model training:
- Llama models: Use Llama tokenizer (via tiktoken fallback)
- GPT-OSS models: Use OpenAI tokenizers
- General fallback: cl100k_base
"""

import json
from typing import List, Dict, Optional, Union, Any
import os

# Model-to-encoding mapping for Groq models
MODEL_ENCODING_MAP = {
    # OpenAI GPT-OSS models on Groq
    "openai/gpt-oss-120b": "o200k_base",
    "openai/gpt-oss-20b": "o200k_base",
    "openai/gpt-oss-safeguard-20b": "o200k_base",
    
    # Llama models - use cl100k_base as closest approximation
    "llama-3.3-70b-versatile": "cl100k_base",
    "llama-3.1-8b-instant": "cl100k_base",
    "meta-llama/llama-4-scout-17b-16e-instruct": "cl100k_base",
    
    # Qwen models
    "qwen/qwen3-32b": "cl100k_base",
    
    # Kimi/Moonshot
    "moonshotai/kimi-k2-instruct": "cl100k_base",
    "moonshotai/kimi-k2-instruct-0905": "cl100k_base",
    
    # Groq compound models
    "groq/compound": "cl100k_base",
    "groq/compound-mini": "cl100k_base",
    
    # Other models
    "allam-2-7b": "cl100k_base",
    "meta-llama/llama-prompt-guard-2-86m": "cl100k_base",
    "meta-llama/llama-prompt-guard-2-22m": "cl100k_base",
}

# Message format overhead (from Groq forum research)
# https://community.groq.com/t/which-tokeniser-is-used-by-groq/132
MESSAGE_OVERHEAD = 4      # Per message formatting tokens
CONVERSATION_OVERHEAD = 3 # Overall conversation formatting


class GroqTokenCounter:
    """Token counter for Groq models using tiktoken."""
    
    DEFAULT_ENCODING = "cl100k_base"
    
    def __init__(self):
        self._encoding_cache: Dict[str, Any] = {}
        self._tiktoken_available = None
    
    def _check_tiktoken(self):
        """Check if tiktoken is available."""
        if self._tiktoken_available is None:
            try:
                import tiktoken
                self._tiktoken_available = True
            except ImportError:
                self._tiktoken_available = False
        return self._tiktoken_available
    
    def get_encoding(self, model: str) -> Any:
        """Get the appropriate encoding for a model."""
        if not self._check_tiktoken():
            raise ImportError(
                "tiktoken required for Groq token counting. "
                "Install: pip install tiktoken"
            )
        
        import tiktoken
        
        encoding_name = MODEL_ENCODING_MAP.get(model, self.DEFAULT_ENCODING)
        
        if encoding_name not in self._encoding_cache:
            try:
                self._encoding_cache[encoding_name] = tiktoken.get_encoding(encoding_name)
            except KeyError:
                # Fallback to default
                self._encoding_cache[encoding_name] = tiktoken.get_encoding(self.DEFAULT_ENCODING)
        
        return self._encoding_cache[encoding_name]
    
    def count_tokens(self, text: str, model: str) -> int:
        """
        Count tokens in a text string.
        
        Args:
            text: Text to count
            model: Model ID for encoding selection
            
        Returns:
            Number of tokens
        """
        if not text:
            return 0
        
        encoding = self.get_encoding(model)
        return len(encoding.encode(text))
    
    def count_message_tokens(self, message: Dict, model: str) -> int:
        """
        Count tokens in a single chat message.
        Includes content + role + format overhead.
        
        Args:
            message: Message dict with 'role' and 'content' keys
            model: Model ID
            
        Returns:
            Token count for message
        """
        encoding = self.get_encoding(model)
        
        # Count content tokens
        content = message.get("content", "")
        if isinstance(content, list):
            # Multimodal content (list of parts)
            content_tokens = 0
            for part in content:
                if isinstance(part, dict):
                    if "text" in part:
                        content_tokens += len(encoding.encode(part["text"]))
                    elif "image_url" in part:
                        # Image tokens - estimate
                        content_tokens += 258  # Same as Gemini image tile
                elif isinstance(part, str):
                    content_tokens += len(encoding.encode(part))
        else:
            content_tokens = len(encoding.encode(str(content)))
        
        # Add format overhead (role markers, etc.)
        total = content_tokens + MESSAGE_OVERHEAD
        
        # Function calls or tool calls add more tokens
        if "function_call" in message:
            function_call = message["function_call"]
            if isinstance(function_call, dict):
                func_str = json.dumps(function_call)
                total += len(encoding.encode(func_str))
        
        if "tool_calls" in message:
            tool_calls = message["tool_calls"]
            if isinstance(tool_calls, list):
                for tool_call in tool_calls:
                    tool_str = json.dumps(tool_call)
                    total += len(encoding.encode(tool_str))
        
        # Tool response
        if message.get("role") == "tool" and "tool_call_id" in message:
            total += len(encoding.encode(message["tool_call_id"]))
        
        return total
    
    def count_messages_tokens(self, messages: List[Dict], model: str) -> int:
        """
        Count tokens in a list of chat messages.
        
        Args:
            messages: List of message dictionaries
            model: Model ID
            
        Returns:
            Total token count
        """
        if not messages:
            return 0
        
        token_count = sum(
            self.count_message_tokens(msg, model)
            for msg in messages
        )
        
        # Add conversation overhead
        return token_count + CONVERSATION_OVERHEAD
    
    def count_request_tokens(
        self,
        model: str,
        messages: Optional[List[Dict]] = None,
        prompt: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        system: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Count tokens for a complete request.
        
        Args:
            model: Model ID
            messages: Chat messages
            prompt: Simple text prompt (alternative to messages)
            tools: Tool definitions
            system: System message/instruction
            
        Returns:
            Dict with prompt_tokens, tool_tokens, total_tokens
        """
        prompt_tokens = 0
        
        # System message
        if system:
            prompt_tokens += self.count_tokens(system, model) + MESSAGE_OVERHEAD
        
        # Count message/prompt tokens
        if messages:
            prompt_tokens = self.count_messages_tokens(messages, model)
        elif prompt:
            prompt_tokens = self.count_tokens(prompt, model)
        
        # Count tool definition tokens
        tool_tokens = 0
        if tools:
            tools_json = json.dumps(tools)
            tool_tokens = self.count_tokens(tools_json, model)
        
        return {
            "prompt_tokens": prompt_tokens,
            "tool_tokens": tool_tokens,
            "total_tokens": prompt_tokens + tool_tokens
        }
    
    def estimate_completion_tokens(
        self,
        max_tokens: Optional[int] = None,
        default: int = 150
    ) -> int:
        """
        Estimate completion tokens based on max_tokens setting.
        
        Args:
            max_tokens: Requested max tokens
            default: Default if not specified
            
        Returns:
            Estimated completion tokens
        """
        if max_tokens and max_tokens > 0:
            return max_tokens
        return default
    
    def count_tokens_in_prompt(self, text: str, model: str) -> int:
        """Alias for count_tokens for backward compatibility."""
        return self.count_tokens(text, model)

    @staticmethod
    def count_messages(messages: List[Dict], model: str) -> int:
        """Static method for PeacockTokenCounter compatibility."""
        counter = GroqTokenCounter()
        if not counter._check_tiktoken():
            return len(str(messages)) // 4
        return counter.count_messages_tokens(messages, model)


# Convenience functions
def count_tokens_groq(text: str, model: str = "llama-3.3-70b-versatile") -> int:
    """Quick function to count tokens for text."""
    counter = GroqTokenCounter()
    return counter.count_tokens(text, model)


def count_messages_tokens_groq(messages: List[Dict], model: str = "llama-3.3-70b-versatile") -> int:
    """Quick function to count tokens in messages."""
    counter = GroqTokenCounter()
    return counter.count_messages_tokens(messages, model)


if __name__ == "__main__":
    # Test
    counter = GroqTokenCounter()
    
    test_text = "Hello, how are you today?"
    test_model = "llama-3.3-70b-versatile"
    
    print("=== Groq Token Counter Test ===")
    print(f"Text: {test_text}")
    print(f"Model: {test_model}")
    print(f"Tokens: {counter.count_tokens(test_text, test_model)}")
    
    # Test messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there! How can I help?"}
    ]
    
    print(f"\nMessages token count: {counter.count_messages_tokens(messages, test_model)}")
    
    # Test with tools
    tools = [{
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather for a location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string"}
                }
            }
        }
    }]
    
    result = counter.count_request_tokens(
        model=test_model,
        messages=messages,
        tools=tools
    )
    print(f"\nRequest with tools:")
    for k, v in result.items():
        print(f"  {k}: {v}")
