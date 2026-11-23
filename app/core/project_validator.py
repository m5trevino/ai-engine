"""
PROJECT VALIDATOR — Validate generated files against Peacock invariants.

Hybrid validation strategy:
1. LOCAL CHECKS: Fast regex/static analysis for common issues
2. MEMORY-AUGMENTED: Query relevant invariants and optionally send to LLM for review
3. CROSS-FILE: Check imports resolve, dependencies match requirements
"""

import re
import ast
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from app.core.memory_engine import query_memory
from app.core.heredoc_parser import HeredocFile


@dataclass
class ValidationIssue:
    severity: str  # "error", "warning", "info"
    file: str
    rule: str
    message: str
    suggestion: str = ""


@dataclass
class ValidationResult:
    file: str
    issues: List[ValidationIssue] = field(default_factory=list)
    passed: bool = True
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


# --- LOCAL VALIDATORS ---

PYTHON_IMPORT_PATTERNS = [
    (r'^import\s+(\w+)', 'import'),
    (r'^from\s+(\w+)', 'from'),
]

FILE_TYPE_RULES = {
    '.py': {
        'name': 'Python',
        'validators': [
            ('syntax', 'validate_python_syntax'),
            ('imports', 'check_import_consistency'),
            ('types', 'check_type_hints'),
        ]
    },
    '.js': {
        'name': 'JavaScript',
        'validators': [
            ('syntax', 'validate_js_basic'),
        ]
    },
    '.ts': {
        'name': 'TypeScript',
        'validators': [
            ('syntax', 'validate_ts_basic'),
        ]
    },
    '.json': {
        'name': 'JSON',
        'validators': [
            ('syntax', 'validate_json_syntax'),
        ]
    },
    '.yaml': {
        'name': 'YAML',
        'validators': [
            ('syntax', 'validate_yaml_basic'),
        ]
    },
    '.yml': {
        'name': 'YAML',
        'validators': [
            ('syntax', 'validate_yaml_basic'),
        ]
    },
    '.sh': {
        'name': 'Shell',
        'validators': [
            ('shebang', 'check_shebang'),
        ]
    },
    '.md': {
        'name': 'Markdown',
        'validators': []
    },
    '.html': {
        'name': 'HTML',
        'validators': [
            ('tags', 'check_html_tags'),
        ]
    },
    '.css': {
        'name': 'CSS',
        'validators': []
    },
    'Dockerfile': {
        'name': 'Dockerfile',
        'validators': [
            ('from', 'check_dockerfile_from'),
        ]
    },
    'requirements.txt': {
        'name': 'Python Requirements',
        'validators': [
            ('format', 'check_requirements_format'),
        ]
    },
}


def validate_python_syntax(content: str, path: str) -> List[ValidationIssue]:
    """Validate Python syntax using AST."""
    issues = []
    try:
        ast.parse(content)
    except SyntaxError as e:
        issues.append(ValidationIssue(
            severity="error",
            file=path,
            rule="python.syntax",
            message=f"Syntax error at line {e.lineno}: {e.msg}",
            suggestion="Check for mismatched brackets, indentation errors, or invalid syntax"
        ))
    return issues


def check_import_consistency(content: str, path: str, all_files: List[str]) -> List[ValidationIssue]:
    """Check that imports in Python files are available in requirements or project."""
    issues = []
    # Extract top-level imports
    imports = set()
    for line in content.split('\n'):
        match = re.match(r'^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)', line.strip())
        if match:
            imports.add(match.group(1))
    
    # Standard library modules (common ones) — skip these
    stdlib = {'os', 'sys', 'json', 're', 'time', 'datetime', 'typing', 'collections', 
              'pathlib', 'hashlib', 'base64', 'urllib', 'http', 'socket', 'threading',
              'asyncio', 'inspect', 'functools', 'itertools', 'math', 'random', 'string',
              'uuid', 'copy', 'pickle', 'csv', 'io', 'warnings', 'logging', 'enum',
              'dataclasses', 'abc', 'contextlib', 'types'}
    
    # Check if requirements.txt exists in project
    has_requirements = any(f.endswith('requirements.txt') for f in all_files)
    
    for imp in imports:
        if imp in stdlib:
            continue
        if imp.startswith(('app.', 'src.', 'core.', 'models.', 'routes.')):
            # Local import — check if module exists
            local_path = imp.replace('.', '/') + '.py'
            if not any(f.endswith(local_path) for f in all_files):
                issues.append(ValidationIssue(
                    severity="warning",
                    file=path,
                    rule="python.local_import",
                    message=f"Local import '{imp}' may not resolve to an existing module",
                    suggestion=f"Ensure {local_path} exists in the project"
                ))
        elif has_requirements:
            # Should be in requirements.txt — we'll do a soft warning
            pass
    
    return issues


