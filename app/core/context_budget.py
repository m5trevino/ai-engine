"""
GROQ CONTEXT BUDGET — Local token counting + stage splitting for multi-turn agentic builds.

Problem: Dumping 20 full memory docs into research_context creates a ~20K token bomb
that blows past Groq's 6K TPM limit.

Solution:
  1. Count tokens locally using tiktoken (cl100k_base for Llama models)
  2. Define a per-stage token budget (e.g., 4K prompt + 2K completion = 6K TPM)
  3. Split bucket contents into stage-sized chunks
  4. Each stage has a single job: extract invariants → plan → generate code

Usage:
    budget = ContextBudget(model_id="llama-3.3-70b-versatile")
    stages = budget.split_bucket_for_stages(bucket_items, stage_type="invariant_extract")
    # stages[0] fits in 4K tokens and tells the LLM to extract invariants
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.utils.groq_token_counter import GroqTokenCounter


@dataclass
class Stage:
    """A single stage in a multi-turn build pipeline."""
    name: str
    system_prompt: str
    user_prompt: str
    estimated_prompt_tokens: int
    max_completion_tokens: int
    estimated_total_tokens: int
    metadata: Dict[str, Any]


# Groq on-demand tier hard limits
GROQ_ON_DEMAND_TPM = 6_000
GROQ_CONTEXT_WINDOWS = {
    "llama-3.1-8b-instant": 128_000,
    "llama-3.3-70b-versatile": 128_000,
    "llama-3.3-70b-specdec": 128_000,
    "llama-3.2-1b-preview": 128_000,
    "llama-3.2-3b-preview": 128_000,
    "llama-3.2-11b-vision-preview": 128_000,
    "llama-3.2-90b-vision-preview": 128_000,
    "llama-4-scout-17b-16e-instruct": 256_000,
    "llama-guard-3-8b": 8_192,
    "mixtral-8x7b-32768": 32_768,
    "mixtral-8x22b-instruct": 65_536,
    "gemma2-9b-it": 8_192,
    "qwen-32b": 128_000,
    "default": 128_000,
}

# Per-stage completion token reservations
# We reserve headroom so the model can actually respond
STAGE_COMPLETION_RESERVE = {
    "invariant_extract": 1_500,   # Extracting invariants is verbose
    "plan": 2_000,                # Architecture plans are medium-length
    "generate": 3_000,            # Code generation needs the most room
    "validate": 1_000,            # Validation reports are concise
    "default": 1_500,
}


class ContextBudget:
    """
    Token budget manager for Groq multi-stage agentic builds.
    
    Each stage gets a safe prompt budget = min(TPM, context_window) - completion_reserve - overhead.
    """

    def __init__(self, model_id: str = "llama-3.3-70b-versatile"):
        self.model_id = model_id
        self.counter = GroqTokenCounter()
        self.tpm_limit = GROQ_ON_DEMAND_TPM
        self.context_window = GROQ_CONTEXT_WINDOWS.get(model_id, GROQ_CONTEXT_WINDOWS["default"])
        # Safe budget: take the LOWER of TPM limit and context window, then reserve completion + overhead
        self.effective_limit = min(self.tpm_limit, self.context_window)
        # Format overhead: system message + user wrapper + JSON schema + tool definitions
        self.overhead_tokens = 200

    def _count(self, text: str) -> int:
        """Count tokens in a text string."""
        if not text:
            return 0
        return self.counter.count_tokens(text, self.model_id)

    def _count_messages(self, messages: List[Dict]) -> int:
        """Count tokens in OpenAI-style message list."""
        return self.counter.count_messages_tokens(messages, self.model_id)

    def safe_prompt_budget(self, stage_type: str = "default") -> int:
        """
        Calculate safe prompt token budget for a stage.
        
        Returns:
            Maximum tokens that can go into the prompt for this stage.
        """
        completion_reserve = STAGE_COMPLETION_RESERVE.get(stage_type, STAGE_COMPLETION_RESERVE["default"])
        return self.effective_limit - completion_reserve - self.overhead_tokens

    def count_bucket(self, items: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Count total tokens in a project bucket.
        
        Args:
            items: bucket["items"] dict: doc_id -> {collection, content, metadata, note}
            
        Returns:
            Dict with total_tokens, doc_count, and per-doc breakdown.
        """
        total = 0
        per_doc = []
        for doc_id, item in items.items():
            content = item.get("content", "")
            note = item.get("note", "")
            doc_text = f"--- {doc_id} ---\n{note}\n{content}"
            tokens = self._count(doc_text)
            total += tokens
            per_doc.append({
                "doc_id": doc_id,
                "collection": item.get("collection", "?"),
                "tokens": tokens,
                "chars": len(doc_text),
            })
        
        per_doc.sort(key=lambda x: x["tokens"], reverse=True)
        return {
            "total_tokens": total,
            "doc_count": len(items),
            "per_doc": per_doc,
            "model": self.model_id,
            "context_window": self.context_window,
            "tpm_limit": self.tpm_limit,
        }

    def truncate_for_budget(self, text: str, budget: int, truncate_msg: str = "\n...[truncated]") -> str:
        """
        Truncate text to fit within a token budget.
        Uses binary search for efficiency.
        """
        if self._count(text) <= budget:
            return text
        
        # Binary search for the right character length
        low, high = 0, len(text)
        best = 0
        while low <= high:
            mid = (low + high) // 2
            candidate = text[:mid] + truncate_msg
            if self._count(candidate) <= budget:
                best = mid
                low = mid + 1
            else:
                high = mid - 1
        
        return text[:best] + truncate_msg

    def pack_bucket_items(self, items: Dict[str, Dict], budget: int) -> str:
        """
        Pack as many bucket items as possible into a token budget.
        Returns the packed text and metadata about what fit.
        """
        lines = []
        used = 0
        included = []
        
        # Sort by relevance if available, else by length (shorter first = more docs fit)
        sorted_items = sorted(
            items.items(),
            key=lambda x: len(x[1].get("content", "")),
        )
        
        for doc_id, item in sorted_items:
            content = item.get("content", "")
            note = item.get("note", "")
            coll = item.get("collection", "?")
            doc_text = f"--- {doc_id} ({coll}) ---\n{note}\n{content}\n"
            doc_tokens = self._count(doc_text)
            
            if used + doc_tokens > budget:
                break
            
            lines.append(doc_text)
            used += doc_tokens
            included.append(doc_id)
        
        return {
            "text": "\n".join(lines),
            "included_docs": included,
            "used_tokens": used,
            "remaining_budget": budget - used,
        }

    def split_bucket_for_stages(
        self,
        items: Dict[str, Dict],
        project_description: str = "",
        project_type_hint: str = "",
    ) -> List[Stage]:
        """
        Split bucket contents into predetermined stages for a Groq build.
        
        Pipeline:
          Stage 1: INVARIANT_EXTRACT — Feed docs, extract architectural invariants
          Stage 2: PLAN — Feed invariants + description, produce file tree + decisions
          Stage 3: GENERATE — Feed plan + invariants, produce heredoc code files
        
        Each stage's prompt is guaranteed to fit within the safe budget.
        """
        stages = []
        bucket_analysis = self.count_bucket(items)
        total_tokens = bucket_analysis["total_tokens"]
        
        # --- STAGE 1: INVARIANT EXTRACTION ---
        s1_budget = self.safe_prompt_budget("invariant_extract")
        s1_system = """You are an Architecture Analyst. Your job is to read the provided research documents and extract ONLY the architectural invariants, patterns, and constraints relevant to building the requested project.

Output format (JSON):
{
  "invariants": [
    {"id": "inv_001", "text": "All auth endpoints must validate JWT tokens", "source_doc": "doc_id", "confidence": 0.9}
  ],
  "patterns": [
    {"id": "pat_001", "text": "Use OAuth2PasswordBearer for FastAPI auth", "source_doc": "doc_id"}
  ],
  "constraints": [
    {"id": "con_001", "text": "Max 6K TPM per call", "source_doc": "doc_id"}
  ],
  "stack_recommendations": ["fastapi", "jwt", "sqlalchemy"]
}

Rules:
- Be concise. Each invariant should be 1-2 sentences.
- Only extract items relevant to the project description.
- Do NOT write code. Only extract knowledge.
"""
        s1_packed = self.pack_bucket_items(items, s1_budget - self._count(s1_system) - 100)
        s1_user = f"""Project: {project_description}
Type: {project_type_hint}

=== RESEARCH DOCUMENTS ===
{s1_packed['text']}

=== INSTRUCTION ===
Extract architectural invariants, patterns, constraints, and stack recommendations from the documents above. Output as JSON only."""
        
        stages.append(Stage(
            name="invariant_extract",
            system_prompt=s1_system,
            user_prompt=s1_user,
            estimated_prompt_tokens=self._count(s1_system) + self._count(s1_user),
            max_completion_tokens=STAGE_COMPLETION_RESERVE["invariant_extract"],
            estimated_total_tokens=self._count(s1_system) + self._count(s1_user) + STAGE_COMPLETION_RESERVE["invariant_extract"],
            metadata={
                "included_docs": s1_packed["included_docs"],
                "total_docs": len(items),
                "stage_budget": s1_budget,
            },
        ))
        
        # --- STAGE 2: ARCHITECTURE PLAN ---
        s2_budget = self.safe_prompt_budget("plan")
        s2_system = """You are a Solutions Architect. Your job is to produce a precise architecture plan based on extracted invariants.

Output format:
1. FILE TREE — List every file to create with full paths
2. DEPENDENCIES — List all pip packages needed
3. ARCHITECTURE DECISIONS — Bullet list of key decisions with rationale
4. INVARIANT COMPLIANCE MAP — Which invariant maps to which file

Rules:
- Be specific. No vague hand-waving.
- Every decision must trace back to an invariant.
- Do NOT write code. Only produce the plan.
"""
        s2_user_template = f"""Project: {project_description}
Type: {project_type_hint}

=== EXTRACTED INVARIANTS ===
{{invariants_json}}

=== INSTRUCTION ===
Produce the architecture plan. Be specific about file paths, dependencies, and how each invariant is satisfied."""
        
        stages.append(Stage(
            name="plan",
            system_prompt=s2_system,
            user_prompt=s2_user_template,
            estimated_prompt_tokens=self._count(s2_system) + self._count(s2_user_template),
            max_completion_tokens=STAGE_COMPLETION_RESERVE["plan"],
            estimated_total_tokens=self._count(s2_system) + self._count(s2_user_template) + STAGE_COMPLETION_RESERVE["plan"],
            metadata={
                "depends_on": "invariant_extract",
                "stage_budget": s2_budget,
            },
        ))
        
        # --- STAGE 3: CODE GENERATION ---
        s3_budget = self.safe_prompt_budget("generate")
        s3_system = """You are a Senior Engineer. Your job is to generate complete, runnable code files as bash heredoc commands.

Output format (MANDATORY):
cat > /path/to/file.py << 'EOF'
# complete file content
EOF
chmod +x /path/to/file.py  # if executable

Rules:
1. EVERY file must be complete — no TODOs, no placeholders.
2. Use full absolute paths or clear relative paths.
3. Quote the EOF delimiter: 'EOF'
4. NEVER use markdown triple backticks around heredoc blocks.
5. Include chmod +x for executables and service files.
6. All code must satisfy the invariants provided.
"""
        s3_user_template = f"""Project: {project_description}
Type: {project_type_hint}

=== ARCHITECTURE PLAN ===
{{plan_text}}

=== INVARIANTS ===
{{invariants_json}}

=== INSTRUCTION ===
Generate ALL files from the architecture plan as heredoc bash blocks. Every file must be complete and runnable."""
        
        stages.append(Stage(
            name="generate",
            system_prompt=s3_system,
            user_prompt=s3_user_template,
            estimated_prompt_tokens=self._count(s3_system) + self._count(s3_user_template),
            max_completion_tokens=STAGE_COMPLETION_RESERVE["generate"],
            estimated_total_tokens=self._count(s3_system) + self._count(s3_user_template) + STAGE_COMPLETION_RESERVE["generate"],
            metadata={
                "depends_on": "plan",
                "stage_budget": s3_budget,
            },
        ))
        
        return stages

    def can_fit_in_single_call(self, text: str, stage_type: str = "default") -> bool:
        """Check if text fits in a single Groq call for this stage type."""
        return self._count(text) <= self.safe_prompt_budget(stage_type)

    def report(self, items: Dict[str, Dict]) -> str:
        """Generate a human-readable token budget report."""
        analysis = self.count_bucket(items)
        budget = self.safe_prompt_budget("invariant_extract")
        
        lines = [
            f"=== GROQ CONTEXT BUDGET REPORT ===",
            f"Model: {self.model_id}",
            f"Context window: {self.context_window:,} tokens",
            f"TPM limit: {self.tpm_limit:,} tokens",
            f"Effective limit: {self.effective_limit:,} tokens",
            f"",
            f"Bucket contents: {analysis['doc_count']} docs, {analysis['total_tokens']:,} total tokens",
            f"Single-call budget (invariant_extract): {budget:,} tokens",
            f"Fits in one call: {'YES' if analysis['total_tokens'] <= budget else 'NO — needs ' + str((analysis['total_tokens'] // budget) + 1) + ' stages'}",
            f"",
            f"Largest documents:",
        ]
        for doc in analysis["per_doc"][:5]:
            lines.append(f"  {doc['doc_id'][:50]} | {doc['tokens']:,} tokens | {doc['chars']:,} chars")
        
        return "\n".join(lines)


def count_tokens_groq_local(text: str, model_id: str = "llama-3.3-70b-versatile") -> int:
    """Quick standalone function."""
    return ContextBudget(model_id=model_id)._count(text)


if __name__ == "__main__":
    # Demo
    budget = ContextBudget("llama-3.3-70b-versatile")
    
    # Fake bucket
    fake_items = {
        "doc_001": {"collection": "tech_vault", "content": "FastAPI uses pydantic for validation." * 100, "note": "Important pattern"},
        "doc_002": {"collection": "app_invariants", "content": "All endpoints must rate-limit." * 50, "note": "Security invariant"},
        "doc_003": {"collection": "bindings", "content": "POST /users -> create user form." * 30, "note": "API mapping"},
    }
    
    print(budget.report(fake_items))
    print()
    
    stages = budget.split_bucket_for_stages(fake_items, "Build a FastAPI auth service", "fastapi")
    for s in stages:
        print(f"\n=== STAGE: {s.name} ===")
        print(f"  Prompt tokens: {s.estimated_prompt_tokens:,}")
        print(f"  Completion reserve: {s.max_completion_tokens:,}")
        print(f"  Total estimate: {s.estimated_total_tokens:,}")
        print(f"  Metadata: {s.metadata}")
