from pydantic import BaseModel
from typing import List, Literal, Optional
import json
from pathlib import Path

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

# Load persistent frozen status
FROZEN_FILE = Path("frozen_models.json")
FROZEN_IDS = []
if FROZEN_FILE.exists():
    try:
        FROZEN_IDS = json.loads(FROZEN_FILE.read_text())
    except:
        pass

MODEL_REGISTRY: List[ModelConfig] = [
    # GOOGLE - EXHAUSTIVE FLEET (Verified April 2026)
    ModelConfig(
        id="models/gemini-2.5-pro", gateway="google", tier="expensive", 
        note="Stable release (June 17th, 2025) of Gemini 2.5 Pro", rpm=150, rpd=1000, tpm=2000000,
        context_window=1048576, input_price_1m=3.50, output_price_1m=10.50
    ),
    ModelConfig(
        id="models/gemini-2.5-flash", gateway="google", tier="cheap", 
        note="Stable version of Gemini 2.5 Flash, our mid-size multimodal model", rpm=1000, rpd=10000, tpm=1000000,
        context_window=1048576, input_price_1m=0.35, output_price_1m=0.70
    ),
    # NOTE: Gemini 2.0 flash models removed — decommissioned by Google
    ModelConfig(
        id="models/gemini-2.5-flash-preview-tts", gateway="google", tier="expensive", 
        note="Gemini 2.5 Flash Preview TTS", rpm=100, tpm=200000, context_window=8192
    ),
    ModelConfig(
        id="models/gemini-2.5-pro-preview-tts", gateway="google", tier="expensive", 
        note="Gemini 2.5 Pro Preview TTS", rpm=100, tpm=200000, context_window=8192
    ),
    ModelConfig(
        id="models/gemma-3-1b-it", gateway="google", tier="free", note="Gemma 3 1B Instruct"
    ),
    ModelConfig(
        id="models/gemma-3-4b-it", gateway="google", tier="free", note="Gemma 3 4B Instruct"
    ),
    ModelConfig(
        id="models/gemma-3-12b-it", gateway="google", tier="free", note="Gemma 3 12B Instruct"
    ),
    ModelConfig(
        id="models/gemma-3-27b-it", gateway="google", tier="free", note="Gemma 3 27B Instruct"
    ),
    ModelConfig(
        id="models/gemma-3n-e4b-it", gateway="google", tier="free", note="Gemma 3n E4B Instruct"
    ),
    ModelConfig(
        id="models/gemma-3n-e2b-it", gateway="google", tier="free", note="Gemma 3n E2B Instruct"
    ),
    ModelConfig(
        id="models/gemma-4-26b-a4b-it", gateway="google", tier="cheap", note="Gemma 4 26B A4B IT", context_window=262144
    ),
    ModelConfig(
        id="models/gemma-4-31b-it", gateway="google", tier="cheap", note="Gemma 4 31B IT", context_window=262144
    ),
    ModelConfig(
        id="models/gemini-flash-latest", gateway="google", tier="cheap", note="Latest release of Gemini Flash"
    ),
    ModelConfig(
        id="models/gemini-flash-lite-latest", gateway="google", tier="free", note="Latest release of Gemini Flash-Lite"
    ),
    ModelConfig(
        id="models/gemini-pro-latest", gateway="google", tier="expensive", note="Latest release of Gemini Pro"
    ),
    ModelConfig(
        id="models/gemini-2.5-flash-lite", gateway="google", tier="free", 
        note="Stable version of Gemini 2.5 Flash-Lite (July 2025)", rpm=4000, tpm=4000000,
        context_window=1048576, input_price_1m=0.10, output_price_1m=0.30
    ),
    ModelConfig(
        id="models/gemini-2.5-flash-image", gateway="google", tier="expensive", 
        note="Nano Banana (Gemini 2.5 Flash Preview Image)", rpm=500, rpd=2000, tpm=500000,
        context_window=32768
    ),
    ModelConfig(
        id="models/gemini-3-pro-preview", gateway="google", tier="expensive", 
        note="Gemini 3 Pro Preview - Frontier Reasoning", rpm=25, rpd=250, tpm=2000000,
        context_window=1048576
    ),
    ModelConfig(
        id="models/gemini-3-flash-preview", gateway="google", tier="cheap", 
        note="Gemini 3 Flash Preview - Speed specialist", rpm=1000, rpd=10000, tpm=2000000,
        context_window=1048576
    ),
    ModelConfig(
        id="models/gemini-3.1-pro-preview", gateway="google", tier="expensive", 
        note="Gemini 3.1 Pro Preview", rpm=25, rpd=250, tpm=2000000, context_window=1048576
    ),
    ModelConfig(
        id="models/gemini-3.1-pro-preview-customtools", gateway="google", tier="expensive", 
        note="Gemini 3.1 Pro Preview (Optimized Tools)", rpm=25, rpd=250, tpm=2000000, context_window=1048576
    ),
    ModelConfig(
        id="models/gemini-3.1-flash-lite-preview", gateway="google", tier="free", 
        note="Gemini 3.1 Flash Lite Preview", rpm=4000, rpd=150000, tpm=4000000, context_window=1048576
    ),
    ModelConfig(
        id="models/gemini-3-pro-image-preview", gateway="google", tier="expensive", 
        note="Nano Banana Pro (Gemini 3 Pro Image Preview)", rpm=20, rpd=250, tpm=100000, context_window=131072
    ),
    ModelConfig(
        id="models/nano-banana-pro-preview", gateway="google", tier="expensive", 
        note="Nano Banana Pro Alternative Alias", rpm=20, rpd=250, tpm=100000, context_window=131072
    ),
    ModelConfig(
        id="models/gemini-3.1-flash-image-preview", gateway="google", tier="expensive", 
        note="Nano Banana 2 (Gemini 3.1 Flash Image Preview)", rpm=100, rpd=1000, tpm=200000, context_window=65536
    ),
    ModelConfig(
        id="models/lyria-3-clip-preview", gateway="google", tier="expensive", 
        note="Lyria 3 30s model Preview", rpm=150, rpd=500, tpm=4000000, context_window=1048576
    ),
    ModelConfig(
        id="models/lyria-3-pro-preview", gateway="google", tier="expensive", 
        note="Lyria 3 Pro Preview - Music Engine", rpm=150, rpd=500, tpm=4000000, context_window=1048576
    ),
    ModelConfig(
        id="models/gemini-robotics-er-1.5-preview", gateway="google", tier="expensive", 
        note="Gemini Robotics-ER 1.5 Preview", rpm=100, tpm=1000000, context_window=1048576
    ),
    ModelConfig(
        id="models/gemini-2.5-computer-use-preview-10-2025", gateway="google", tier="expensive", 
        note="Gemini 2.5 Computer Use Preview", rpm=150, rpd=10000, tpm=2000000, context_window=131072
    ),
    ModelConfig(
        id="models/deep-research-pro-preview-12-2025", gateway="google", tier="expensive", 
        note="Deep Research Pro Preview (Dec 2025)", rpm=5, rpd=50, tpm=1000000, context_window=131072
    ),
    ModelConfig(
        id="models/gemini-embedding-001", gateway="google", tier="free", 
        note="Obtain distributed representation of text", context_window=2048
    ),
    ModelConfig(
        id="models/gemini-embedding-2-preview", gateway="google", tier="free", 
        note="Multimodal Contextual Embedding", context_window=8192
    ),

    # GROQ - FRONT-LINE OSS FLEET
    ModelConfig(
        id="meta-llama/llama-4-scout-17b-16e-instruct", gateway="groq", tier="free",
        note="Llama 4 Frontier Scout (MoE 16e)", rpm=2000, rpd=10000, tpm=1000000,
        context_window=131072
    ),
    ModelConfig(
        id="openai/gpt-oss-120b", gateway="groq", tier="expensive",
        note="GPT-OSS flagship reasoning", rpm=300, rpd=5000, tpm=500000,
        context_window=131072
    ),
    ModelConfig(
        id="openai/gpt-oss-20b", gateway="groq", tier="cheap",
        note="GPT-OSS high-speed variant", rpm=1000, rpd=10000, tpm=1000000,
        context_window=131072
    ),
    ModelConfig(
        id="llama-3.3-70b-versatile", gateway="groq", tier="expensive",
        note="Llama 3.3 70B Versatile", rpm=1000, rpd=10000, tpm=1000000,
        context_window=131072
    ),
    ModelConfig(
        id="llama-3.1-8b-instant", gateway="groq", tier="free",
        note="Llama 3.1 8B Instant", rpm=5000, rpd=100000, tpm=1000000,
        context_window=131072
    ),
    # NOTE: Removed legacy/discontinued Groq models: llama3-70b-8192, llama3-8b-8192, mixtral-8x7b-32768, gemma2-9b-it
    ModelConfig(
        id="qwen/qwen3-32b", gateway="groq", tier="cheap",
        note="Qwen 3 32B High-Logic", rpm=500, rpd=5000, tpm=500000,
        context_window=131072
    ),
    ModelConfig(
        id="groq/compound", gateway="groq", tier="expensive", note="Groq Compound Reasoner",
        context_window=131072
    ),
    ModelConfig(
        id="groq/compound-mini", gateway="groq", tier="expensive", note="Groq Compound Mini Reasoner",
        context_window=131072
    ),
    ModelConfig(
        id="openai/gpt-oss-safeguard-20b", gateway="groq", tier="cheap", note="GPT-OSS Safeguard 20B",
        context_window=131072
    ),
    ModelConfig(
        id="moonshotai/kimi-k2-instruct", gateway="groq", tier="expensive", note="Moonshot Kimi K2 Instruct",
        status="deprecated"
    ),
    ModelConfig(
        id="moonshotai/kimi-k2-instruct-0905", gateway="groq", tier="expensive", note="Moonshot Kimi K2 Instruct 0905",
        status="deprecated"
    ),
    ModelConfig(
        id="meta-llama/llama-prompt-guard-2-86m", gateway="groq", tier="free", note="Llama Prompt Guard 2 86M",
        context_window=512
    ),
    ModelConfig(
        id="meta-llama/llama-prompt-guard-2-22m", gateway="groq", tier="free", note="Llama Prompt Guard 2 22M",
        context_window=512
    ),
    ModelConfig(
        id="allam-2-7b", gateway="groq", tier="free", note="Allam 2 7B",
        context_window=4096
    ),

    # DEEPSEEK & MISTRAL
    ModelConfig(
        id="deepseek-chat", gateway="deepseek", tier="cheap", note="DeepSeek V3 (Chat)"
    ),
    ModelConfig(
        id="deepseek-reasoner", gateway="deepseek", tier="expensive", note="DeepSeek R1 (Reasoner)"
    ),
    ModelConfig(
        id="mistral-large-latest", gateway="mistral", tier="expensive", note="Mistral Large 2"
    )
]

# Load dynamically registered models
try:
    _dynamic_path = os.path.join(os.path.dirname(__file__), "dynamic_models.json")
    if os.path.exists(_dynamic_path):
        with open(_dynamic_path, "r") as _f:
            _dynamic_models = json.load(_f)
        for _dm in _dynamic_models:
            if not any(m.id == _dm["id"] for m in MODEL_REGISTRY):
                MODEL_REGISTRY.append(ModelConfig(**_dm))
except Exception:
    pass  # Ignore corrupted dynamic file

# Apply Status Overrides
for m in MODEL_REGISTRY:
    if m.id in FROZEN_IDS:
        m.status = "frozen"

# CONFIGURATION ENGINE
class Config:
    def __init__(self):
        import os
        self.MASTER_KEY = os.getenv("MASTER_KEY", os.getenv("PEACOCK_KEY"))
        self.PORT = int(os.getenv("PORT", 3099))
        self.ENV = os.getenv("ENV", "production")
        self.DEBUG = os.getenv("DEBUG", "false").lower() == "true"

config = Config()
