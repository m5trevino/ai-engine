from pydantic import BaseModel
from typing import List, Literal, Optional

class ModelConfig(BaseModel):
    id: str
    gateway: Literal['groq', 'google', 'deepseek', 'mistral']
    tier: Literal['free', 'cheap', 'expensive', 'custom', 'deprecated']
    note: str
    status: Literal['active', 'frozen', 'deprecated'] = 'active'
    context_window: Optional[int] = None
    # Rate Limits
    rpm: Optional[int] = None
    tpm: Optional[int] = None
    rpd: Optional[int] = None
    # Pricing (per 1M tokens)
    input_price_1m: float = 0.0
    output_price_1m: float = 0.0

# 🏎️ HELLCAT PROTOCOL - PERFORMANCE MODES
PERFORMANCE_MODES = {
    "stealth": {"name": "BLACK KEY (Stealth)", "multiplier": 3.0, "color": "\033[90m"},
    "balanced": {"name": "BLUE KEY (Balanced)", "multiplier": 1.15, "color": "\033[94m"},
    "apex": {"name": "RED KEY (Apex)", "multiplier": 1.02, "color": "\033[91m"}
}

import json
from pathlib import Path

# Load persistent frozen status
FROZEN_FILE = Path("frozen_models.json")
FROZEN_IDS = []
if FROZEN_FILE.exists():
    try:
        FROZEN_IDS = json.loads(FROZEN_FILE.read_text())
    except:
        pass

