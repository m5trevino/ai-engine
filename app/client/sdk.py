"""
PEACOCK ENGINE - Python Client SDK
Minimal wrapper for easy integration.
"""

import requests
from typing import List, Optional, Dict, Any, Union
from pathlib import Path


class PeacockClient:
    """
    Minimal Python client for PEACOCK ENGINE.
    
    Example:
        >>> from app.client.sdk import PeacockClient
        >>> client = PeacockClient("http://localhost:3099")
        >>> response = client.chat("llama-3.3-70b-versatile", "Hello!")
        >>> print(response.content)
    """
    
    def __init__(self, base_url: str = "http://localhost:3099"):
        """
        Initialize the client.
        
        Args:
            base_url: The PEACOCK ENGINE URL (default: http://localhost:3099)
        """
        self.base_url = base_url.rstrip('/')
        self._models = None
        self._keys = None
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a request to the API."""
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def health(self) -> Dict[str, Any]:
        """Check engine health."""
        return self._request("GET", "/health")
    
    def get_models(self, refresh: bool = False) -> Dict[str, List[Dict]]:
        """
        Get all available models grouped by gateway.
        
        Args:
            refresh: Force refresh from server
        
        Returns:
            Dictionary of gateway -> list of models
        """
        if self._models is None or refresh:
            self._models = self._request("GET", "/v1/chat/models")
        return self._models
    
    def get_model(self, model_id: str) -> Optional[Dict]:
        """
        Get a specific model by ID.
        
        Args:
            model_id: The model identifier
        
        Returns:
            Model config or None if not found
        """
        models = self.get_models()
        for gateway, gateway_models in models.items():
            for model in gateway_models:
                if model['id'] == model_id:
                    return {**model, 'gateway': gateway}
        return None
    
    def get_keys_usage(self) -> Dict[str, Any]:
        """Get API key usage statistics."""
        return self._request("GET", "/v1/keys/usage")
    
    def chat(
        self,
        model: str,
        prompt: str,
        files: Optional[List[str]] = None,
        format: str = "text",
        schema: Optional[Dict[str, Any]] = None,
        temp: float = 0.7,
        key: Optional[str] = None
    ) -> 'ChatResponse':
        """
        Send a chat request.
        
        Args:
            model: Model ID (e.g., 'llama-3.3-70b-versatile')
            prompt: The prompt text
            files: Optional list of file paths to include as context
            format: Output format ('text', 'json', or 'pydantic')
            schema: Schema definition for 'pydantic' format
            temp: Temperature (0.0-2.0)
            key: Specific key account to use (bypasses rotation)
        
        Returns:
            ChatResponse object
        """
        # Validate files exist
        if files:
            valid_files = [f for f in files if Path(f).exists()]
            if len(valid_files) != len(files):
                missing = set(files) - set(valid_files)
                print(f"Warning: Files not found: {missing}")
            files = valid_files
        
        payload = {
            "model": model,
            "prompt": prompt,
            "files": files or [],
            "format": format,
            "temp": temp
        }
        
        if schema:
            payload["schema"] = schema
        
        if key:
            payload["key"] = key
        
        response = self._request("POST", "/v1/chat", json=payload)
        return ChatResponse(response)
    
    def quick_chat(self, prompt: str, model: str = "llama-3.3-70b-versatile") -> str:
        """
        Quick chat - returns just the content string.
        
        Args:
            prompt: The prompt text
            model: Model ID (default: llama-3.3-70b-versatile)
        
        Returns:
            Response content string
        """
        response = self.chat(model, prompt)
        return response.content
    
    def analyze_files(
        self,
        files: List[str],
        prompt: str,
        model: str = "llama-3.3-70b-versatile"
    ) -> 'ChatResponse':
        """
        Analyze files with a prompt.
        
        Args:
            files: List of file paths
            prompt: Analysis prompt
            model: Model to use
        
        Returns:
            ChatResponse object
        """
        return self.chat(model, prompt, files=files)
    
    def extract_structured(
        self,
        text: str,
        schema: Dict[str, Any],
        model: str = "llama-3.3-70b-versatile"
    ) -> Dict[str, Any]:
        """
        Extract structured data using a schema.
        
        Args:
            text: Text to extract from
            schema: Schema definition
            model: Model to use
        
        Returns:
            Structured data dict
        """
        response = self.chat(
            model=model,
            prompt=f"Extract structured data from:\n{text}",
            format="pydantic",
            schema=schema
        )
        return response.content if isinstance(response.content, dict) else {}


class ChatResponse:
    """Wrapper for chat response data."""
    
    def __init__(self, data: Dict[str, Any]):
        self._data = data
    
    @property
    def content(self) -> Any:
        """Response content (string or dict depending on format)."""
        return self._data.get("content")
    
    @property
    def model(self) -> str:
        """Model ID used."""
        return self._data.get("model", "")
    
    @property
    def gateway(self) -> str:
        """Gateway used."""
        return self._data.get("gateway", "")
    
    @property
    def key_used(self) -> str:
        """API key account used."""
        return self._data.get("key_used", "")
    
    @property
    def format(self) -> str:
        """Response format."""
        return self._data.get("format", "")
    
    @property
    def usage(self) -> Dict[str, int]:
        """Token usage statistics."""
        return self._data.get("usage", {})
    
    @property
    def duration_ms(self) -> int:
        """Request duration in milliseconds."""
        return self._data.get("duration_ms", 0)
    
    @property
    def prompt_tokens(self) -> int:
        """Number of prompt tokens."""
        return self.usage.get("prompt_tokens", 0)
    
    @property
    def completion_tokens(self) -> int:
        """Number of completion tokens."""
        return self.usage.get("completion_tokens", 0)
    
    @property
    def total_tokens(self) -> int:
        """Total token count."""
        return self.usage.get("total_tokens", 0)
    
    def __repr__(self) -> str:
        return f"<ChatResponse model={self.model} tokens={self.total_tokens}>"
    
    def __str__(self) -> str:
        return str(self.content)


# Convenience functions for quick usage

def chat(prompt: str, model: str = "llama-3.3-70b-versatile", base_url: str = "http://localhost:3099") -> str:
    """
    Quick one-off chat without creating a client.
    
    Args:
        prompt: The prompt text
        model: Model ID
        base_url: Engine URL
    
    Returns:
        Response content string
    """
    client = PeacockClient(base_url)
    return client.quick_chat(prompt, model)


def analyze(file_path: str, question: str, model: str = "llama-3.3-70b-versatile") -> str:
    """
    Quick file analysis without creating a client.
    
    Args:
        file_path: Path to file
        question: Analysis question
        model: Model ID
    
    Returns:
        Response content string
    """
    client = PeacockClient()
    response = client.analyze_files([file_path], question, model)
    return response.content
