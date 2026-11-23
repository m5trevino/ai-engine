"""
PROJECT ENGINE — Iterative project generation orchestrator.

Pipeline:
  1. INGEST   → Query memory for relevant invariants, patterns, past projects
  2. ARCHITECT → LLM designs project structure (file tree, deps, decisions)
  3. GENERATE  → LLM generates files in heredoc format (batched)
  4. VALIDATE  → Local + memory checks on generated files
  5. PACKAGE   → Assemble deploy.sh + README + manifest

The engine loops: if validation fails, feed errors back and regenerate.
"""

import json
import time
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from app.core.striker import execute_strike
from app.core.memory_engine import query_memory
from app.core.layer_instructions import build_system_prompt, LAYER_DOCTRINE
from app.config import MODEL_REGISTRY
from app.core.heredoc_parser import (
    extract_heredocs, HeredocFile, generate_deploy_script,
    generate_file_tree, validate_heredoc_syntax
)
from app.core.project_validator import (
    validate_project, ValidationResult, format_validation_report,
    ValidationIssue
)


def _get_safe_max_tokens(model_id: str, prompt: str, reserved_output: int = 2000) -> int:
    """Get safe max_tokens that won't exceed Groq's TPM limit."""
    model_cfg = next((m for m in MODEL_REGISTRY if m.id == model_id), None)
    
    # Estimate prompt tokens (rough: 4 chars ~= 1 token)
    estimated_prompt_tokens = len(prompt) // 4
    
    # Groq on-demand tier has a hard 6000 TPM limit regardless of model advertised TPM
    effective_tpm = 6000
    
    if model_cfg and model_cfg.tpm:
        # Use the lower of advertised TPM and conservative limit
        effective_tpm = min(model_cfg.tpm, 6000) if model_cfg.gateway == "groq" else model_cfg.tpm
    
    # Reserve some headroom
    available = effective_tpm - estimated_prompt_tokens - 500
    
    # Cap at reasonable limits
    if model_cfg and model_cfg.gateway == "google":
        return min(max(available, 1000), 8192)
    
    return min(max(available, 1000), reserved_output)


@dataclass
class ProjectConfig:
    """Configuration for a project generation run."""
    name: str
    description: str
    model: str
    gateway: str
    temperature: float = 0.3
    max_iterations: int = 3
    files_per_batch: int = 3
    enable_memory: bool = True
    memory_collections: Optional[List[str]] = None
    project_type_hint: Optional[str] = None  # e.g., "fastapi", "react", "cli"
    research_context: Optional[str] = None  # Pre-gathered memory context (skip ingest)


@dataclass
class ArchitecturePlan:
    """Output of the ARCHITECT phase."""
    project_name: str
    description: str
    file_tree: List[Dict[str, Any]]  # Each has: path, purpose, invariants, dependencies
    dependencies: List[str]
    architecture_decisions: List[str]
    deployment_notes: List[str]
    applicable_invariants: Dict[str, List[str]]  # file_path -> list of invariant law_ids
    raw_response: str = ""


@dataclass
class GenerationBatch:
    """A batch of files generated in one API call."""
    files: List[HeredocFile]
    prompt_tokens: int = 0
    completion_tokens: int = 0
    duration_ms: int = 0
    raw_response: str = ""


@dataclass
class ProjectResult:
    """Final output of the project generation pipeline."""
    config: ProjectConfig
    architecture: Optional[ArchitecturePlan] = None
    files: List[HeredocFile] = field(default_factory=list)
    validation_results: List[ValidationResult] = field(default_factory=list)
    deploy_script: str = ""
    readme: str = ""
    manifest: Dict[str, Any] = field(default_factory=dict)
    total_tokens: int = 0
    total_cost: float = 0.0
    total_duration_ms: int = 0
    iterations: int = 0
    errors: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, architecting, generating, validating, packaging, complete, failed


# --- PHASE 1: INGEST ---

async def _ingest_memory(config: ProjectConfig) -> Dict[str, Any]:
    """Query Peacock memory for relevant context."""
    if not config.enable_memory:
        return {"status": "skipped", "context": "", "total_hits": 0}

    # If research context was pre-gathered (e.g., from project bucket), use it directly
    if config.research_context:
        return {
            "status": "ok",
            "query": "preloaded_research_context",
            "total_hits": 0,
            "context": config.research_context,
        }

    # Query with project description
    collections = config.memory_collections or [
        "app_invariants", "agent_invariants", "tech_vault", "bindings"
    ]

    mem_result = await query_memory(
        query=f"{config.description} {config.project_type_hint or ''}",
        collections=collections,
        n=5,
        timeout=10.0,
    )

    return mem_result


# --- PHASE 2: ARCHITECT ---

