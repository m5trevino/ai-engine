"""
PEACOCK PIPELINE MODES — Three execution philosophies for large-context agentic builds.

RECON:    Plan every LLM call first, then execute sequentially.
RELAY:    Progressive handoff. Each call receives state from previous + next data chunk.
SWARM:    Parallel map-reduce. All chunks process simultaneously, then merge.

Each mode takes: bucket_items, objective, model_id, budget (ContextBudget)
Each mode returns: execution trace + final deliverable
"""

import json
import asyncio
import time
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from app.core.context_budget import ContextBudget
from app.core.key_manager import GroqPool
from app.utils.formatter import CLIFormatter
from openai import AsyncOpenAI


@dataclass
class Strike:
    """A single LLM call in a pipeline."""
    strike_id: str
    role: str  # 'planner', 'extractor', 'merger', 'generator', 'critic'
    system_prompt: str
    user_prompt: str
    estimated_input_tokens: int
    max_output_tokens: int
    depends_on: List[str] = field(default_factory=list)
    result: str = ""
    actual_tokens: int = 0
    latency_ms: int = 0
    status: str = "pending"  # pending, running, complete, failed


@dataclass
class PipelineResult:
    """Result of a full pipeline execution."""
    mode: str
    strikes: List[Strike]
    final_output: str
    total_tokens: int
    total_latency_ms: int
    token_budget_used: int
    docs_processed: int
    docs_total: int


# ─────────────────────────────────────────────────────────────────────────────
# SHARED: Execute a single strike against Groq
# ─────────────────────────────────────────────────────────────────────────────

async def _fire_strike(strike: Strike, model_id: str = "llama-3.3-70b-versatile") -> Strike:
    """Execute one LLM call."""
    start = time.time()
    asset = GroqPool.get_next()
    client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=asset.key)
    
    try:
        resp = await client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": strike.system_prompt},
                {"role": "user", "content": strike.user_prompt},
            ],
            temperature=0.3,
            max_tokens=strike.max_output_tokens,
        )
        strike.result = resp.choices[0].message.content or ""
        strike.actual_tokens = getattr(resp.usage, "total_tokens", 0) if resp.usage else 0
        strike.status = "complete"
    except Exception as e:
        strike.result = f"STRIKE FAILED: {e}"
        strike.status = "failed"
    finally:
        strike.latency_ms = int((time.time() - start) * 1000)
        await client.close()
    
    return strike


# ═════════════════════════════════════════════════════════════════════════════
# MODE 1: RECON — Plan every strike first, then execute
# ═════════════════════════════════════════════════════════════════════════════