def check_type_hints(content: str, path: str) -> List[ValidationIssue]:
    """Check if Python file has type hints on function definitions."""
    issues = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check for return annotation
                has_return = node.returns is not None
                # Check for parameter annotations
                has_param_types = any(arg.annotation for arg in node.args.args if arg.arg != 'self')
                
                if node.args.args and len(node.args.args) > 1 and not has_param_types:
                    # Has parameters (excluding self) but no type hints
                    if not any(decorator.attr == 'overload' if isinstance(decorator, ast.Attribute) else False 
                               for decorator in node.decorator_list):
                        issues.append(ValidationIssue(
                            severity="info",
                            file=path,
                            rule="python.type_hints",
                            message=f"Function '{node.name}' lacks type hints",
                            suggestion="Add parameter and return type annotations for better code quality"
                        ))
    except:
        pass
    return issues


def validate_json_syntax(content: str, path: str) -> List[ValidationIssue]:
    """Validate JSON syntax."""
    issues = []
    import json
    try:
        json.loads(content)
    except json.JSONDecodeError as e:
        issues.append(ValidationIssue(
            severity="error",
            file=path,
            rule="json.syntax",
            message=f"Invalid JSON: {e.msg} at line {e.lineno}",
            suggestion="Fix JSON syntax — check for trailing commas or mismatched braces"
        ))
    return issues


def validate_yaml_basic(content: str, path: str) -> List[ValidationIssue]:
    """Basic YAML validation."""
    issues = []
    try:
        import yaml
        yaml.safe_load(content)
    except Exception as e:
        issues.append(ValidationIssue(
            severity="error",
            file=path,
            rule="yaml.syntax",
            message=f"Invalid YAML: {str(e)[:100]}",
            suggestion="Fix indentation and YAML syntax"
        ))
    return issues


def check_shebang(content: str, path: str) -> List[ValidationIssue]:
    """Check shell scripts start with shebang."""
    issues = []
    if not content.startswith('#!'):
        issues.append(ValidationIssue(
            severity="warning",
            file=path,
            rule="shell.shebang",
            message="Shell script missing shebang line",
            suggestion="Add '#!/bin/bash' or '#!/bin/sh' as the first line"
        ))
    return issues


def check_html_tags(content: str, path: str) -> List[ValidationIssue]:
    """Basic HTML tag balance check."""
    issues = []
    # Very basic: count opening and closing tags for common tags
    for tag in ['html', 'body', 'div', 'head', 'script']:
        opens = len(re.findall(rf'<{tag}[\s>]', content, re.IGNORECASE))
        closes = len(re.findall(rf'</{tag}>', content, re.IGNORECASE))
        if opens != closes and opens > 0:
            issues.append(ValidationIssue(
                severity="warning",
                file=path,
                rule="html.tags",
                message=f"Tag '<{tag}>' appears {opens} times but closes {closes} times",
                suggestion=f"Ensure all <{tag}> tags are properly closed"
            ))
    return issues


def check_dockerfile_from(content: str, path: str) -> List[ValidationIssue]:
    """Check Dockerfile has FROM instruction."""
    issues = []
    if not re.search(r'^FROM\s+', content, re.MULTILINE | re.IGNORECASE):
        issues.append(ValidationIssue(
            severity="error",
            file=path,
            rule="dockerfile.from",
            message="Dockerfile missing FROM instruction",
            suggestion="Add a base image, e.g., 'FROM python:3.11-slim'"
        ))
    return issues