ARCHITECT_SYSTEM_PROMPT = """You are PEACOCK ARCHITECT. Design complete projects. Output valid JSON only.

{
  "project_name": "name",
  "description": "summary",
  "file_tree": [
    {"path": "rel/path.py", "purpose": "what it does", "invariants": [], "dependencies": [], "size_estimate": "small"}
  ],
  "dependencies": ["package"],
  "architecture_decisions": ["why"],
  "deployment_notes": ["how to run"]
}

Rules:
- Relative paths only
- Include configs, tests, README, requirements
- size_estimate: small|medium|large
- Keep file count reasonable (5-12 files)"""


async def _architect_phase(config: ProjectConfig, memory_context: str) -> ArchitecturePlan:
    """Run the ARCHITECT phase: design project structure."""
    
    truncated_memory = _truncate_context(memory_context, max_chars=1500)
    
    prompt = f"""{ARCHITECT_SYSTEM_PROMPT}

Memory:
{truncated_memory}

Request: {config.description}
Type: {config.project_type_hint or 'auto'}

Design the file tree."""

    result = await execute_strike(
        gateway=config.gateway,
        model_id=config.model,
        prompt=prompt,
        temperature=config.temperature,
        max_tokens=2048,
    )
    
    raw = result.get("content", "")
    
    # Try to parse JSON from the response
    plan_data = _extract_json_from_response(raw)
    
    if not plan_data:
        raise ValueError(f"ARCHITECT phase failed to produce valid JSON. Raw: {raw[:500]}")
    
    # Clean up file_tree — remove entries with embedded content (malformed LLM output)
    clean_tree = []
    seen_paths = set()
    for f in plan_data.get("file_tree", []):
        if not isinstance(f, dict):
            continue
        path = f.get("path", "")
        # Skip entries that have content (LLM sometimes embeds file contents in tree)
        if "content" in f or not path:
            continue
        # Skip duplicates
        if path in seen_paths:
            continue
        seen_paths.add(path)
        clean_tree.append(f)
    
    # Build invariant mapping
    invariants_map = {}
    for f in clean_tree:
        invariants_map[f["path"]] = f.get("invariants", [])
    
    return ArchitecturePlan(
        project_name=plan_data.get("project_name", config.name),
        description=plan_data.get("description", config.description),
        file_tree=clean_tree,
        dependencies=plan_data.get("dependencies", []),
        architecture_decisions=plan_data.get("architecture_decisions", []),
        deployment_notes=plan_data.get("deployment_notes", []),
        applicable_invariants=invariants_map,
        raw_response=raw,
    )


def _extract_json_from_response(text: str) -> Optional[Dict]:
    """Extract JSON object from LLM response text."""
    # Strategy 1: Look for JSON code block
    import re
    patterns = [
        r'```json\s*(.*?)\s*```',
        r'```\s*(\{.*?\})\s*```',
        r'(\{\s*"project_name".*?\})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except:
                continue
    
    # Strategy 2: Try to find any JSON object in the text
    try:
        # Find the first { and last }
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end+1])
    except:
        pass
    
    return None


# --- PHASE 3: GENERATE ---

GENERATE_SYSTEM_PROMPT = """You are PEACOCK BUILDER. Generate production-ready code files as heredoc bash commands.

Output format for EACH file:
cat > path/to/file.ext << 'EOF'
<file content here>
EOF

Rules:
1. Use relative paths (e.g., app/main.py)
2. Quote EOF ('EOF')
3. Multiple files = multiple blocks
4. chmod +x for executables
5. NEVER nest triple backticks inside heredoc content
6. NEVER include markdown outside bash blocks
7. Complete runnable files — no TODOs, no placeholders
8. Include proper imports and error handling

Generate EXACTLY the requested files."""


def _truncate_context(context: str, max_chars: int = 2000) -> str:
    """Truncate context to stay within token limits."""
    if len(context) <= max_chars:
        return context
    return context[:max_chars] + "\n... [truncated for length]"