async def recon_mode(
    bucket_items: Dict[str, Dict],
    objective: str,
    project_type_hint: str = "",
    model_id: str = "llama-3.3-70b-versatile",
) -> PipelineResult:
    """
    RECON MODE: Generate a complete mission plan, then execute it.
    
    Flow:
      1. Count bucket tokens
      2. Generate RECON PLAN (one LLM call that designs the entire pipeline)
      3. Parse plan into Strike objects
      4. Execute strikes sequentially
      5. Return results
    """
    budget = ContextBudget(model_id)
    analysis = budget.count_bucket(bucket_items)
    total_docs = analysis["doc_count"]
    total_tokens = analysis["total_tokens"]
    
    CLIFormatter.info(f"[RECON] Analyzing {total_docs} docs, {total_tokens:,} tokens...")
    
    # ── PHASE 1: RECON PLANNING ──
    # Pack a representative sample of docs for the planner (first ~3K tokens)
    sample_pack = budget.pack_bucket_items(bucket_items, 3000)
    
    recon_system = """You are a Mission Planner. Your job is to design a precise multi-strike pipeline for building a software project from research documents.

You will receive:
- An objective (what to build)
- Document count and total token count
- A sample of the research documents

You must output a RECON PLAN in this exact JSON format:
{
  "assessment": "Brief assessment of the docs and complexity",
  "strikes": [
    {
      "id": "strike_001",
      "role": "extractor",
      "purpose": "Extract auth invariants from docs 1-5",
      "system_prompt": "Full system prompt for this strike",
      "estimated_input_tokens": 4200,
      "max_output_tokens": 1500,
      "depends_on": []
    },
    {
      "id": "strike_002", 
      "role": "extractor",
      "purpose": "Extract auth invariants from docs 6-10",
      "system_prompt": "...",
      "estimated_input_tokens": 4200,
      "max_output_tokens": 1500,
      "depends_on": ["strike_001"]
    },
    {
      "id": "strike_003",
      "role": "merger",
      "purpose": "Merge all extracted invariants into unified JSON",
      "system_prompt": "...",
      "estimated_input_tokens": 3500,
      "max_output_tokens": 2000,
      "depends_on": ["strike_001", "strike_002"]
    },
    {
      "id": "strike_004",
      "role": "generator",
      "purpose": "Generate FastAPI auth service code",
      "system_prompt": "...",
      "estimated_input_tokens": 5000,
      "max_output_tokens": 3000,
      "depends_on": ["strike_003"]
    }
  ],
  "total_estimated_tokens": 14900,
  "risk_flags": ["Large bucket may need truncation", "Auth docs have conflicting advice"]
}

Rules:
- Every strike must fit within 6K total tokens (input + output).
- If docs are too large for one extractor strike, split into multiple extractors.
- The final strike MUST be a generator that outputs heredoc bash blocks.
- Be specific about which docs each strike processes.
- Output JSON only. No markdown, no explanation."""
    
    recon_user = f"""Objective: {objective}
Project Type: {project_type_hint}
Documents: {total_docs} docs, {total_tokens:,} total tokens
Token Budget Per Strike: 6,000 tokens (input + output)

=== DOCUMENT SAMPLE ===
{sample_pack['text']}

Generate the RECON PLAN as JSON only."""
    
    plan_strike = Strike(
        strike_id="recon_plan",
        role="planner",
        system_prompt=recon_system,
        user_prompt=recon_user,
        estimated_input_tokens=budget._count(recon_system) + budget._count(recon_user),
        max_output_tokens=3000,
    )
    
    plan_strike = await _fire_strike(plan_strike, model_id)
    
    # Parse the recon plan
    strikes = []
    try:
        plan_text = plan_strike.result
        json_start = plan_text.find('{')
        json_end = plan_text.rfind('}') + 1
        plan_json = json.loads(plan_text[json_start:json_end])
        
        for s in plan_json.get("strikes", []):
            strikes.append(Strike(
                strike_id=s["id"],
                role=s["role"],
                system_prompt=s["system_prompt"],
                user_prompt="",  # Filled during execution with actual doc chunks
                estimated_input_tokens=s.get("estimated_input_tokens", 4000),
                max_output_tokens=s.get("max_output_tokens", 1500),
                depends_on=s.get("depends_on", []),
            ))
        
        CLIFormatter.info(f"[RECON] Plan generated: {len(strikes)} strikes")
    except Exception as e:
        CLIFormatter.error(f"[RECON] Failed to parse plan: {e}. Falling back to default pipeline.")
        strikes = _default_strikes(budget, bucket_items, objective, project_type_hint)
    
    # ── PHASE 2: EXECUTION ──
    # Build doc chunks for extractor strikes
    doc_chunks = _chunk_docs_for_strikes(budget, bucket_items, strikes)
    
    # Execute sequentially, filling in user_prompts with actual data
    results_by_id: Dict[str, str] = {}
    for strike in strikes:
        # Resolve dependencies
        dep_results = "\n\n".join(
            f"=== RESULT FROM {dep_id} ===\n{results_by_id.get(dep_id, '')}"
            for dep_id in strike.depends_on
        )
        
        # Find doc chunk for this strike if it's an extractor
        doc_chunk = doc_chunks.get(strike.strike_id, "")
        
        # Build final user prompt
        parts = [f"Objective: {objective}\nType: {project_type_hint}"]
        if doc_chunk:
            parts.append(f"=== YOUR ASSIGNED DOCUMENTS ===\n{doc_chunk}")
        if dep_results:
            parts.append(f"=== INPUTS FROM PREVIOUS STRIKES ===\n{dep_results}")
        if strike.role == "generator":
            parts.append("Generate the complete project as heredoc bash blocks. Every file must be complete and runnable.")
        
        strike.user_prompt = "\n\n".join(parts)
        strike.estimated_input_tokens = budget._count(strike.system_prompt) + budget._count(strike.user_prompt)
        
        CLIFormatter.info(f"[RECON] Firing {strike.strike_id} ({strike.role})...")
        strike = await _fire_strike(strike, model_id)
        results_by_id[strike.strike_id] = strike.result
    
    # Find generator result as final output
    final_strike = next((s for s in strikes if s.role == "generator"), strikes[-1] if strikes else None)
    final_output = final_strike.result if final_strike else "No generator strike found."
    
    total_tokens_used = sum(s.actual_tokens for s in strikes)
    total_latency = sum(s.latency_ms for s in strikes)
    
    return PipelineResult(
        mode="recon",
        strikes=strikes,
        final_output=final_output,
        total_tokens=total_tokens_used,
        total_latency_ms=total_latency,
        token_budget_used=total_tokens_used,
        docs_processed=total_docs,
        docs_total=total_docs,
    )


