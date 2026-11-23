"""
CODEBASE ANALYZER ENGINE
────────────────────────
Deep-dive directory ingestion for the Neural Link.

Phases:
  1. DISCOVERY   → Walk tree, detect languages, count lines
  2. DEPS        → Parse manifest files (requirements.txt, package.json, etc.)
  3. ENTRY       → Identify main / app / index / server entry points
  4. FILE_MAP    → Summarize every key file via LLM (map phase)
  5. SYNTHESIS   → Architecture doc + data-flow + design patterns (reduce phase)
  6. INVARIANTS  → Extract implicit rules / conventions
  7. INGEST      → Chunk & store in Peacock Unified codebase_vault

Uses map-reduce for large codebases to stay within TPM budget.
"""

import os
import json
import asyncio
import httpx
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict

# Peacock Unified endpoint
PEACOCK_UNIFIED_URL = os.getenv("PEACOCK_UNIFIED_URL", "http://localhost:8000")
COLLECTION_NAME = "codebase_vault"

# ── Language detection ───────────────────────────────────────────────

LANG_MAP = {
    ".py": "python", ".pyi": "python", ".pyw": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java", ".kt": "kotlin", ".scala": "scala",
    ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp", ".hpp": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".r": "r",
    ".sh": "bash", ".bash": "bash", ".zsh": "bash",
    ".ps1": "powershell",
    ".sql": "sql",
    ".html": "html", ".htm": "html",
    ".css": "css", ".scss": "css", ".sass": "css", ".less": "css",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
    ".md": "markdown", ".rst": "markdown",
    ".dockerfile": "docker", "dockerfile": "docker",
    ".tf": "terraform", ".hcl": "terraform",
    ".proto": "protobuf",
    ".graphql": "graphql", ".gql": "graphql",
}

# Files that reveal dependencies / project structure
MANIFEST_FILES = {
    "requirements.txt": "pip",
    "setup.py": "pip",
    "pyproject.toml": "pip",
    "Pipfile": "pip",
    "package.json": "npm",
    "package-lock.json": "npm",
    "yarn.lock": "npm",
    "pnpm-lock.yaml": "npm",
    "Cargo.toml": "cargo",
    "Cargo.lock": "cargo",
    "go.mod": "go",
    "go.sum": "go",
    "Gemfile": "ruby",
    "Gemfile.lock": "ruby",
    "composer.json": "php",
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "CMakeLists.txt": "cmake",
    "Makefile": "make",
    "Dockerfile": "docker",
    "docker-compose.yml": "docker",
    "docker-compose.yaml": "docker",
    ".github/workflows": "ci",
    "tsconfig.json": "typescript",
    "next.config.js": "nextjs",
    "next.config.mjs": "nextjs",
    "tailwind.config.js": "tailwind",
    "vite.config.js": "vite",
    "vite.config.ts": "vite",
    "webpack.config.js": "webpack",
    "astro.config.mjs": "astro",
    "svelte.config.js": "svelte",
}

# Common entry-point filenames
ENTRY_HINTS = [
    "main.py", "app.py", "server.py", "manage.py", "wsgi.py", "asgi.py",
    "index.js", "index.ts", "main.js", "main.ts", "server.js", "server.ts",
    "app.js", "app.ts", "server.go", "main.go", "cmd/",
    "main.rs", "lib.rs",
    "index.php", "public/index.php",
    "src/main/java", "Application.java", "Main.java",
    "src/main.rs", "src/lib.rs",
]

SKIP_DIRS = {
    ".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".tox", "dist", "build", ".egg-info", ".coverage",
    "htmlcov", ".next", ".nuxt", "out", "target", ".cargo", ".idea",
    ".vscode", ".vs", "bin", "obj", "vendor", "third_party", "third-party",
    ".gitignore", ".DS_Store", ".env", ".env.local",
}

SKIP_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".webm",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".lock", ".log", ".tmp", ".temp", ".swp", ".swo",
    ".class", ".jar", ".war", ".ear",
}