async def _generate_phase(
    config: ProjectConfig,
    architecture: ArchitecturePlan,
    memory_context: str,
    iteration: int = 0,
    fix_issues: Optional[List[ValidationIssue]] = None,
) -> GenerationBatch:
    """Run the GENERATE phase: create file contents."""
    
    # Group files by size for batching
    small_files = [f for f in architecture.file_tree if f.get("size_estimate") == "small"]
    medium_files = [f for f in architecture.file_tree if f.get("size_estimate") == "medium"]
    large_files = [f for f in architecture.file_tree if f.get("size_estimate") == "large"]
    unknown_files = [f for f in architecture.file_tree if f.get("size_estimate") not in ("small", "medium", "large")]
    
    all_files = small_files + medium_files + unknown_files + large_files
    
    # Batch files — use smaller batches to keep prompts under TPM limits
    batch_size = min(config.files_per_batch, 3)  # Cap at 3 for TPM safety
    batches = [all_files[i:i+batch_size] for i in range(0, len(all_files), batch_size)]
    
    all_generated: List[HeredocFile] = []
    total_tokens = 0
    total_cost = 0.0
    total_duration = 0
    
    # Truncate memory context to keep prompts small
    truncated_memory = _truncate_context(memory_context, max_chars=1500)
    truncated_decisions = architecture.architecture_decisions[:3]  # Only top 3 decisions
    
    for batch_idx, batch_files in enumerate(batches):
        # Build compact file specs
        file_specs = []
        for f in batch_files:
            file_specs.append(f"- {f['path']}: {f['purpose']}")
        
        fix_context = ""
        if fix_issues and iteration > 0:
            fix_lines = [f"- {i.file}: {i.message}" for i in fix_issues[:5]]  # Max 5 fixes
            fix_context = f"""Fix these issues:\n{chr(10).join(fix_lines)}\n"""
        
        prompt = f"""{GENERATE_SYSTEM_PROMPT}

Project: {architecture.project_name}
{architecture.description}

Decisions:
{chr(10).join(f"- {d}" for d in truncated_decisions)}

Context:
{truncated_memory}

Files (batch {batch_idx + 1}/{len(batches)}):
{chr(10).join(file_specs)}
{fix_context}
Generate now."""
        
        # Calculate safe max_tokens to avoid TPM limit errors
        safe_max = _get_safe_max_tokens(config.model, prompt, reserved_output=3000)
        
        result = await execute_strike(
            gateway=config.gateway,
            model_id=config.model,
            prompt=prompt,
            temperature=max(config.temperature - (iteration * 0.05), 0.1),
            max_tokens=safe_max,
        )
        
        raw = result.get("content", "")
        
        # Validate heredoc syntax before parsing
        is_valid, syntax_issues = validate_heredoc_syntax(raw)
        if not is_valid:
            # Try to fix or warn
            pass  # Parser will do its best
        
        # Parse heredocs
        parse_result = extract_heredocs(raw)
        
        if parse_result.errors:
            # Log but continue — might be partial success
            pass
        
        # Deduplicate: later batches override earlier ones for same path
        for f in parse_result.files:
            existing_idx = next((i for i, ef in enumerate(all_generated) if ef.path == f.path), None)
            if existing_idx is not None:
                all_generated[existing_idx] = f
            else:
                all_generated.append(f)
        
        usage = result.get("usage", {})
        total_tokens += usage.get("total_tokens", 0)
        total_cost += result.get("cost", 0.0)
        # Rough duration estimate
        total_duration += 1000  # Placeholder
    
    return GenerationBatch(
        files=all_generated,
        prompt_tokens=total_tokens,  # Simplified
        completion_tokens=total_tokens,
        duration_ms=total_duration,
        raw_response="",
    )


# --- PHASE 4: VALIDATE ---

async def _validate_phase(
    config: ProjectConfig,
    files: List[HeredocFile],
    architecture: ArchitecturePlan,
) -> List[ValidationResult]:
    """Run the VALIDATE phase: check files against rules and invariants."""
    
    results = await validate_project(
        files=files,
        project_type=config.project_type_hint,
        enable_memory_validation=config.enable_memory,
    )
    
    return results


# --- PHASE 5: PACKAGE ---

def _package_phase(
    config: ProjectConfig,
    architecture: ArchitecturePlan,
    files: List[HeredocFile],
    validation_results: List[ValidationResult],
) -> Dict[str, Any]:
    """Run the PACKAGE phase: assemble deploy script, README, manifest."""
    
    # Generate deploy script
    deploy_script = generate_deploy_script(files, architecture.project_name)
    
    # Generate README
    file_tree_str = generate_file_tree(files)
    validation_summary = format_validation_report(validation_results)
    
    readme = f"""# {architecture.project_name}

{architecture.description}

## File Structure

```
{file_tree_str}
```

## Dependencies

```
{chr(10).join(architecture.dependencies)}
```

## Architecture Decisions

{chr(10).join(f"- {d}" for d in architecture.architecture_decisions)}

## Deployment

```bash
# Quick start
bash deploy.sh
```

{chr(10).join(f"- {n}" for n in architecture.deployment_notes)}

## Validation Report

{validation_summary}

---
*Generated by Peacock Engine Project Generator*
"""
    
    # Build manifest
    manifest = {
        "project_name": architecture.project_name,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generator": "peacock-engine-v3",
        "model": config.model,
        "file_count": len(files),
        "files": [
            {
                "path": f.path,
                "hash": f.hash,
                "mode": f.mode,
                "executable": f.executable,
            }
            for f in files
        ],
        "dependencies": architecture.dependencies,
        "validation": {
            "total_errors": sum(r.error_count for r in validation_results),
            "total_warnings": sum(r.warning_count for r in validation_results),
            "passed": all(r.passed for r in validation_results),
        },
    }
    
    return {
        "deploy_script": deploy_script,
        "readme": readme,
        "manifest": manifest,
    }


