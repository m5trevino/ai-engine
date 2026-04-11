"""
This script includes tokenizer regex logic ported from:
https://github.com/smartprocure/gemini-token-estimator

Copyright (c) GovSpend

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

import os
import re
import sys
import argparse
import subprocess
import tempfile
import shutil
import fnmatch
from urllib.parse import urlparse

# -----------------------------------------------------------------------------
# 1. Tokenizer Logic
# -----------------------------------------------------------------------------

cons = "bcdfghjklmnpqrstvwxzßçñ"
vowels = "aeiouyàáâäèéêëìíîïòóôöùúûüýÿæœ"
cons_upper = "BCDFGHJKLMNPQRSTVWXZÇÑ"
vowels_upper = "AEIOUYÀÁÂÄÈÉÊËÌÍÎÏÒÓÔÖÙÚÛÜÝŸÆŒ"

lowercase_word = f"[ ]?(?:[{cons}]{{0,3}}[{vowels}]{{1,3}}[{cons}]{{0,3}}){{1,3}}"
uppercase_word = f"[ ]?(?:[{cons_upper}]{{0,3}}[{vowels_upper}]{{1,3}}[{cons_upper}]{{0,3}}){{1,3}}"
titlecase_word = f"[ ]?[A-ZÀÁÂÄÈÉÊËÌÍÎÏÒÓÔÖÙÚÛÜÝŸÆŒÇÑ][a-zàáâäèéêëìíîïòóôöùúûüýÿæœßçñ]{{1,8}}"
common_abbreviations = r"pdf|png|http(?:s)?|rfp|www|PDF|PNG|HTTP|HTTP(?:S)?|RFP|WWW"
non_latin_word = r"[ ]?[^\u0000-\u007F\u00A0-\u00FF\u0100-\u017F\ue000-\uf8ff]{1,5}"

regex_patterns_list = [
    r"\d", r"\n+", r"\r+", r"\t+", r"\x0b+", r"\f+", r"[\ue000-\uf8ff]",
    common_abbreviations, lowercase_word, titlecase_word, uppercase_word,
    f"[{cons}]{{1,2}}", f"[{cons_upper}]{{1,2}}", non_latin_word,
    r"\(\)", r"\[\]", r"\{\}", r"([.=#_-])\1{1,15}",
    r"[ ]?[!@#$%^&*()_+\-=\[\]{}\\|;:'\",.<>/?`~]{1,3}", r"[ ]+", r"."
]

COMBINED_PATTERN = re.compile("|".join(regex_patterns_list))

def tokenize(text: str) -> list[str]:
    if not text: return []
    return [m.group(0) for m in COMBINED_PATTERN.finditer(text)]

def get_token_count(text: str) -> int:
    if not text: return 0
    return sum(1 for _ in COMBINED_PATTERN.finditer(text))

# -----------------------------------------------------------------------------
# 2. File System Traversal with .gitignore/.gtcignore support
# -----------------------------------------------------------------------------

ALWAYS_IGNORE_DIRS = {
    '.git', 'node_modules', '__pycache__', '.idea', '.vscode', 'dist', 'build',
    'venv', 'env', '.venv', 'coverage', '.next', '.ds_store', '.mypy_cache',
    '.pytest_cache', '.tox', 'htmlcov', 'site-packages'
}

ALWAYS_IGNORE_FILES = {
    'package-lock.json', 'yarn.lock', '.DS_Store', 'poetry.lock', 'Pipfile.lock'
}

DEFAULT_IGNORE_PATTERNS = [
    '*.png', '*.jpg', '*.jpeg', '*.gif', '*.ico', '*.svg', '*.pdf', '*.zip',
    '*.tar', '*.gz', '*.pyc', '*.exe', '*.dll', '*.so', '*.dylib', '*.lock',
    '*.class', '*.bin', '*.woff', '*.woff2', '*.ttf', '*.eot',
    '*.egg-info', '*.egg'
]

class Node:
    def __init__(self, name, path, is_dir):
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.children = []
        self.tokens = 0
        self.content = None
        self.error = None

    def add_child(self, node):
        self.children.append(node)
        self.children.sort(key=lambda x: (not x.is_dir, x.name.lower()))

def parse_ignore_pattern(raw_pattern, allow_comments=True, path_based="auto"):
    pattern = raw_pattern.strip()
    if not pattern:
        return None
    if allow_comments and pattern.startswith('#'):
        return None

    dir_only = pattern.endswith('/')
    if dir_only:
        pattern = pattern[:-1].strip()
    if not pattern:
        return None

    if pattern.startswith('./'):
        pattern = pattern[2:]
    if pattern.startswith('/'):
        pattern = pattern[1:]
    if os.sep != '/':
        pattern = pattern.replace(os.sep, '/')

    if path_based == "auto":
        path_based = '/' in pattern
    else:
        path_based = bool(path_based)

    return (pattern, dir_only, path_based)

def load_ignore_patterns(path, filename, path_based):
    """
    Load ignore patterns from the specified file in a directory.
    Simple implementation: treats lines as glob patterns.
    """
    ignore_path = os.path.join(path, filename)
    patterns = []
    if os.path.exists(ignore_path):
        try:
            with open(ignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    parsed = parse_ignore_pattern(line, allow_comments=True, path_based=path_based)
                    if parsed:
                        patterns.append(parsed)
        except Exception:
            pass
    return patterns

def load_cli_patterns(patterns):
    parsed_patterns = []
    for pattern in patterns or []:
        parsed = parse_ignore_pattern(pattern, allow_comments=False, path_based="auto")
        if parsed:
            parsed_patterns.append(parsed)
    return parsed_patterns

def normalize_rel_path(path, root_path):
    try:
        rel_path = os.path.relpath(path, root_path)
    except ValueError:
        rel_path = path
    return rel_path.replace(os.sep, '/')

def matches_patterns(name, rel_path, is_dir, patterns):
    for pattern, dir_only, path_based in patterns:
        if dir_only and not is_dir:
            continue
        target = rel_path if path_based else name
        if fnmatch.fnmatch(target, pattern):
            return True
    return False

def is_ignored(name, rel_path, is_dir, active_patterns, gtc_patterns, cli_patterns):
    """
    Check if a file/dir name matches any of the ignore criteria.
    """
    # 1. Fixed Lists
    if is_dir and name in ALWAYS_IGNORE_DIRS:
        return True
    if not is_dir and name in ALWAYS_IGNORE_FILES:
        return True

    # 2. Pattern Matching (Extensions & .gitignore)
    # fnmatch is not fully gitignore compliant but covers most cases
    if matches_patterns(name, rel_path, is_dir, active_patterns):
        return True
    if matches_patterns(name, rel_path, is_dir, gtc_patterns):
        return True
    if matches_patterns(name, rel_path, is_dir, cli_patterns):
        return True
    return False

def scan_directory(path, root_path, parent_patterns=None, gtc_patterns=None, cli_patterns=None):
    if parent_patterns is None:
        parent_patterns = []
        for pattern in DEFAULT_IGNORE_PATTERNS:
            parsed = parse_ignore_pattern(pattern, allow_comments=False, path_based=False)
            if parsed:
                parent_patterns.append(parsed)

    if gtc_patterns is None:
        gtc_patterns = []
    if cli_patterns is None:
        cli_patterns = []

    # Load .gitignore in current directory and add to patterns
    current_patterns = parent_patterns.copy()
    current_patterns.extend(load_ignore_patterns(path, '.gitignore', path_based=False))

    name = os.path.basename(path) or path
    node = Node(name, path, is_dir=True)

    try:
        entries = sorted(os.listdir(path))
    except PermissionError:
        node.error = "Permission Denied"
        return node
    except FileNotFoundError:
        node.error = "Not Found"
        return node

    for entry in entries:
        full_path = os.path.join(path, entry)
        is_entry_dir = os.path.isdir(full_path)

        # Check ignore rules
        rel_path = normalize_rel_path(full_path, root_path)

        if is_ignored(entry, rel_path, is_entry_dir, current_patterns, gtc_patterns, cli_patterns):
            continue

        if is_entry_dir:
            # Recurse with current patterns
            child_node = scan_directory(full_path, root_path, current_patterns, gtc_patterns, cli_patterns)
            node.add_child(child_node)
            node.tokens += child_node.tokens
        elif os.path.isfile(full_path):
            child_node = Node(entry, full_path, is_dir=False)
            try:
                with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if '\0' in content:
                         child_node.tokens = 0
                    else:
                        child_node.tokens = get_token_count(content)
                        child_node.content = content
            except Exception as e:
                child_node.error = str(e)

            node.add_child(child_node)
            node.tokens += child_node.tokens

    return node

# -----------------------------------------------------------------------------
# 3. Output Formatting
# -----------------------------------------------------------------------------

def print_tree(node, prefix="", is_last=True, is_root=True):
    if is_root:
        connector = ""
    else:
        connector = "└── " if is_last else "├── "

    token_display = f" ({node.tokens} tokens)"
    name_display = node.name + "/" if node.is_dir else node.name

    if not is_root:
        print(f"{prefix}{connector}{name_display}{token_display}")

    if is_root:
        child_prefix = ""
    else:
        child_prefix = prefix + ("    " if is_last else "│   ")

    count = len(node.children)
    for i, child in enumerate(node.children):
        is_last_child = (i == count - 1)
        print_tree(child, child_prefix, is_last_child, is_root=False)

def print_all_files_content(node, project_root_abs):
    if not node.is_dir and node.content is not None:
        try:
            rel_path = os.path.relpath(node.path, project_root_abs)
        except ValueError:
            rel_path = node.path

        display_path = "/" + rel_path if not rel_path.startswith(os.sep) else rel_path
        display_path = display_path.replace(os.sep, '/')

        print("-" * 80)
        print(f"{display_path}:")
        print("-" * 80)
        print(node.content)
        print("")

    if node.is_dir:
        for child in node.children:
            print_all_files_content(child, project_root_abs)

# -----------------------------------------------------------------------------
# 4. GitHub & Git Context Handling
# -----------------------------------------------------------------------------

def is_github_url(url):
    return url.startswith("http://") or url.startswith("https://") or url.startswith("git@")

def parse_github_url(url):
    if not is_github_url(url):
        return os.path.abspath(url), None

    url = url.rstrip('/')
    match = re.match(r'(https://github\.com/[^/]+/[^/]+)(?:/tree/(.+))?', url)
    if match:
        base_url = match.group(1) + ".git"
        ref = match.group(2)
        return base_url, ref
    return url, None

class GitContext:
    def __init__(self, url, branch=None, commit=None, date=None, first=False):
        self.original_url = url
        self.temp_dir = tempfile.mkdtemp(prefix="tc_gh_")
        self.base_url, self.url_ref = parse_github_url(url)

        self.target_branch = branch
        self.target_commit = commit
        self.target_date = date
        self.target_first = first

    def _run_git(self, args, cwd=None, capture_output=False):
        cwd = cwd or self.temp_dir
        if capture_output:
            return subprocess.check_output(args, cwd=cwd, text=True).strip()
        else:
            subprocess.run(
                args,
                cwd=cwd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )

    def _detect_default_branch(self):
        """
        Attempts to find the default branch (e.g., main, master, develop)
        by querying the remote's HEAD reference.
        """
        try:
            # symbolic-ref returns something like "refs/remotes/origin/main"
            ref = self._run_git(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                capture_output=True
            )
            if ref:
                return ref.strip().split('/')[-1]

        except subprocess.CalledProcessError:
            pass
        return None

    def __enter__(self):
        print(f"Cloning {self.base_url} to temporary directory...")
        try:
            self._run_git(["git", "clone", "--filter=blob:none", self.base_url, self.temp_dir], cwd=os.getcwd())

            ref_to_checkout = self.target_branch if self.target_branch else self.url_ref

            if ref_to_checkout:
                print(f"Switching to branch/ref: {ref_to_checkout}")
                self._run_git(["git", "checkout", ref_to_checkout])
            else:
                default_branch = self._detect_default_branch()
                if default_branch:
                    print(f"Detected default branch: {default_branch}")
                    self._run_git(["git", "checkout", default_branch])
                else:
                    pass

            final_commit = None

            if self.target_commit:
                print(f"Targeting specific commit: {self.target_commit}")
                final_commit = self.target_commit

            elif self.target_first:
                print("Finding initial commit...")
                try:
                    roots = self._run_git(
                        ["git", "rev-list", "--max-parents=0", "HEAD"],
                        capture_output=True
                    )
                    if roots:
                        first_commit_hash = roots.split()[-1]
                        print(f"Found initial commit: {first_commit_hash}")
                        final_commit = first_commit_hash
                    else:
                        print("Warning: Could not determine initial commit.")
                except subprocess.CalledProcessError:
                    print("Error finding initial commit.")

            elif self.target_date:
                print(f"Finding commit closest to date: {self.target_date}")
                try:
                    commit_hash = self._run_git(
                        ["git", "rev-list", "-n", "1", f"--before={self.target_date}", "HEAD"],
                        capture_output=True
                    )
                    if not commit_hash:
                        print(f"Warning: No commit found before {self.target_date}. Keeping current HEAD.")
                    else:
                        print(f"Found commit {commit_hash} for date {self.target_date}")
                        final_commit = commit_hash
                except subprocess.CalledProcessError:
                    print(f"Error finding commit for date: {self.target_date}")

            if final_commit:
                self._run_git(["git", "checkout", final_commit])

            return self.temp_dir

        except subprocess.CalledProcessError as e:
            print(f"Error during git operation: {e}")
            if e.stderr:
                print(f"Git Error: {e.stderr.decode().strip() if isinstance(e.stderr, bytes) else e.stderr}")
            self.cleanup()
            sys.exit(1)
        except Exception as e:
            print(f"Unexpected error: {e}")
            self.cleanup()
            sys.exit(1)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

# -----------------------------------------------------------------------------
# Main & Analysis Logic
# -----------------------------------------------------------------------------

def run_analysis(root_path, source_name, args):
    root_abs = os.path.abspath(root_path)
    gtc_patterns = load_ignore_patterns(root_abs, '.gtcignore', path_based="auto")
    cli_patterns = load_cli_patterns(args.exclude)

    if args.dir:
        target_subdirs = args.dir
    else:
        target_subdirs = ["."]

    print(f"Source       : {source_name}")
    print(f"Working Path : {root_abs}")
    print("-" * 60)

    grand_total_tokens = 0
    scanned_nodes = []

    for subdir in target_subdirs:
        if subdir == ".":
            scan_path_abs = root_abs
            display_name = ""
        else:
            scan_path_abs = os.path.join(root_abs, subdir)
            display_name = f"{subdir}/"

        if not os.path.exists(scan_path_abs):
            print(f"Warning: Directory '{subdir}' not found. Skipping.")
            continue

        # Start scanning with default patterns
        node = scan_directory(scan_path_abs, root_abs, None, gtc_patterns, cli_patterns)
        scanned_nodes.append(node)
        grand_total_tokens += node.tokens

        if display_name:
            print(f"{display_name} ({node.tokens} tokens)")

        print_tree(node, is_root=True)
        if len(target_subdirs) > 1:
            print("")

    print("-" * 60)
    print(f"Grand Total Tokens: {grand_total_tokens}")
    print("-" * 60)

    if args.content:
        print("\n")
        for node in scanned_nodes:
            print_all_files_content(node, root_abs)

def main():
    examples = """