BINARY_EXTENSIONS = {
    ".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".mp3",
    ".mp4", ".wav", ".avi", ".mov", ".webm", ".pdf", ".zip",
    ".tar", ".gz", ".bz2", ".7z", ".rar", ".class", ".jar",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
}

# ── Data structures ──────────────────────────────────────────────────

@dataclass
class FileInfo:
    path: str
    rel_path: str
    size: int
    lines: int
    language: str
    is_entry_hint: bool = False
    is_manifest: bool = False
    manifest_type: str = ""

@dataclass
class CodebaseScan:
    scan_id: str
    source_path: str
    project_name: str
    started_at: str
    status: str = "pending"  # pending, discovering, analyzing, synthesizing, ingesting, completed, error
    progress_pct: float = 0.0
    files: List[FileInfo] = field(default_factory=list)
    languages: Dict[str, int] = field(default_factory=dict)
    total_files: int = 0
    total_lines: int = 0
    manifests: List[Dict] = field(default_factory=list)
    entry_points: List[str] = field(default_factory=list)
    file_summaries: List[Dict] = field(default_factory=list)
    architecture_doc: str = ""
    dependency_graph: str = ""
    invariant_doc: str = ""
    error: str = ""
    docs_ingested: int = 0


# ── Phase 1: Discovery ───────────────────────────────────────────────

def discover_codebase(root_path: str, scan: CodebaseScan) -> CodebaseScan:
    """Walk directory tree and collect file metadata."""
    root = Path(root_path).resolve()
    if not root.exists():
        raise ValueError(f"Path does not exist: {root_path}")
    
    scan.status = "discovering"
    scan.project_name = root.name or "unknown_project"
    
    for p in root.rglob("*"):
        # Skip hidden dirs and common noise
        rel = p.relative_to(root)
        parts = rel.parts
        if any(part.startswith(".") and part not in (".github", ".vscode") for part in parts):
            continue
        if any(part in SKIP_DIRS for part in parts):
            continue
        
        if p.is_file():
            ext = p.suffix.lower()
            if ext in SKIP_EXTENSIONS:
                continue
            
            # Skip binary files
            if ext in BINARY_EXTENSIONS or _is_binary(p):
                continue
            
            lang = LANG_MAP.get(ext, "unknown")
            lines = _count_lines(p)
            size = p.stat().st_size
            
            rel_str = str(rel).replace("\\", "/")
            is_manifest = p.name in MANIFEST_FILES or any(rel_str.startswith(k) for k in MANIFEST_FILES if "/" in k)
            manifest_type = MANIFEST_FILES.get(p.name, "")
            is_entry = any(hint in rel_str for hint in ENTRY_HINTS)
            
            fi = FileInfo(
                path=str(p),
                rel_path=rel_str,
                size=size,
                lines=lines,
                language=lang,
                is_entry_hint=is_entry,
                is_manifest=is_manifest,
                manifest_type=manifest_type,
            )
            scan.files.append(fi)
            scan.languages[lang] = scan.languages.get(lang, 0) + 1
            scan.total_lines += lines
    
    scan.total_files = len(scan.files)
    scan.entry_points = [f.rel_path for f in scan.files if f.is_entry_hint]
    scan.manifests = [
        {"file": f.rel_path, "type": f.manifest_type, "content": _safe_read(Path(f.path), 5000)}
        for f in scan.files if f.is_manifest
    ]
    scan.progress_pct = 15.0
    return scan


def _is_binary(path: Path, sample_size: int = 8192) -> bool:
    try:
        with open(path, "rb") as f:
            chunk = f.read(sample_size)
            if b"\x00" in chunk:
                return True
    except Exception:
        return True
    return False


def _count_lines(path: Path) -> int:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def _safe_read(path: Path, max_chars: int = 10000) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return text[:max_chars] + ("\n... [truncated]" if len(text) > max_chars else "")
    except Exception as e:
        return f"[read error: {e}]"