# ═════════════════════════════════════════════════════════════════════════════
# MODE 2: RELAY — Progressive handoff with state passing
# ═════════════════════════════════════════════════════════════════════════════

async def relay_mode(
    bucket_items: Dict[str, Dict],
    objective: str,
    project_type_hint: str = "",
    model_id: str = "llama-3.3-70b-versatile",
) -> PipelineResult:
    """
    RELAY MODE: Chunked progressive handoff.
    
    Flow:
      1. Split docs into token-sized chunks
      2. Call 1: Process chunk 1 → extract invariants + produce "progress state"
      3. Call 2: Receive progress state + chunk 2 → update invariants + update state
      4. ... continue until all chunks consumed
      5. Final call: Receive final state → generate code
    
    The "progress state" is a compact JSON that accumulates knowledge across calls.
    """
    budget = ContextBudget(model_id)
    analysis = budget.count_bucket(bucket_items)
    total_docs = analysis["doc_count"]
    total_tokens = analysis["total_tokens"]
    
    CLIFormatter.info(f"[RELAY] {total_docs} docs, {total_tokens:,} tokens. Building relay chain...")
    
    # Chunk docs into batches that fit within budget minus state overhead
    state_overhead = 800  # Reserve tokens for progress state JSON
    chunk_budget = budget.safe_prompt_budget("invariant_extract") - state_overhead
    
    chunks = []
    remaining = dict(bucket_items)
    while remaining:
        packed = budget.pack_bucket_items(remaining, chunk_budget)
        if not packed["included_docs"]:
            # Force at least one doc even if oversized (truncate handled by pack)
            first_id = list(remaining.keys())[0]
            first_item = remaining[first_id]
            packed = {
                "text": f"--- {first_id} ({first_item.get('collection', '?')}) ---\n{first_item.get('note', '')}\n{budget.truncate_for_budget(first_item.get('content', ''), chunk_budget - 200)}",
                "included_docs": [first_id],
                "used_tokens": 0,
                "remaining_budget": 0,
            }
        chunks.append(packed)
        for doc_id in packed["included_docs"]:
            remaining.pop(doc_id, None)
    
    CLIFormatter.info(f"[RELAY] {len(chunks)} chunks created")
    
    # Relay system prompts
    relay_system = """You are a Relay Runner in a multi-call pipeline. Your job is to process assigned documents, extract invariants/patterns, and produce a compact PROGRESS STATE JSON for the next runner.

Output format (MANDATORY JSON):
{
  "invariants_extracted": [{"text": "...", "source": "doc_id"}],
  "patterns_found": [{"text": "...", "source": "doc_id"}],
  "constraints_noted": [{"text": "...", "source": "doc_id"}],
  "stack_hints": ["fastapi", "jwt"],
  "open_questions": ["Any ambiguities that need resolution"],
  "confidence": 0.85
}

Rules:
- Be concise. Max 15 items per array.
- The next runner will receive YOUR output plus new docs.
- Do NOT write code. Only extract knowledge.
- If this is the FINAL chunk, set "is_final": true."""
    
    final_system = """You are the Anchor Runner. You receive the accumulated progress state from all previous relay runners and the final document chunk. Your job is to produce the complete project as heredoc bash blocks.

Output format (MANDATORY):
cat > /path/to/file.py << 'EOF'
# complete runnable code
EOF
chmod +x /path/to/file.py

Rules:
- EVERY file must be complete — no TODOs, no placeholders.
- Use full absolute paths or clear relative paths.
- Quote EOF: 'EOF'
- NEVER use markdown triple backticks.
- Include chmod +x for executables."""
    
    # Execute relay chain
    strikes = []
    progress_state = {"invariants_extracted": [], "patterns_found": [], "constraints_noted": [], "stack_hints": [], "open_questions": [], "confidence": 1.0}
    
    for i, chunk in enumerate(chunks):
        is_final = (i == len(chunks) - 1)
        
        if is_final and len(chunks) > 1:
            # Final chunk: generate code using accumulated state
            user_prompt = (
                f"Objective: {objective}\nType: {project_type_hint}\n\n"
                f"=== ACCUMULATED PROGRESS STATE ===\n{json.dumps(progress_state, indent=2)}\n\n"
                f"=== FINAL DOCUMENT CHUNK ===\n{chunk['text']}\n\n"
                f"Generate the complete project. This is the final deliverable."
            )
            strike = Strike(
                strike_id=f"relay_final",
                role="generator",
                system_prompt=final_system,
                user_prompt=user_prompt,
                estimated_input_tokens=budget._count(final_system) + budget._count(user_prompt),
                max_output_tokens=3000,
                depends_on=[f"relay_{i-1}"] if i > 0 else [],
            )
        else:
            # Intermediate chunk: extract invariants, pass state forward
            state_json = json.dumps(progress_state, indent=2)
            user_prompt = (
                f"Objective: {objective}\nType: {project_type_hint}\n\n"
                f"=== PREVIOUS PROGRESS STATE ===\n{state_json}\n\n"
                f"=== YOUR ASSIGNED CHUNK ({i+1}/{len(chunks)}) ===\n{chunk['text']}\n\n"
                f"Extract invariants and update the progress state. Output JSON only."
            )
            strike = Strike(
                strike_id=f"relay_{i}",
                role="extractor",
                system_prompt=relay_system,
                user_prompt=user_prompt,
                estimated_input_tokens=budget._count(relay_system) + budget._count(user_prompt),
                max_output_tokens=1500,
                depends_on=[f"relay_{i-1}"] if i > 0 else [],
            )
        
        strike = await _fire_strike(strike, model_id)
        strikes.append(strike)
        
        # Parse progress state from result for next iteration
        if not is_final or len(chunks) == 1:
            try:
                result_text = strike.result
                json_start = result_text.find('{')
                json_end = result_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    new_state = json.loads(result_text[json_start:json_end])
                    # Merge arrays
                    for key in ["invariants_extracted", "patterns_found", "constraints_noted", "stack_hints", "open_questions"]:
                        progress_state[key] = list(dict.fromkeys(
                            progress_state.get(key, []) + new_state.get(key, [])
                        ))
                    progress_state["confidence"] = min(
                        progress_state.get("confidence", 1.0),
                        new_state.get("confidence", 1.0)
                    )
            except Exception:
                pass  # Carry forward existing state
        
        CLIFormatter.info(f"[RELAY] Chunk {i+1}/{len(chunks)} complete. State has {len(progress_state['invariants_extracted'])} invariants.")
    
    # If only one chunk, we need a separate generation call
    if len(chunks) == 1:
        gen_user = (
            f"Objective: {objective}\nType: {project_type_hint}\n\n"
            f"=== PROGRESS STATE ===\n{json.dumps(progress_state, indent=2)}\n\n"
            f"Generate the complete project as heredoc bash blocks."
        )
        gen_strike = Strike(
            strike_id="relay_generate",
            role="generator",
            system_prompt=final_system,
            user_prompt=gen_user,
            estimated_input_tokens=budget._count(final_system) + budget._count(gen_user),
            max_output_tokens=3000,
            depends_on=["relay_0"],
        )
        gen_strike = await _fire_strike(gen_strike, model_id)
        strikes.append(gen_strike)
        final_output = gen_strike.result
    else:
        final_output = strikes[-1].result if strikes else ""
    
    total_tokens_used = sum(s.actual_tokens for s in strikes)
    total_latency = sum(s.latency_ms for s in strikes)
    
    return PipelineResult(
        mode="relay",
        strikes=strikes,
        final_output=final_output,
        total_tokens=total_tokens_used,
        total_latency_ms=total_latency,
        token_budget_used=total_tokens_used,
        docs_processed=total_docs,
        docs_total=total_docs,
    )