Examples:
  (Assuming command name is 'gtc')

  # 1. Local Directory
  gtc                       # Scan current directory
  gtc . -d src -d lib -c    # Scan specific dirs with content
  gtc . -e "*.test.ts" -e "__snapshots__"  # Exclude patterns (CLI)

  # 2. GitHub Repository
  gtc https://github.com/user/repo
  gtc https://github.com/user/repo -b develop

  # 3. Time Travel (Git History)
  gtc . --date 2023-01-01   # Checkout state at specific date
  gtc . --commit 5f3a1b     # Checkout specific commit
  gtc . --first             # Checkout initial commit
"""
    parser = argparse.ArgumentParser(
        prog='gtc',
        description="Estimate tokens for Gemini and display tree.",
        epilog=examples,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("target", nargs="?", default=".", help="Local path or GitHub URL")
    parser.add_argument("-d", "--dir", action="append", help="Specific subdirectory to analyze", default=[])
    parser.add_argument("-c", "--content", action="store_true", help="Display file contents")
    parser.add_argument("-e", "--exclude", action="append", help="Exclude patterns (glob). Can be used multiple times.", default=[])
    parser.add_argument("-b", "--branch", help="Git branch to checkout (default: auto-detected from remote)")
    parser.add_argument("--commit", help="Git commit hash to checkout (defaults to latest)")
    parser.add_argument("--date", help="Checkout the latest commit before this date (format: YYYY-MM-DD)")
    parser.add_argument("--first", action="store_true", help="Checkout the first (initial) commit of the repo")
    from . import __version__
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')

    args = parser.parse_args()

    target_is_url = is_github_url(args.target)
    use_git_options = any([args.branch, args.commit, args.date, args.first])

    if target_is_url or use_git_options:
        if not target_is_url and use_git_options:
            if not os.path.exists(os.path.join(args.target, '.git')):
                print(f"Error: '{args.target}' is not a valid Git repository.")
                sys.exit(1)

        ctx = GitContext(
            args.target,
            branch=args.branch,
            commit=args.commit,
            date=args.date,
            first=args.first
        )
        with ctx as temp_root:
            run_analysis(temp_root, args.target, args)

    else:
        if not os.path.exists(args.target):
            print(f"Error: Path '{args.target}' does not exist.")
            sys.exit(1)
        run_analysis(args.target, args.target, args)

if __name__ == "__main__":
    main()
