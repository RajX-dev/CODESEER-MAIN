# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

"""
Django Git History Miner — Phase 1 of the LLM Evaluation Experiment.

This script scans the Django repository's git history to find commits that:
  1. Changed or renamed a function/method signature (detected via diff heuristics)
  2. Touched at least 4 Python files (indicating a cross-cutting refactor)

The output is a JSON file listing candidate commits with metadata, suitable
for use as ground-truth tasks in the LLM hallucination evaluation.

Usage:
    # First, clone Django somewhere (if not already present):
    git clone https://github.com/django/django.git /path/to/django

    # Then run:
    python scripts/mine_django_refactors.py --repo /path/to/django --min-files 4 --output refactor_tasks.json
"""

import argparse
import json
import os
import re
import subprocess
import sys

# Reconfigure stdout to use utf-8 for Windows emoji support
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def run_git(repo_dir: str, args: list[str]) -> str:
    """Run a git command and return stdout."""
    result = subprocess.run(
        ["git", "-C", repo_dir] + args,
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout


def get_commit_list(repo_dir: str, max_commits: int = 5000) -> list[str]:
    """Get recent commit hashes."""
    out = run_git(repo_dir, [
        "log", "--format=%H", f"-n{max_commits}", "--no-merges",
    ])
    return [line.strip() for line in out.strip().split("\n") if line.strip()]


def get_commit_info(repo_dir: str, sha: str) -> dict:
    """Get commit metadata."""
    out = run_git(repo_dir, [
        "log", "-1", "--format=%H%n%an%n%s%n%aI", sha,
    ])
    lines = out.strip().split("\n")
    if len(lines) < 4:
        return {}
    return {
        "sha": lines[0],
        "author": lines[1],
        "subject": lines[2],
        "date": lines[3],
    }


def get_changed_files(repo_dir: str, sha: str) -> list[str]:
    """Get list of Python files changed in a commit."""
    out = run_git(repo_dir, [
        "diff-tree", "--no-commit-id", "-r", "--name-only", sha,
    ])
    files = [f.strip() for f in out.strip().split("\n") if f.strip()]
    return [f for f in files if f.endswith(".py")]


# Heuristic patterns for detecting function signature changes in diffs
FUNC_DEF_RE = re.compile(r"^[-+]\s*def\s+(\w+)\s*\(")
CLASS_DEF_RE = re.compile(r"^[-+]\s*class\s+(\w+)")


def diff_has_signature_change(repo_dir: str, sha: str) -> tuple[bool, list[str]]:
    """
    Check if a commit's diff contains a function/method rename or signature change.
    Returns (has_change, list_of_affected_function_names).
    """
    out = run_git(repo_dir, [
        "diff", f"{sha}~1", sha, "--", "*.py",
    ])

    removed_funcs = set()
    added_funcs = set()
    changed_funcs = []

    for line in out.split("\n"):
        m = FUNC_DEF_RE.match(line)
        if m:
            func_name = m.group(1)
            if line.startswith("-"):
                removed_funcs.add(func_name)
            elif line.startswith("+"):
                added_funcs.add(func_name)

    # A signature change looks like a function def that appears in both
    # removed and added lines (same name, different params),
    # OR a function that only appears in removed (rename/deletion)
    changed_funcs = list(removed_funcs & added_funcs)  # Same name, modified sig
    renamed_funcs = list(removed_funcs - added_funcs)   # Removed entirely

    has_change = len(changed_funcs) > 0 or len(renamed_funcs) > 0
    all_affected = changed_funcs + renamed_funcs
    return has_change, all_affected


def mine_refactor_commits(
    repo_dir: str,
    min_files: int = 4,
    max_commits_to_scan: int = 5000,
    max_tasks: int = 30,
) -> list[dict]:
    """
    Scan git history for commits that:
      - Touch >= min_files Python files
      - Contain a function signature change or rename
    """
    print(f"📜 Scanning up to {max_commits_to_scan} commits in {repo_dir}...")
    commits = get_commit_list(repo_dir, max_commits=max_commits_to_scan)
    print(f"   Found {len(commits)} non-merge commits total")

    tasks = []
    scanned = 0

    for sha in commits:
        scanned += 1
        if scanned % 500 == 0:
            print(f"   ...scanned {scanned}/{len(commits)} commits, found {len(tasks)} tasks so far")

        py_files = get_changed_files(repo_dir, sha)
        if len(py_files) < min_files:
            continue

        try:
            has_sig_change, affected_funcs = diff_has_signature_change(repo_dir, sha)
        except Exception:
            continue

        if not has_sig_change:
            continue

        info = get_commit_info(repo_dir, sha)
        if not info:
            continue

        task = {
            **info,
            "python_files_changed": len(py_files),
            "files": py_files,
            "affected_functions": affected_funcs,
        }
        tasks.append(task)

        if len(tasks) >= max_tasks:
            print(f"   ✅ Reached {max_tasks} tasks, stopping scan")
            break

    print(f"\n📊 Scan complete: {scanned} commits scanned, {len(tasks)} refactor tasks found")
    return tasks


def main():
    parser = argparse.ArgumentParser(
        description="Mine Django git history for refactoring commits"
    )
    parser.add_argument(
        "--repo",
        required=True,
        help="Path to the Django git repository",
    )
    parser.add_argument(
        "--min-files",
        type=int,
        default=4,
        help="Minimum number of Python files changed (default: 4)",
    )
    parser.add_argument(
        "--max-commits",
        type=int,
        default=5000,
        help="Maximum commits to scan (default: 5000)",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=30,
        help="Maximum tasks to collect (default: 30)",
    )
    parser.add_argument(
        "--output",
        default="refactor_tasks.json",
        help="Output JSON file path",
    )
    args = parser.parse_args()

    if not os.path.isdir(os.path.join(args.repo, ".git")):
        print(f"❌ Error: {args.repo} is not a git repository")
        sys.exit(1)

    tasks = mine_refactor_commits(
        args.repo,
        min_files=args.min_files,
        max_commits_to_scan=args.max_commits,
        max_tasks=args.max_tasks,
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(tasks, f, indent=2)

    print(f"\n💾 Saved {len(tasks)} tasks to {args.output}")

    # Print a preview
    print("\n📋 Task Preview:")
    print("-" * 70)
    for i, t in enumerate(tasks[:5]):
        print(
            f"  {i+1}. [{t['sha'][:8]}] {t['subject'][:60]}"
            f"  ({t['python_files_changed']} files, funcs: {t['affected_functions'][:3]})"
        )
    if len(tasks) > 5:
        print(f"  ... and {len(tasks) - 5} more")


if __name__ == "__main__":
    main()