# ── Phase 2: Build context budget ────────────────────────────────────

def _build_tree_string(files: List[FileInfo], max_lines: int = 200) -> str:
    """Render a compact tree view of the codebase."""
    lines = []
    dirs = set()
    for f in sorted(files, key=lambda x: x.rel_path):
        parts = f.rel_path.split("/")
        for i in range(len(parts) - 1):
            prefix = "  " * i + "📁 " + parts[i]
            dirs.add(prefix)
    for d in sorted(dirs):
        lines.append(d)
    for f in sorted(files, key=lambda x: x.rel_path):
        depth = f.rel_path.count("/")
        icon = "📝" if f.language != "unknown" else "📄"
        lines.append("  " * depth + f"{icon} {f.rel_path} ({f.lines}L, {f.language})")
    
    tree = "\n".join(lines)
    if len(tree) > max_lines * 80:
        tree = tree[:max_lines * 80] + "\n... [tree truncated]"
    return tree


def _build_manifest_summary(manifests: List[Dict]) -> str:
    parts = []
    for m in manifests:
        parts.append(f"=== {m['file']} ({m['type']}) ===")
        parts.append(m['content'])
        parts.append("")
    return "\n".join(parts)


def _select_key_files(files: List[FileInfo], max_total_lines: int = 3000) -> List[FileInfo]:
    """Select the most informative files for LLM analysis."""
    scored = []
    for f in files:
        score = 0
        if f.is_entry_hint:
            score += 100
        if f.is_manifest:
            score += 80
        if f.language in ("python", "javascript", "typescript", "go", "rust", "java"):
            score += 30
        if f.lines > 500:
            score -= 20  # penalty for huge files
        if f.lines < 10:
            score -= 10
        scored.append((score, f))
    
    scored.sort(key=lambda x: (-x[0], -x[1].lines))
    selected = []
    total_lines = 0
    for _, f in scored:
        if total_lines + f.lines > max_total_lines:
            break
        selected.append(f)
        total_lines += f.lines
    return selected


# ── Phase 3: LLM Analysis (Map) ──────────────────────────────────────

async def _call_llm(prompt: str, model_id: str = "groq/llama-3.3-70b-versatile") -> str:
    """Fire a one-shot LLM call via Peacock Engine local chat API."""
    from app.config import MODEL_REGISTRY
    from app.core.groq_tool_engine import _groq_call_with_retry
    from openai import AsyncOpenAI
    
    # Use Groq pool directly for speed
    from app.core.key_manager import GroqPool
    asset = GroqPool.get_next()
    client = AsyncOpenAI(base_url="https://api.groq.com/openai/v1", api_key=asset.key)
    try:
        resp = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert software architect. Be concise but thorough."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4096,
        )
        return resp.choices[0].message.content or ""
    finally:
        await client.close()


async def analyze_file_batch(files: List[FileInfo], project_name: str) -> List[Dict]:
    """Analyze a batch of files and return structured summaries."""
    summaries = []
    for f in files:
        content = _safe_read(Path(f.path), 4000)
        prompt = f"""Analyze this source file from project "{project_name}".

File: {f.rel_path}
Language: {f.language}
Lines: {f.lines}

```
{content}
```

Provide a structured analysis in this exact format:

PURPOSE: (one sentence describing what this file does)
KEY_FUNCTIONS: (comma-separated list of important functions/classes/exports)
DEPENDENCIES: (external imports or internal files it depends on)
PATTERNS: (design patterns or architectural decisions visible here)
NOTES: (anything unusual, clever, or noteworthy)
"""
        try:
            result = await _call_llm(prompt)
        except Exception as e:
            result = f"ERROR: {e}"
        
        summaries.append({
            "file": f.rel_path,
            "language": f.language,
            "lines": f.lines,
            "analysis": result,
        })
    return summaries


# ── Phase 4: Synthesis (Reduce) ──────────────────────────────────────