# --- MAIN ORCHESTRATOR ---

async def generate_project(config: ProjectConfig) -> ProjectResult:
    """
    Run the complete project generation pipeline.
    
    This is the main entry point. It orchestrates all 5 phases:
    INGEST → ARCHITECT → GENERATE → VALIDATE → PACKAGE
    with iteration if validation fails.
    """
    result = ProjectResult(config=config, status="ingesting")
    start_time = time.time()
    
    try:
        # === PHASE 1: INGEST ===
        result.status = "ingesting"
        memory_result = await _ingest_memory(config)
        memory_context = memory_result.get("context", "")
        
        # === PHASE 2: ARCHITECT ===
        result.status = "architecting"
        architecture = await _architect_phase(config, memory_context)
        result.architecture = architecture
        
        # === PHASE 3-4: GENERATE + VALIDATE (with iteration) ===
        current_files: List[HeredocFile] = []
        current_validation: List[ValidationResult] = []
        
        for iteration in range(config.max_iterations):
            result.iterations = iteration + 1
            result.status = f"generating (iteration {iteration + 1})"
            
            # Determine what needs fixing
            fix_issues = None
            if iteration > 0 and current_validation:
                fix_issues = []
                for vr in current_validation:
                    for issue in vr.issues:
                        if issue.severity in ("error", "warning"):
                            fix_issues.append(issue)
            
            # Generate files
            batch = await _generate_phase(
                config=config,
                architecture=architecture,
                memory_context=memory_context,
                iteration=iteration,
                fix_issues=fix_issues,
            )
            
            current_files = batch.files
            result.total_tokens += batch.prompt_tokens + batch.completion_tokens
            
            # Validate
            result.status = f"validating (iteration {iteration + 1})"
            current_validation = await _validate_phase(config, current_files, architecture)
            result.validation_results = current_validation
            
            # Check if we need another iteration
            total_errors = sum(r.error_count for r in current_validation)
            if total_errors == 0:
                break  # All good!
            
            # If max iterations reached, we'll package what we have
        
        result.files = current_files
        
        # === PHASE 5: PACKAGE ===
        result.status = "packaging"
        package = _package_phase(config, architecture, current_files, current_validation)
        result.deploy_script = package["deploy_script"]
        result.readme = package["readme"]
        result.manifest = package["manifest"]
        
        result.status = "complete"
        result.total_duration_ms = int((time.time() - start_time) * 1000)
        
    except Exception as e:
        result.status = "failed"
        result.errors.append(str(e))
        import traceback
        result.errors.append(traceback.format_exc())
    
    return result


# --- UTILITIES ---

def project_result_to_json(result: ProjectResult) -> Dict[str, Any]:
    """Convert a ProjectResult to a JSON-serializable dict."""
    return {
        "status": result.status,
        "config": {
            "name": result.config.name,
            "description": result.config.description,
            "model": result.config.model,
            "gateway": result.config.gateway,
        },
        "architecture": {
            "project_name": result.architecture.project_name if result.architecture else None,
            "description": result.architecture.description if result.architecture else None,
            "file_tree": result.architecture.file_tree if result.architecture else [],
            "dependencies": result.architecture.dependencies if result.architecture else [],
            "architecture_decisions": result.architecture.architecture_decisions if result.architecture else [],
        } if result.architecture else None,
        "files": [
            {
                "path": f.path,
                "content": f.content,
                "mode": f.mode,
                "executable": f.executable,
                "hash": f.hash,
            }
            for f in result.files
        ],
        "deploy_script": result.deploy_script,
        "readme": result.readme,
        "manifest": result.manifest,
        "validation": {
            "results": [
                {
                    "file": r.file,
                    "passed": r.passed,
                    "errors": r.error_count,
                    "warnings": r.warning_count,
                    "issues": [
                        {
                            "severity": i.severity,
                            "rule": i.rule,
                            "message": i.message,
                            "suggestion": i.suggestion,
                        }
                        for i in r.issues
                    ],
                }
                for r in result.validation_results
            ],
            "report": format_validation_report(result.validation_results),
        },
        "metrics": {
            "total_tokens": result.total_tokens,
            "total_cost": result.total_cost,
            "total_duration_ms": result.total_duration_ms,
            "iterations": result.iterations,
        },
        "errors": result.errors,
    }
