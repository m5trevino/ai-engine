"""
Gemini Token Counter using Google GenAI SDK.
Based on: gemini-tree-token-counter + geminitokencounter repos

Key formulas from Google's documentation:
- Text: ~4 characters per token (varies by language)
- Images <=384px: 258 tokens
- Images >384px: 258 tokens per 768x768 tile
- Video: 263 tokens per second
- Audio: 32 tokens per second
- PDF: treated as images (1 page = 1 image)
"""

import re
from typing import Union, List, Dict, Optional, Any
from pathlib import Path
import os


class GeminiTokenCounter:
    """Accurate token counting for Gemini models using official API."""
    
    # Multimodal token rates (from Google docs)
    IMAGE_SMALL_TOKENS = 258  # Both dimensions <=384px
    IMAGE_TILE_TOKENS = 258   # Per 768x768 tile for larger images
    VIDEO_TOKENS_PER_SEC = 263
    AUDIO_TOKENS_PER_SEC = 32
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize token counter.
        
        Args:
            api_key: Google API key. If None, loads from GOOGLE_KEYS env var.
        """
        if api_key:
            self.api_key = api_key
        else:
            # Parse from env var format: LABEL:key,LABEL2:key2
            env_keys = os.getenv("GOOGLE_KEYS", "")
            if env_keys:
                # Take first key
                first_entry = env_keys.split(",")[0]
                if ":" in first_entry:
                    self.api_key = first_entry.split(":", 1)[1].strip()
                else:
                    self.api_key = first_entry.strip()
            else:
                self.api_key = None
        
        self._client = None
    
    @property
    def client(self):
        """Lazy-load Google GenAI client."""
        if self._client is None:
            try:
                from google import genai
                if not self.api_key:
                    raise ValueError("No Google API key available")
                self._client = genai.Client(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "google-genai SDK required. Install: pip install google-genai"
                )
        return self._client
    
    def count_tokens_api(self, model: str, contents: Union[str, List, Dict]) -> int:
        """
        Count tokens using Google's official count_tokens API.
        This is the MOST accurate method.
        
        Args:
            model: Model ID (e.g., "models/gemini-2.0-flash-lite-001")
            contents: Text, file, or multimodal content
            
        Returns:
            Total token count
        """
        try:
            response = self.client.models.count_tokens(
                model=model,
                contents=contents
            )
            return response.total_tokens
        except Exception as e:
            # Log error and fall back to estimation
            print(f"[TokenCounter] API error: {e}, falling back to estimation")
            return self.estimate_tokens(str(contents))
    
    def estimate_tokens(self, text: str) -> int:
        """
        Offline estimation using regex-based tokenization.
        Ported from gemini-tree-token-counter.
        
        For Gemini: ~4 characters per token, but varies by language.
        This regex-based approach is more accurate than simple char/4.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        if not text:
            return 0
        
        # Character classes for tokenization (from gemini-tree-token-counter)
        cons = "bcdfghjklmnpqrstvwxzßçñ"
        vowels = "aeiouyàáâäèéêëìíîïòóôöùúûüýÿæœ"
        cons_upper = "BCDFGHJKLMNPQRSTVWXZÇÑ"
        vowels_upper = "AEIOUYÀÁÂÄÈÉÊËÌÍÎÏÒÓÔÖÙÚÛÜÝŸÆŒ"
        
        # Build regex patterns
        lowercase_word = f"[ ]?(?:[{cons}]{{0,3}}[{vowels}]{{1,3}}[{cons}]{{0,3}}){{1,3}}"
        uppercase_word = f"[ ]?(?:[{cons_upper}]{{0,3}}[{vowels_upper}]{{1,3}}[{cons_upper}]{{0,3}}){{1,3}}"
        titlecase_word = f"[ ]?[A-ZÀÁÂÄÈÉÊËÌÍÎÏÒÓÔÖÙÚÛÜÝŸÆŒÇÑ][a-zàáâäèéêëìíîïòóôöùúûüýÿæœßçñ]{{1,8}}"
        common_abbrev = r"pdf|png|http(?:s)?|rfp|www|PDF|PNG|HTTP|HTTP(?:S)?|RFP|WWW"
        non_latin_word = r"[ ]?[^\u0000-\u007F\u00A0-\u00FF\u0100-\u017F\ue000-\uf8ff]{1,5}"
        
        patterns = [
            r"\d", r"\n+", r"\r+", r"\t+", r"\x0b+", r"\f+", r"[\ue000-\uf8ff]",
            common_abbrev, lowercase_word, titlecase_word, uppercase_word,
            f"[{cons}]{{1,2}}", f"[{cons_upper}]{{1,2}}", non_latin_word,
            r"\(\)", r"\[\]", r"\{\}", r"([.=#_-])\1{{1,15}}",
            r"[ ]?[!@#$%^&*()_+\-=\[\]{}\\|;:'\",.<>/?`~]{{1,3}}", r"[ ]+", r"."
        ]
        
        combined = re.compile("|".join(patterns))
        return sum(1 for _ in combined.finditer(text))
    
    def count_multimodal(
        self,
        text: str = "",
        images: Optional[List[Dict[str, int]]] = None,
        video_seconds: float = 0,
        audio_seconds: float = 0
    ) -> Dict[str, int]:
        """
        Calculate tokens for multimodal input.
        
        Args:
            text: Text content
            images: List of image dicts with 'width', 'height' keys
            video_seconds: Duration of video in seconds
            audio_seconds: Duration of audio in seconds
            
        Returns:
            Dict with breakdown: text_tokens, image_tokens, video_tokens, 
            audio_tokens, total_tokens
        """
        # Text tokens
        text_tokens = self.estimate_tokens(text)
        
        # Image tokens
        image_tokens = 0
        if images:
            for img in images:
                w = img.get('width', 0)
                h = img.get('height', 0)
                
                if w <= 384 and h <= 384:
                    # Small image
                    image_tokens += self.IMAGE_SMALL_TOKENS
                else:
                    # Large image - calculate tiles
                    tiles_w = (w + 767) // 768
                    tiles_h = (h + 767) // 768
                    image_tokens += tiles_w * tiles_h * self.IMAGE_TILE_TOKENS
        
        # Video tokens
        video_tokens = int(video_seconds * self.VIDEO_TOKENS_PER_SEC)
        
        # Audio tokens
        audio_tokens = int(audio_seconds * self.AUDIO_TOKENS_PER_SEC)
        
        return {
            "text_tokens": text_tokens,
            "image_tokens": image_tokens,
            "video_tokens": video_tokens,
            "audio_tokens": audio_tokens,
            "total_tokens": text_tokens + image_tokens + video_tokens + audio_tokens
        }
    
    def count_file(self, file_path: Union[str, Path]) -> int:
        """
        Count tokens in a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            Token count
        """
        path = Path(file_path)
        if not path.exists():
            return 0
        
        # Check if image
        if path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp']:
            try:
                from PIL import Image
                with Image.open(path) as img:
                    w, h = img.size
                    result = self.count_multimodal(images=[{'width': w, 'height': h}])
                    return result['total_tokens']
            except ImportError:
                # Fallback: estimate as small image
                return self.IMAGE_SMALL_TOKENS
        
        # Check if PDF
        if path.suffix.lower() == '.pdf':
            # PDFs treated as images, 1 page = 1 image
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(path)
                page_count = len(doc)
                doc.close()
                # Estimate each page as one image tile
                return page_count * self.IMAGE_TILE_TOKENS
            except ImportError:
                # Fallback: estimate 1 token per 4 bytes
                return path.stat().st_size // 4
        
        # Text file
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            return self.estimate_tokens(content)
        except Exception:
            return 0
    
    def count_tokens_offline(self, text: str, model: Optional[str] = None) -> int:
        """Alias for estimate_tokens for backward compatibility."""
        return self.estimate_tokens(text)

    @staticmethod
    def count_tokens(model: str, text: str, files: List[str] = []) -> int:
        """Static method for PeacockTokenCounter compatibility."""
        counter = GeminiTokenCounter()
        total = counter.estimate_tokens(text)
        for f in files:
            total += counter.count_file(f)
        return total


# Convenience functions for quick use
def count_tokens_gemini(text: str, model: str = "models/gemini-2.0-flash-lite-001", api_key: Optional[str] = None) -> int:
    """Quick function to count tokens using API."""
    counter = GeminiTokenCounter(api_key=api_key)
    return counter.count_tokens_api(model, text)


def estimate_tokens_gemini(text: str) -> int:
    """Quick function to estimate tokens offline."""
    counter = GeminiTokenCounter()
    return counter.estimate_tokens(text)


if __name__ == "__main__":
    # Test
    counter = GeminiTokenCounter()
    
    test_text = "Hello, how are you today?"
    
    print("=== Gemini Token Counter Test ===")
    print(f"Text: {test_text}")
    print(f"Estimated tokens: {counter.estimate_tokens(test_text)}")
    
    # Test multimodal
    result = counter.count_multimodal(
        text="Describe this image",
        images=[{'width': 1024, 'height': 768}],
        video_seconds=10
    )
    print(f"\nMultimodal breakdown:")
    for k, v in result.items():
        print(f"  {k}: {v}")