async def synthesize_architecture(
    scan: CodebaseScan,
    file_summaries: List[Dict],
) -> Tuple[str, str, str]:
    """Synthesize file analyses into architecture + dependency + invariant docs."""
    
    tree = _build_tree_string(scan.files, max_lines=150)
    manifest_text = _build_manifest_summary(scan.manifests)
    
    # Build compact summary of all file analyses
    file_bulletins = []
    for s in file_summaries[:40]:  # cap at 40 files
        file_bulletins.append(
            f"- {s['file']} ({s['language']}, {s['lines']}L): "
            + s['analysis'].replace('\n', ' | ')[:300]
        )
    
    lang_distribution = ", ".join(f"{k}:{v}" for k, v in sorted(scan.languages.items(), key=lambda x: -x[1])[:8])
    
    prompt = f"""You are a principal software architect documenting a codebase.

PROJECT: {scan.project_name}
TOTAL_FILES: {scan.total_files}
TOTAL_LINES: {scan.total_lines}
LANGUAGES: {lang_distribution}
ENTRY_POINTS: {', '.join(scan.entry_points[:10])}

DIRECTORY_TREE:
{tree}

MANIFESTS:
{manifest_text[:3000]}

FILE_SUMMARIES:
{"\n".join(file_bulletins[:50])}

Produce THREE documents separated by exactly `---ARCH---`, `---DEPS---`, and `---INV---`:

1. ARCHITECTURE DOCUMENT (before first separator):
   - Overall architecture pattern (microservices, monolith, layered, event-driven, etc.)
   - Key modules and their responsibilities
   - Data flow through the system
   - External integrations
   - Deployment considerations
   Write in markdown with clear headers.

2. DEPENDENCY & DATA-FLOW DOCUMENT (between separators):
   - Map of how files/modules relate to each other
   - Internal dependency graph (which files import which)
   - External dependency categories (DB, cache, API clients, etc.)
   - Data lifecycle (request → validation → processing → response)

3. INVARIANTS & CONVENTIONS DOCUMENT (after last separator):
   - Implicit rules every developer must follow
   - Naming conventions
   - Error handling patterns
   - Testing conventions
   - Security considerations
   - Any anti-patterns to avoid
"""
    
    result = await _call_llm(prompt)
    
    # Parse the three sections
    arch = ""
    deps = ""
    inv = ""
    
    if "---ARCH---" in result and "---DEPS---" in result and "---INV---" in result:
        parts = result.split("---ARCH---", 1)[1]
        arch_parts = parts.split("---DEPS---", 1)
        arch = arch_parts[0].strip()
        rest = arch_parts[1]
        dep_parts = rest.split("---INV---", 1)
        deps = dep_parts[0].strip()
        inv = dep_parts[1].strip() if len(dep_parts) > 1 else ""
    else:
        # Fallback: just treat entire response as architecture
        arch = result
        deps = "Dependency analysis not separated."
        inv = "Invariants not separated."
    
    return arch, deps, inv


# ── Phase 5: Ingestion ───────────────────────────────────────────────