# ═════════════════════════════════════════════════════════════════════════════
# MODE 3: SWARM — Parallel map-reduce
# ═════════════════════════════════════════════════════════════════════════════

async def swarm_mode(
    bucket_items: Dict[str, Dict],
    objective: str,
    project_type_hint: str = "",
    model_id: str = "llama-3.3-70b-versatile",
) -> PipelineResult:
    """
    SWARM MODE: Parallel map-reduce.
    
    Flow:
      1. Split docs into token-sized chunks
      2. Fire ALL chunks simultaneously (asyncio.gather)
      3. Each call extracts invariants from its chunk
      4. Merge all results into unified invariants
      5. Single final call generates code from merged invariants
    
    Fastest execution. Highest token burn (parallel API calls).
    """
    budget = ContextBudget(model_id)
    analysis = budget.count_bucket(bucket_items)
    total_docs = analysis["doc_count"]
    total_tokens = analysis["total_tokens"]
    
    CLIFormatter.info(f"[SWARM] {total_docs} docs, {total_tokens:,} tokens. Spawning swarm...")
    
    # Chunk docs
    chunk_budget = budget.safe_prompt_budget("invariant_extract")
    chunks = []
    remaining = dict(bucket_items)
    while remaining:
        packed = budget.pack_bucket_items(remaining, chunk_budget - 400)
        if not packed["included_docs"]:
            first_id = list(remaining.keys())[0]
            first_item = remaining[first_id]
            packed = {
                "text": f"--- {first_id} ({first_item.get('collection', '?')}) ---\n{first_item.get('note', '')}\n{budget.truncate_for_budget(first_item.get('content', ''), chunk_budget - 600)}",
                "included_docs": [first_id],
                "used_tokens": 0,
                "remaining_budget": 0,
            }
        chunks.append(packed)
        for doc_id in packed["included_docs"]:
            remaining.pop(doc_id, None)
    
    CLIFormatter.info(f"[SWARM] {len(chunks)} worker chunks. Firing in parallel...")
    
    # MAP: Fire all extractor strikes in parallel
    worker_system = """You are a Swarm Worker. Process your assigned documents and extract invariants, patterns, constraints, and stack hints.

Output format (JSON only):
{"invariants": [{"text": "...", "source": "doc_id"}], "patterns": [...], "constraints": [...], "stack_recommendations": [...]}

Rules:
- Be concise. Max 10 items per array.
- Only extract items relevant to the objective.
- Do NOT write code."""
    
    worker_strikes = []
    for i, chunk in enumerate(chunks):
        user_prompt = (
            f"Objective: {objective}\nType: {project_type_hint}\n\n"
            f"=== YOUR CHUNK ({i+1}/{len(chunks)}) ===\n{chunk['text']}\n\n"
            f"Extract invariants as JSON only."
        )
        worker_strikes.append(Strike(
            strike_id=f"swarm_worker_{i}",
            role="extractor",
            system_prompt=worker_system,
            user_prompt=user_prompt,
            estimated_input_tokens=budget._count(worker_system) + budget._count(user_prompt),
            max_output_tokens=1500,
        ))
    
    # Parallel execution
    completed_workers = await asyncio.gather(*[_fire_strike(s, model_id) for s in worker_strikes])
    
    # REDUCE: Merge all worker outputs
    all_invariants = []
    all_patterns = []
    all_constraints = []
    all_stacks = []
    
    for strike in completed_workers:
        try:
            result_text = strike.result
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                parsed = json.loads(result_text[json_start:json_end])
                all_invariants.extend(parsed.get("invariants", []))
                all_patterns.extend(parsed.get("patterns", []))
                all_constraints.extend(parsed.get("constraints", []))
                all_stacks.extend(parsed.get("stack_recommendations", []))
        except Exception:
            pass
    
    all_stacks = list(dict.fromkeys(all_stacks))
    
    merged = json.dumps({
        "invariants": all_invariants,
        "patterns": all_patterns,
        "constraints": all_constraints,
        "stack_recommendations": all_stacks,
    }, indent=2)
    
    CLIFormatter.info(f"[SWARM] Reduce complete. {len(all_invariants)} invariants from {len(chunks)} workers.")
    
    # FINAL: Generate from merged results
    gen_system = """You are a Senior Engineer. Generate complete, runnable code files as bash heredoc commands.

Output format (MANDATORY):
cat > /path/to/file.py << 'EOF'
# complete runnable code
EOF
chmod +x /path/to/file.py

Rules:
1. EVERY file must be complete — no TODOs, no placeholders.
2. Use full absolute paths or clear relative paths.
3. Quote EOF: 'EOF'
4. NEVER use markdown triple backticks.
5. Include chmod +x for executables."""
    
    gen_user = (
        f"Objective: {objective}\nType: {project_type_hint}\n\n"
        f"=== MERGED INTELLIGENCE FROM {len(chunks)} WORKERS ===\n{merged}\n\n"
        f"Generate the complete project as heredoc bash blocks."
    )
    
    gen_strike = Strike(
        strike_id="swarm_generator",
        role="generator",
        system_prompt=gen_system,
        user_prompt=gen_user,
        estimated_input_tokens=budget._count(gen_system) + budget._count(gen_user),
        max_output_tokens=3000,
    )
    gen_strike = await _fire_strike(gen_strike, model_id)
    
    all_strikes = list(completed_workers) + [gen_strike]
    total_tokens_used = sum(s.actual_tokens for s in all_strikes)
    total_latency = sum(s.latency_ms for s in all_strikes)
    
    # For swarm, the effective latency is the max parallel latency + final latency
    # (since workers ran in parallel)
    parallel_latency = max(s.latency_ms for s in completed_workers) if completed_workers else 0
    effective_latency = parallel_latency + gen_strike.latency_ms
    
    return PipelineResult(
        mode="swarm",
        strikes=all_strikes,
        final_output=gen_strike.result,
        total_tokens=total_tokens_used,
        total_latency_ms=effective_latency,
        token_budget_used=total_tokens_used,
        docs_processed=total_docs,
        docs_total=total_docs,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _default_strikes(
    budget: ContextBudget,
    bucket_items: Dict[str, Dict],
    objective: str,
    project_type_hint: str,
) -> List[Strike]:
    """Fallback pipeline if recon plan parsing fails."""
    # Simple 3-stage fallback
    stages = budget.split_bucket_for_stages(bucket_items, objective, project_type_hint)
    strikes = []
    for s in stages:
        strikes.append(Strike(
            strike_id=s.name,
            role=s.name,
            system_prompt=s.system_prompt,
            user_prompt=s.user_prompt,
            estimated_input_tokens=s.estimated_prompt_tokens,
            max_output_tokens=s.max_completion_tokens,
        ))
    return strikes


def _chunk_docs_for_strikes(
    budget: ContextBudget,
    bucket_items: Dict[str, Dict],
    strikes: List[Strike],
) -> Dict[str, str]:
    """Map doc chunks to extractor strikes."""
    doc_chunks = {}
    remaining = dict(bucket_items)
    
    for strike in strikes:
        if strike.role == "extractor":
            budget_for_docs = budget.safe_prompt_budget("invariant_extract") - budget._count(strike.system_prompt) - 300
            packed = budget.pack_bucket_items(remaining, budget_for_docs)
            if packed["included_docs"]:
                doc_chunks[strike.strike_id] = packed["text"]
                for doc_id in packed["included_docs"]:
                    remaining.pop(doc_id, None)
    
    return doc_chunks


# ─────────────────────────────────────────────────────────────────────────────
# UNIFIED ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

async def run_pipeline(
    mode: str,
    bucket_items: Dict[str, Dict],
    objective: str,
    project_type_hint: str = "",
    model_id: str = "llama-3.3-70b-versatile",
) -> PipelineResult:
    """Run a pipeline in the specified mode."""
    if mode == "recon":
        return await recon_mode(bucket_items, objective, project_type_hint, model_id)
    elif mode == "relay":
        return await relay_mode(bucket_items, objective, project_type_hint, model_id)
    elif mode == "swarm":
        return await swarm_mode(bucket_items, objective, project_type_hint, model_id)
    else:
        raise ValueError(f"Unknown mode: {mode}. Choose: recon, relay, swarm")


def format_pipeline_report(result: PipelineResult) -> str:
    """Generate a human-readable report of pipeline execution."""
    lines = [
        f"=== PIPELINE REPORT: {result.mode.upper()} ===",
        f"Documents: {result.docs_processed}/{result.docs_total}",
        f"Total tokens burned: {result.total_tokens:,}",
        f"Total latency: {result.total_latency_ms:,}ms",
        f"Strikes fired: {len(result.strikes)}",
        f"",
        f"=== STRIKE LOG ===",
    ]
    for s in result.strikes:
        status_icon = "✅" if s.status == "complete" else "❌"
        lines.append(
            f"{status_icon} {s.strike_id} | {s.role} | "
            f"in={s.estimated_input_tokens:,} out={s.max_output_tokens:,} | "
            f"actual={s.actual_tokens:,} | {s.latency_ms}ms"
        )
    lines.append("")
    lines.append("=== FINAL OUTPUT PREVIEW ===")
    lines.append(result.final_output[:800] + "..." if len(result.final_output) > 800 else result.final_output)
    lines.append("=== END REPORT ===")
    return "\n".join(lines)