def check_requirements_format(content: str, path: str) -> List[ValidationIssue]:
    """Validate requirements.txt format."""
    issues = []
    for i, line in enumerate(content.split('\n'), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        # Very loose check — just warn on obvious issues
        if line.startswith('-') and not line.startswith(('-r', '-e', '-i')):
            issues.append(ValidationIssue(
                severity="warning",
                file=path,
                rule="requirements.format",
                message=f"Line {i}: Unexpected option '{line}'",
                suggestion="Use standard pip requirement format: package==version"
            ))
    return issues


def validate_js_basic(content: str, path: str) -> List[ValidationIssue]:
    """Basic JavaScript validation."""
    issues = []
    # Check for obvious issues
    if content.count('{') != content.count('}'):
        issues.append(ValidationIssue(
            severity="warning",
            file=path,
            rule="js.braces",
            message="Brace count mismatch",
            suggestion="Check for missing or extra braces"
        ))
    if content.count('(') != content.count(')'):
        issues.append(ValidationIssue(
            severity="warning",
            file=path,
            rule="js.parens",
            message="Parenthesis count mismatch",
            suggestion="Check for missing or extra parentheses"
        ))
    return issues


def validate_ts_basic(content: str, path: str) -> List[ValidationIssue]:
    """Basic TypeScript validation (same as JS + type check hints)."""
    issues = validate_js_basic(content, path)
    # Check for 'any' overuse
    any_count = content.count(': any')
    if any_count > 5:
        issues.append(ValidationIssue(
            severity="info",
            file=path,
            rule="ts.any",
            message=f"Uses 'any' type {any_count} times",
            suggestion="Replace 'any' with specific types or interfaces"
        ))
    return issues


# --- MAIN VALIDATION ORCHESTRATOR ---

async def validate_project(
    files: List[HeredocFile],
    project_type: Optional[str] = None,
    enable_memory_validation: bool = True,
) -> List[ValidationResult]:
    """
    Validate a complete project against local rules and memory invariants.
    
    Args:
        files: List of HeredocFile objects
        project_type: Optional hint (e.g., "fastapi", "react", "cli")
        enable_memory_validation: Whether to query memory for additional invariants
    
    Returns:
        List of ValidationResult, one per file
    """
    results: List[ValidationResult] = []
    all_paths = [f.path for f in files]
    
    # Build file lookup
    file_map = {f.path: f for f in files}
    
    for f in files:
        result = ValidationResult(file=f.path)
        
        # Determine file type
        suffix = Path(f.path).suffix.lower()
        basename = Path(f.path).name
        
        # Get validators for this file type
        type_info = FILE_TYPE_RULES.get(suffix) or FILE_TYPE_RULES.get(basename)
        
        if type_info:
            for rule_name, validator_name in type_info['validators']:
                validator = globals().get(validator_name)
                if validator:
                    if validator_name in ('check_import_consistency',):
                        issues = validator(f.content, f.path, all_paths)
                    else:
                        issues = validator(f.content, f.path)
                    result.issues.extend(issues)
        
        # Memory-augmented validation (if enabled)
        if enable_memory_validation and project_type:
            mem_issues = await _validate_against_memory(f, project_type)
            result.issues.extend(mem_issues)
        
        # Determine pass/fail
        result.passed = result.error_count == 0
        results.append(result)
    
    # Cross-file validation: requirements.txt consistency
    req_file = next((f for f in files if f.path.endswith('requirements.txt')), None)
    if req_file:
        req_packages = set()
        for line in req_file.content.split('\n'):
            line = line.strip().split('#')[0].strip()
            if line and not line.startswith('-'):
                pkg = line.split('==')[0].split('>=')[0].split('<=')[0].strip()
                if pkg:
                    req_packages.add(pkg.lower())
        
        for f in files:
            if f.path.endswith('.py'):
                imports = set()
                for line in f.content.split('\n'):
                    match = re.match(r'^(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)', line.strip())
                    if match:
                        imports.add(match.group(1).lower())
                
                for imp in imports:
                    if imp not in req_packages and imp not in {'os', 'sys', 'json', 're', 'time'}:
                        # Find the result for this file
                        for r in results:
                            if r.file == f.path:
                                r.issues.append(ValidationIssue(
                                    severity="info",
                                    file=f.path,
                                    rule="deps.missing",
                                    message=f"Import '{imp}' not found in requirements.txt",
                                    suggestion=f"Add '{imp}' to requirements.txt if it's an external package"
                                ))
    
    return results


async def _validate_against_memory(file: HeredocFile, project_type: str) -> List[ValidationIssue]:
    """Query memory for invariants relevant to this file and project type."""
    issues = []
    
    # Build a query for relevant invariants
    query = f"{project_type} {Path(file.path).suffix} {Path(file.path).name} best practices"
    
    try:
        mem_result = await query_memory(
            query=query,
            collections=["app_invariants", "agent_invariants", "tech_vault"],
            n=3,
            timeout=5.0,
        )
        
        if mem_result.get("status") == "ok" and mem_result.get("total_hits", 0) > 0:
            # For now, we just note that invariants were found
            # In a full implementation, we'd parse the invariants and check compliance
            context = mem_result.get("context", "")
            
            # Simple keyword-based checks from memory context
            if "type hint" in context.lower() and file.path.endswith('.py'):
                if "-> " not in file.content and "def " in file.content:
                    issues.append(ValidationIssue(
                        severity="info",
                        file=file.path,
                        rule="memory.type_hints",
                        message="Memory invariant suggests type hints, but few found",
                        suggestion="Add type annotations per project invariants"
                    ))
            
            if "auth" in context.lower() and file.path.endswith('.py'):
                if 'auth' not in file.content.lower() and 'login' not in file.content.lower():
                    issues.append(ValidationIssue(
                        severity="info",
                        file=file.path,
                        rule="memory.auth",
                        message="Memory invariant mentions auth — verify this file doesn't need it",
                        suggestion="Review auth requirements for this module"
                    ))
    except Exception:
        # Memory validation is best-effort
        pass
    
    return issues


def format_validation_report(results: List[ValidationResult]) -> str:
    """Format validation results as a markdown report."""
    lines = ["# Project Validation Report", ""]
    
    total_errors = sum(r.error_count for r in results)
    total_warnings = sum(r.warning_count for r in results)
    
    lines.append(f"**Summary:** {len(results)} files | {total_errors} errors | {total_warnings} warnings")
    lines.append("")
    
    for r in results:
        status = "✅" if r.passed else "❌"
        lines.append(f"{status} **{r.file}** — {r.error_count} errors, {r.warning_count} warnings")
        for issue in r.issues:
            icon = {"error": "🔴", "warning": "🟡", "info": "🔵"}.get(issue.severity, "⚪")
            lines.append(f"  {icon} `{issue.rule}`: {issue.message}")
            if issue.suggestion:
                lines.append(f"     💡 {issue.suggestion}")
        lines.append("")
    
    return "\n".join(lines)