async def ingest_to_peacock(scan: CodebaseScan) -> int:
    """Store all analysis documents into Peacock Unified codebase_vault."""
    docs = []
    metas = []
    ids = []
    base_id = hashlib.sha256(f"{scan.source_path}:{scan.started_at}".encode()).hexdigest()[:16]
    
    # 1. Architecture overview
    docs.append(scan.architecture_doc)
    metas.append({
        "scan_id": scan.scan_id,
        "project_name": scan.project_name,
        "source_path": scan.source_path,
        "doc_type": "architecture_overview",
        "language": ",".join(scan.languages.keys()),
        "total_files": scan.total_files,
        "total_lines": scan.total_lines,
        "analyzed_at": scan.started_at,
        "entry_points": ",".join(scan.entry_points[:10]),
    })
    ids.append(f"{base_id}_arch")
    
    # 2. Dependency graph
    docs.append(scan.dependency_graph)
    metas.append({
        "scan_id": scan.scan_id,
        "project_name": scan.project_name,
        "source_path": scan.source_path,
        "doc_type": "dependency_graph",
        "analyzed_at": scan.started_at,
    })
    ids.append(f"{base_id}_deps")
    
    # 3. Invariants
    docs.append(scan.invariant_doc)
    metas.append({
        "scan_id": scan.scan_id,
        "project_name": scan.project_name,
        "source_path": scan.source_path,
        "doc_type": "invariants",
        "analyzed_at": scan.started_at,
    })
    ids.append(f"{base_id}_inv")
    
    # 4. File summaries (one doc per file, batched)
    for i, summary in enumerate(scan.file_summaries):
        doc_id = f"{base_id}_file_{i:04d}"
        content = f"""# {summary['file']}

Language: {summary['language']} | Lines: {summary['lines']}

## Analysis

{summary['analysis']}
"""
        docs.append(content)
        metas.append({
            "scan_id": scan.scan_id,
            "project_name": scan.project_name,
            "source_path": scan.source_path,
            "doc_type": "file_summary",
            "file_path": summary['file'],
            "language": summary['language'],
            "lines": summary['lines'],
            "analyzed_at": scan.started_at,
        })
        ids.append(doc_id)
        
        # Batch in chunks of 50 to avoid huge payloads
        if len(docs) >= 50:
            await _push_batch(ids, docs, metas)
            docs, metas, ids = [], [], []
    
    if docs:
        await _push_batch(ids, docs, metas)
    
    return len(scan.file_summaries) + 3


async def _push_batch(ids: List[str], docs: List[str], metas: List[Dict]):
    """Push a batch to Peacock Unified."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(
                f"{PEACOCK_UNIFIED_URL}/api/collections/{COLLECTION_NAME}/add",
                json={"ids": ids, "documents": docs, "metadatas": metas},
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"[INGEST ERROR] {e}")
            # Non-fatal — log and continue


# ── Orchestrator ─────────────────────────────────────────────────────

async def run_codebase_scan(
    source_path: str,
    scan_id: str,
    db_callback=None,  # callable(scan) to persist status
) -> CodebaseScan:
    """
    Full pipeline: discover → analyze → synthesize → ingest.
    Returns the completed scan object.
    """
    scan = CodebaseScan(
        scan_id=scan_id,
        source_path=source_path,
        project_name="",
        started_at=datetime.utcnow().isoformat(),
    )
    
    try:
        # Phase 1: Discovery
        scan = discover_codebase(source_path, scan)
        if db_callback:
            db_callback(scan)
        
        # Phase 2: File analysis (map)
        scan.status = "analyzing"
        key_files = _select_key_files(scan.files, max_total_lines=4000)
        scan.file_summaries = await analyze_file_batch(key_files, scan.project_name)
        scan.progress_pct = 55.0
        if db_callback:
            db_callback(scan)
        
        # Phase 3: Synthesis (reduce)
        scan.status = "synthesizing"
        arch, deps, inv = await synthesize_architecture(scan, scan.file_summaries)
        scan.architecture_doc = arch
        scan.dependency_graph = deps
        scan.invariant_doc = inv
        scan.progress_pct = 80.0
        if db_callback:
            db_callback(scan)
        
        # Phase 4: Ingestion
        scan.status = "ingesting"
        scan.docs_ingested = await ingest_to_peacock(scan)
        scan.progress_pct = 100.0
        scan.status = "completed"
        if db_callback:
            db_callback(scan)
        
    except Exception as e:
        scan.status = "error"
        scan.error = str(e)
        if db_callback:
            db_callback(scan)
    
    return scan


# ── Query helpers ────────────────────────────────────────────────────

async def query_codebase_vault(query: str, n: int = 5) -> Dict[str, Any]:
    """Query the codebase_vault collection."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                f"{PEACOCK_UNIFIED_URL}/api/search",
                params={"q": query, "collections": [COLLECTION_NAME], "n": n},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
