"""
PEACOCK ENGINE — Plan Generator (TB-011)
Creates a complete "Path to Completion" plan for file processing with
model assignment and key selection based on real-time telemetry.

Scope:
  • Ingest a file and split it into token-safe chunks using TB-003
  • Assign the best available key via TB-007 intelligent selector
  • Calculate estimated execution time per chunk and total
  • Save the plan as JSON for review / audit

References:
  • app.core.tiktoken_counter (TB-003)
  • app.core.rate_limit_tracker (TB-001)
  • app.core.key_manager (TB-007)
  • app.config.MODEL_REGISTRY
"""

import os
import time
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Literal
from pathlib import Path

from app.core.tiktoken_counter import count_text
from app.core.key_manager import get_pool
from app.core.plan_scheduler import PlanScheduler, ScheduledPlan
from app.config import MODEL_REGISTRY


# ═══════════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ChunkPlan:
    """A single chunk in the execution plan."""
    chunk_id: int
    text: str
    token_count: int
    model_id: str
    key_label: str
    route: Literal["direct"]
    estimated_seconds: float
    rationale: str
    wait_seconds: float = 0.0
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    completed_at: Optional[float] = None
    error: Optional[str] = None


@dataclass
class ExecutionPlan:
    """Full plan for processing a file."""
    file_path: str
    total_chunks: int
    total_tokens: int
    estimated_total_seconds: float   # Sum of raw processing times
    chunks: List[ChunkPlan]
    model_id: str
    config: Dict[str, Any]
    makespan_seconds: float = 0.0    # Wall-clock time with pacing / concurrency (TB-013)
    status: Literal["pending", "queued", "running", "completed", "failed", "archived"] = "pending"
    completed_at: Optional[float] = None
    created_at: float = field(default_factory=time.time)
    execution_log: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize plan to a review-friendly dict."""
        return {
            "file_path": self.file_path,
            "total_chunks": self.total_chunks,
            "total_tokens": self.total_tokens,
            "estimated_total_seconds": self.estimated_total_seconds,
            "makespan_seconds": self.makespan_seconds,
            "status": self.status,
            "model_id": self.model_id,
            "config": self.config,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "execution_log": self.execution_log,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "text_preview": (c.text[:200] + "...") if len(c.text) > 200 else c.text,
                    "token_count": c.token_count,
                    "model_id": c.model_id,
                    "key_label": c.key_label,
                    "route": c.route,
                    "estimated_seconds": c.estimated_seconds,
                    "wait_seconds": c.wait_seconds,
                    "status": c.status,
                    "rationale": c.rationale,
                }
                for c in self.chunks
            ],
        }

    def to_full_dict(self) -> Dict[str, Any]:
        """Serialize the complete plan, including full chunk text, for storage."""
        return {
            "file_path": self.file_path,
            "total_chunks": self.total_chunks,
            "total_tokens": self.total_tokens,
            "estimated_total_seconds": self.estimated_total_seconds,
            "makespan_seconds": self.makespan_seconds,
            "status": self.status,
            "model_id": self.model_id,
            "config": self.config,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "execution_log": self.execution_log,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "text": c.text,
                    "token_count": c.token_count,
                    "model_id": c.model_id,
                    "key_label": c.key_label,
                    "route": c.route,
                    "estimated_seconds": c.estimated_seconds,
                    "wait_seconds": c.wait_seconds,
                    "status": c.status,
                    "completed_at": c.completed_at,
                    "error": c.error,
                    "rationale": c.rationale,
                }
                for c in self.chunks
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionPlan":
        """Rehydrate an ExecutionPlan from a storage dict."""
        chunk_dicts = data.get("chunks", [])
        chunks = [ChunkPlan(**c) for c in chunk_dicts]
        return cls(
            file_path=data["file_path"],
            total_chunks=data.get("total_chunks", len(chunks)),
            total_tokens=data.get("total_tokens", 0),
            estimated_total_seconds=data.get("estimated_total_seconds", 0.0),
            chunks=chunks,
            model_id=data["model_id"],
            config=data.get("config", {}),
            makespan_seconds=data.get("makespan_seconds", 0.0),
            status=data.get("status", "pending"),
            completed_at=data.get("completed_at"),
            created_at=data.get("created_at", time.time()),
            execution_log=data.get("execution_log", []),
        )

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    def to_full_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_full_dict(), indent=indent)

    def save(self, path: Optional[str] = None) -> str:
        """Save plan as JSON for review. Returns the saved path."""
        path = path or f"plans/{Path(self.file_path).stem}_plan.json"
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(self.to_json(), encoding="utf-8")
        return str(out)


# ═══════════════════════════════════════════════════════════════════════════════
# CHUNKING ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def _split_by_paragraphs(text: str) -> List[str]:
    """Split text at double-newline boundaries."""
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def _split_by_code_boundaries(text: str) -> List[str]:
    """
    Attempt to split Python-like code at function / class boundaries.
    Falls back to line-based splitting if no clear boundaries exist.
    """
    import re
    pattern = re.compile(r"^(def\s+|class\s+)", re.MULTILINE)
    matches = list(pattern.finditer(text))

    if len(matches) < 2:
        return text.splitlines()

    chunks = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunks.append(text[start:end].strip())
    return chunks


def _chunk_text(text: str, model_id: str, max_chunk_tokens: int) -> List[str]:
    """
    Split text into token-safe chunks.

    Strategy:
      1. Try natural boundaries (paragraphs for text, functions for code)
      2. Merge small pieces until near max_chunk_tokens
      3. If a single piece exceeds max_chunk_tokens, split by lines
    """
    total_tokens = count_text(text, model_id)
    if total_tokens <= max_chunk_tokens:
        return [text]

    is_code = (
        "def " in text or "class " in text or "import " in text or "#" in text
    ) and text.count("\n") > 10

    if is_code:
        pieces = _split_by_code_boundaries(text)
    else:
        pieces = _split_by_paragraphs(text)

    chunks: List[str] = []
    current: List[str] = []
    current_tokens = 0

    for piece in pieces:
        piece_tokens = count_text(piece, model_id)

        if piece_tokens > max_chunk_tokens:
            lines = piece.splitlines()
            for line in lines:
                line_tokens = count_text(line, model_id)
                if current_tokens + line_tokens > max_chunk_tokens and current:
                    chunks.append("\n".join(current))
                    current = [line]
                    current_tokens = line_tokens
                else:
                    current.append(line)
                    current_tokens += line_tokens
            continue

        if current_tokens + piece_tokens > max_chunk_tokens and current:
            chunks.append("\n\n".join(current))
            current = [piece]
            current_tokens = piece_tokens
        else:
            current.append(piece)
            current_tokens += piece_tokens

    if current:
        chunks.append("\n\n".join(current))

    return chunks


# ═══════════════════════════════════════════════════════════════════════════════
# PLAN GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class PlanGenerator:
    """
    Generates execution plans with model assignment and key selection.

    Usage:
        generator = PlanGenerator()
        plan = await generator.generate_plan("/path/to/file.py", model_id="llama-3.3-70b-versatile")
        plan.save()
        for chunk in plan.chunks:
            print(f"Chunk {chunk.chunk_id} via {chunk.key_label}")
    """

    DEFAULT_MODEL = "llama-3.3-70b-versatile"
    DEFAULT_TARGET_CHUNK_TOKENS = 8000
    DEFAULT_SYSTEM_PROMPT_TOKENS = 100
    DEFAULT_COMPLETION_HEADROOM = 1000

    _THROUGHPUT: Dict[str, float] = {
        "groq": 250.0,
        "opencode-go": 120.0,
        "opencode-zen": 120.0,
        "openrouter": 100.0,
        "ollama": 60.0,
        "hetzner": 80.0,
    }

    def __init__(self):
        pass

    @staticmethod
    def _get_model_config(model_id: str):
        return next(
            (m for m in MODEL_REGISTRY if m.id == model_id and m.status == "active"),
            None,
        )

    def _max_chunk_tokens(self, model_id: str) -> int:
        """Compute max safe chunk size for a model."""
        model_cfg = self._get_model_config(model_id)
        max_ctx = model_cfg.context_window if model_cfg and model_cfg.context_window else 131072
        safe = max_ctx - self.DEFAULT_SYSTEM_PROMPT_TOKENS - self.DEFAULT_COMPLETION_HEADROOM
        return min(safe, self.DEFAULT_TARGET_CHUNK_TOKENS)

    def _estimate_seconds(self, chunk_tokens: int, gateway: str) -> float:
        """Rough timing estimate based on throughput."""
        base = chunk_tokens / self._THROUGHPUT.get(gateway, 100.0)
        return round(base + 0.5, 2)

    def _pick_key(self, model_id: str, estimated_tokens: int) -> str:
        """Synchronous key selection fallback."""
        model_cfg = self._get_model_config(model_id)
        gateway = model_cfg.gateway if model_cfg else "groq"
        pool = get_pool(gateway)

        if pool and pool.deck:
            try:
                asset = pool.get_next()
                return asset.account
            except Exception:
                pass
        return "default"

    async def _pick_key_async(self, model_id: str, estimated_tokens: int) -> str:
        """Async key selection using TB-007 intelligent selector."""
        model_cfg = self._get_model_config(model_id)
        gateway = model_cfg.gateway if model_cfg else "groq"
        pool = get_pool(gateway)

        if pool and pool.deck:
            try:
                asset = await pool.get_next_intelligent(model_id, estimated_tokens)
                return asset.account
            except Exception:
                pass
        return self._pick_key(model_id, estimated_tokens)

    async def generate_plan(
        self,
        file_path: str,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> ExecutionPlan:
        """
        Generate a complete execution plan for a file.

        Args:
            file_path: Path to the file to process
            model_id: Target model (defaults to DEFAULT_MODEL)
            system_prompt: Optional system prompt to account for in token budget

        Returns:
            ExecutionPlan with per-chunk routing decisions
        """
        model_id = model_id or self.DEFAULT_MODEL
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        text = path.read_text(encoding="utf-8", errors="replace")
        max_chunk = self._max_chunk_tokens(model_id)

        if system_prompt:
            sys_tokens = count_text(system_prompt, model_id)
            max_chunk -= sys_tokens
            max_chunk = max(max_chunk, 512)

        chunks = _chunk_text(text, model_id, max_chunk)

        model_cfg = self._get_model_config(model_id)
        gateway = model_cfg.gateway if model_cfg else "groq"

        chunk_plans: List[ChunkPlan] = []
        total_tokens = 0
        total_seconds = 0.0

        for idx, chunk_text in enumerate(chunks):
            tokens = count_text(chunk_text, model_id)

            # Assign key
            key_label = await self._pick_key_async(model_id, tokens)

            # Estimate timing
            est_seconds = self._estimate_seconds(tokens, gateway)

            chunk_plans.append(
                ChunkPlan(
                    chunk_id=idx,
                    text=chunk_text,
                    token_count=tokens,
                    model_id=model_id,
                    key_label=key_label,
                    route="direct",
                    estimated_seconds=est_seconds,
                    rationale=f"direct via {gateway}",
                )
            )
            total_tokens += tokens
            total_seconds += est_seconds

        plan = ExecutionPlan(
            file_path=str(file_path),
            total_chunks=len(chunks),
            total_tokens=total_tokens,
            estimated_total_seconds=round(total_seconds, 2),
            makespan_seconds=round(total_seconds, 2),
            chunks=chunk_plans,
            model_id=model_id,
            config={"target_chunk_tokens": self.DEFAULT_TARGET_CHUNK_TOKENS},
        )

        # TB-013: apply rate-limit-aware scheduling so each chunk has an accurate
        # wait_seconds that accounts for RPM pacing and concurrency limits.
        scheduled = PlanScheduler(
            proxy_overhead=1.0,
            fixed_overhead=0.5,
            proxy_fixed_overhead=0.0,
        ).schedule(plan)
        for chunk, sched in zip(plan.chunks, scheduled.chunks):
            chunk.wait_seconds = sched.wait_seconds
            chunk.estimated_seconds = sched.estimated_seconds
        plan.makespan_seconds = scheduled.makespan_seconds

        return plan


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════

async def generate_plan(
    file_path: str,
    model_id: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> ExecutionPlan:
    """One-shot plan generation."""
    generator = PlanGenerator()
    return await generator.generate_plan(file_path, model_id=model_id, system_prompt=system_prompt)