MODEL_REGISTRY: List[ModelConfig] = [
    # GOOGLE (March 2026 Fleet)
    ModelConfig(
        id="gemini-3.1-pro", gateway="google", tier="expensive", 
        note="Flagship Reasoning (64k output)", rpm=5, rpd=100, tpm=250000,
        input_price_1m=2.00, output_price_1m=12.00, context_window=1000000
    ),
    ModelConfig(
        id="gemini-3.1-flash", gateway="google", tier="cheap", 
        note="Frontier performance everyday driver", rpm=15, rpd=1000, tpm=250000,
        input_price_1m=0.25, output_price_1m=0.75, context_window=1000000
    ),
    ModelConfig(
        id="gemini-3.1-flash-lite", gateway="google", tier="free", 
        note="Sub-50ms latency king", rpm=15, rpd=1000, tpm=250000,
        input_price_1m=0.10, output_price_1m=0.40, context_window=1000000
    ),
    ModelConfig(
        id="gemini-3.1-flash-live", gateway="google", tier="expensive", 
        note="Native Multimodal Streaming", rpm=15, rpd=1000, tpm=250000,
        input_price_1m=0.30, output_price_1m=2.50
    ),
    ModelConfig(
        id="gemini-2.5-pro", gateway="google", tier="expensive", 
        note="Verified stable reasoning", rpm=150, rpd=1000, tpm=2000000,
        input_price_1m=3.50, output_price_1m=10.50, context_window=2000000
    ),
    ModelConfig(
        id="gemini-2.5-flash", gateway="google", tier="cheap", 
        note="Production Workhorse", rpm=1000, rpd=10000, tpm=1000000,
        input_price_1m=0.30, output_price_1m=2.50, context_window=1000000
    ),
    ModelConfig(
        id="gemini-2.5-flash-lite", gateway="google", tier="free", 
        note="Stable efficiency tier", rpm=4000, rpd=150000, tpm=4000000,
        input_price_1m=0.10, output_price_1m=0.30
    ),
    ModelConfig(
        id="gemini-2.0-flash-lite", gateway="google", tier="free", 
        note="Legacy High Volume", rpm=4000, rpd=999999, tpm=4000000,
        status="active"
    ),
    ModelConfig(
        id="gemini-pro-latest", gateway="google", tier="expensive", 
        note="Alias for latest stable Pro", status="active"
    ),
    ModelConfig(
        id="gemini-flash-latest", gateway="google", tier="cheap", 
        note="Alias for latest stable Flash", status="active"
    ),
    ModelConfig(
        id="gemini-embedding-2-preview", gateway="google", tier="cheap", 
        note="First Multimodal Embedding Model", status="active"
    ),
    ModelConfig(
        id="gemini-embedding-001", gateway="google", tier="free", 
        note="Standard Text Embeddings", status="active"
    ),
    ModelConfig(
        id="nano-banana-pro", gateway="google", tier="expensive", 
        note="SOTA Native Image Gen/Edit", input_price_1m=80.00
    ),
    ModelConfig(
        id="nano-banana-2", gateway="google", tier="expensive", 
        note="High-volume Image Creation", input_price_1m=40.00
    ),

    # GROQ (LPU Powered - Official Live List)
    ModelConfig(
        id="openai/gpt-oss-120b", gateway="groq", tier="expensive", 
        note="OpenAI Reasoning on LPU", rpm=30, rpd=1000, tpm=250000,
        input_price_1m=0.60, output_price_1m=0.80, context_window=131072
    ),
    ModelConfig(
        id="openai/gpt-oss-20b", gateway="groq", tier="cheap", 
        note="1000 tokens/sec speed king", rpm=30, rpd=1000, tpm=250000,
        input_price_1m=0.20, output_price_1m=0.30, context_window=131072
    ),
    ModelConfig(
        id="openai/gpt-oss-safeguard-20b", gateway="groq", tier="free", 
        note="Replacement for Llama Guard", status="active", context_window=131072
    ),
    ModelConfig(
        id="meta-llama/llama-4-scout-17b-16e-instruct", gateway="groq", tier="cheap", 
        note="Fastest Multimodal MoE (460 t/s)", rpm=30, rpd=1000, tpm=30000,
        input_price_1m=0.11, output_price_1m=0.34, context_window=131072
    ),
    ModelConfig(
        id="moonshotai/kimi-k2-instruct-0905", gateway="groq", tier="expensive", 
        note="The 256k Context Beast", rpm=30, rpd=1000, tpm=30000,
        input_price_1m=0.50, output_price_1m=0.75, context_window=262144
    ),
    ModelConfig(
        id="moonshotai/kimi-k2-instruct", gateway="groq", tier="expensive", 
        note="High performance reasoning", rpm=30, rpd=1000, tpm=30000,
        input_price_1m=0.50, output_price_1m=0.75, context_window=131072
    ),
    ModelConfig(
        id="llama-3.3-70b-versatile", gateway="groq", tier="expensive", 
        note="Complex reasoning standard", rpm=30, rpd=1000, tpm=12000,
        input_price_1m=0.59, output_price_1m=0.79, context_window=131072
    ),
    ModelConfig(
        id="llama-3.1-8b-instant", gateway="groq", tier="free", 
        note="High-volume instant text", rpm=30, rpd=14400, tpm=6000,
        input_price_1m=0.05, output_price_1m=0.08, context_window=131072
    ),
    ModelConfig(
        id="groq/compound", gateway="groq", tier="expensive", 
        note="Groq Optimized Logic", status="active", context_window=131072
    ),
    ModelConfig(
        id="groq/compound-mini", gateway="groq", tier="cheap", 
        note="Groq Optimized Mini", status="active", context_window=131072
    ),
    ModelConfig(
        id="qwen/qwen3-32b", gateway="groq", tier="expensive", 
        note="Alibaba Cloud Reasoning", status="active", context_window=131072
    ),
    ModelConfig(
        id="allam-2-7b", gateway="groq", tier="free", 
        note="SDAIA Specialized Model", status="active", context_window=4096
    ),
    ModelConfig(
        id="canopylabs/orpheus-v1-english", gateway="groq", tier="custom", 
        note="Canopy Labs English", status="active", context_window=4000
    ),
    ModelConfig(
        id="canopylabs/orpheus-arabic-saudi", gateway="groq", tier="custom", 
        note="Canopy Labs Arabic", status="active", context_window=4000
    ),
    ModelConfig(
        id="meta-llama/llama-prompt-guard-2-86m", gateway="groq", tier="free", 
        note="Meta Security Guard (Large)", status="active", context_window=512
    ),
    ModelConfig(
        id="meta-llama/llama-prompt-guard-2-22m", gateway="groq", tier="free", 
        note="Meta Security Guard (Small)", status="active", context_window=512
    ),
    ModelConfig(
        id="whisper-large-v3-turbo", gateway="groq", tier="cheap", 
        note="OpenAI Audio Transcription (Fast)", status="active", context_window=448
    ),
    ModelConfig(
        id="whisper-large-v3", gateway="groq", tier="cheap", 
        note="OpenAI Audio Transcription (High Def)", status="active", context_window=448
    ),
]

# Apply Status Overrides
for m in MODEL_REGISTRY:
    if m.id in FROZEN_IDS:
        m.status = "frozen"
