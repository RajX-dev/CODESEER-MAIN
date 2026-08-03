# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

"""
LLM Hallucination Reduction Evaluation Harness.

Three-condition experiment evaluating whether N3MO structural context
reduces hallucination rate in LLM-assisted refactoring tasks.

Conditions:
  A) No-tool baseline — LLM receives only the instruction and file list
  B) Vector-RAG baseline — LLM receives semantically similar file chunks
  C) N3MO via MCP — LLM receives the deterministic blast-radius subgraph

Ground-truth: Real Django git commits that renamed/changed function signatures
and touched 4+ files (produced by mine_django_refactors.py).

Metrics (per task, compared against the real commit diff):
  - Recall:     % of actually-changed files the LLM identified
  - Precision:  % of LLM-identified files that were actually changed
  - Hallucination rate: % of LLM responses containing references to
                        non-existent symbols

Usage:
    python scripts/llm_eval_harness.py \\
        --tasks refactor_tasks.json \\
        --django-repo /path/to/django \\
        --api-key sk-... \\
        --model gpt-4o \\
        --output eval_results.json

Prerequisites:
    - Django repo cloned locally
    - refactor_tasks.json produced by mine_django_refactors.py
    - An OpenAI or Anthropic API key
    - N3MO indexer running with PostgreSQL for condition C
"""

import argparse
import json
import os
import subprocess
import sys
import time
import re

# Reconfigure stdout to use utf-8 for Windows emoji support
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def checkout_commit(repo_dir: str, sha: str):
    """Checkout the parent of a commit (pre-refactor state)."""
    subprocess.run(
        ["git", "-C", repo_dir, "checkout", f"{sha}~1", "--force"],
        capture_output=True, text=True, timeout=30,
    )


def get_diff_files(repo_dir: str, sha: str) -> list[str]:
    """Get the list of Python files changed in a commit (ground truth)."""
    result = subprocess.run(
        ["git", "-C", repo_dir, "diff-tree", "--no-commit-id", "-r",
         "--name-only", sha],
        capture_output=True, text=True, timeout=30,
    )
    files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    return [f for f in files if f.endswith(".py")]


def get_commit_message(repo_dir: str, sha: str) -> str:
    """Get the commit message to use as the refactor instruction."""
    result = subprocess.run(
        ["git", "-C", repo_dir, "log", "-1", "--format=%B", sha],
        capture_output=True, text=True, timeout=30,
    )
    return result.stdout.strip()


def read_file_contents(repo_dir: str, file_path: str) -> str:
    """Read a file's contents, with error handling."""
    full_path = os.path.join(repo_dir, file_path)
    try:
        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def call_openai(api_key: str, model: str, system_prompt: str,
                user_prompt: str) -> str:
    """Call the OpenAI API. Returns the response text."""
    try:
        import openai
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.choices[0].message.content
    except ImportError:
        print("❌ Error: pip install openai required")
        sys.exit(1)


def call_anthropic(api_key: str, model: str, system_prompt: str,
                   user_prompt: str) -> str:
    """Call the Anthropic API. Returns the response text."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=0,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt},
            ],
        )
        return response.content[0].text
    except ImportError:
        print("❌ Error: pip install anthropic required")
        sys.exit(1)


def call_llm(api_key: str, model: str, system_prompt: str,
             user_prompt: str) -> str:
    """Route to the correct API based on model name."""
    if model.startswith("claude"):
        return call_anthropic(api_key, model, system_prompt, user_prompt)
    else:
        return call_openai(api_key, model, system_prompt, user_prompt)


def extract_mentioned_files(response: str) -> list[str]:
    """Extract file paths mentioned in the LLM response."""
    # Match patterns like `path/to/file.py` or path/to/file.py
    pattern = r'[\w/\\.-]+\.py'
    matches = re.findall(pattern, response)
    # Deduplicate while preserving order
    seen = set()
    result = []
    for m in matches:
        m = m.replace("\\", "/")
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def extract_mentioned_symbols(response: str) -> list[str]:
    """Extract function/class names from backtick-quoted references."""
    pattern = r'`(\w+(?:\.\w+)*)`'
    return list(set(re.findall(pattern, response)))


def check_hallucinations(mentioned_symbols: list[str],
                         repo_dir: str, relevant_files: list[str]) -> list[str]:
    """
    Check which mentioned symbols don't actually exist in the relevant files.
    A hallucination = the LLM referenced a symbol that doesn't exist.
    """
    # Build a set of all identifiers from the relevant source files
    real_identifiers = set()
    for fpath in relevant_files:
        content = read_file_contents(repo_dir, fpath)
        # Extract def/class names
        for m in re.finditer(r'(?:def|class)\s+(\w+)', content):
            real_identifiers.add(m.group(1))
        # Also add dotted forms
        for m in re.finditer(r'(\w+\.\w+)', content):
            real_identifiers.add(m.group(1))

    # Common builtins/stdlib that shouldn't count as hallucinations
    builtins = {
        'self', 'cls', 'None', 'True', 'False', 'print', 'len', 'str',
        'int', 'list', 'dict', 'set', 'tuple', 'type', 'super', 'range',
        'open', 'os', 'sys', 'json', 're', 'path', 'import', 'return',
    }

    hallucinations = []
    for sym in mentioned_symbols:
        base = sym.split(".")[-1]  # Check the leaf name
        if base in builtins:
            continue
        if sym not in real_identifiers and base not in real_identifiers:
            hallucinations.append(sym)

    return hallucinations


def get_n3mo_blast_radius(affected_funcs: list[str], repo_dir: str) -> str:
    """
    Query N3MO for the blast radius of the affected functions.
    Returns a formatted string of the impact analysis.
    """
    # Try using N3MO CLI
    results = []
    for func in affected_funcs[:3]:  # Limit to 3 to keep context manageable
        try:
            result = subprocess.run(
                ["n3mo", "impact", func],
                capture_output=True, text=True, timeout=30,
                cwd=repo_dir,
            )
            if result.returncode == 0:
                results.append(f"Impact analysis for `{func}`:\n{result.stdout}")
        except Exception:
            pass

    if results:
        return "\n\n".join(results)
    return "N3MO impact analysis unavailable for this task."


def evaluate_condition(
    condition: str,
    task: dict,
    repo_dir: str,
    api_key: str,
    model: str,
) -> dict:
    """
    Evaluate a single task under a single condition.
    Returns metrics dict.
    """
    sha = task["sha"]
    ground_truth_files = set(task["files"])
    commit_msg = get_commit_message(repo_dir, sha)
    affected_funcs = task.get("affected_functions", [])

    # Checkout pre-commit state
    checkout_commit(repo_dir, sha)

    system_prompt = (
        "You are a senior software engineer. You are given a refactoring "
        "instruction for a large Python codebase (Django). Your job is to "
        "identify ALL files that need to be modified to complete this refactor "
        "safely. List each file path. Be thorough — missing a file means a "
        "regression."
    )

    if condition == "A":
        # No-tool baseline: just the instruction
        user_prompt = (
            f"Refactoring instruction (from a commit message):\n"
            f"{commit_msg}\n\n"
            f"The affected function(s): {', '.join(affected_funcs)}\n\n"
            f"List ALL Python files in the Django repository that would need "
            f"to be modified for this refactor."
        )
    elif condition == "B":
        # Vector-RAG: include some file contents of affected functions' files
        context_files = []
        for fpath in list(ground_truth_files)[:5]:
            content = read_file_contents(repo_dir, fpath)
            if content:
                # Truncate to first 200 lines
                lines = content.split("\n")[:200]
                context_files.append(f"--- {fpath} ---\n" + "\n".join(lines))

        user_prompt = (
            f"Refactoring instruction:\n{commit_msg}\n\n"
            f"The affected function(s): {', '.join(affected_funcs)}\n\n"
            f"Here are some relevant files from the codebase:\n\n"
            + "\n\n".join(context_files) + "\n\n"
            f"Based on these files and your knowledge of Django, list ALL "
            f"Python files that would need to be modified for this refactor."
        )
    elif condition == "C":
        # N3MO: include the blast radius analysis
        blast_radius = get_n3mo_blast_radius(affected_funcs, repo_dir)
        user_prompt = (
            f"Refactoring instruction:\n{commit_msg}\n\n"
            f"The affected function(s): {', '.join(affected_funcs)}\n\n"
            f"N3MO structural impact analysis (blast radius):\n"
            f"{blast_radius}\n\n"
            f"Based on the structural impact analysis above, list ALL "
            f"Python files that would need to be modified for this refactor."
        )
    else:
        raise ValueError(f"Unknown condition: {condition}")

    # Call the LLM
    response = call_llm(api_key, model, system_prompt, user_prompt)

    # Extract predictions
    predicted_files = set(extract_mentioned_files(response))
    mentioned_symbols = extract_mentioned_symbols(response)

    # Calculate metrics
    true_positives = predicted_files & ground_truth_files
    false_positives = predicted_files - ground_truth_files
    false_negatives = ground_truth_files - predicted_files

    recall = len(true_positives) / len(ground_truth_files) if ground_truth_files else 0
    precision = len(true_positives) / len(predicted_files) if predicted_files else 0

    # Check hallucinations
    all_relevant_files = list(ground_truth_files | predicted_files)
    hallucinated_symbols = check_hallucinations(
        mentioned_symbols, repo_dir, all_relevant_files
    )
    hallucination_rate = (
        len(hallucinated_symbols) / len(mentioned_symbols)
        if mentioned_symbols else 0
    )

    return {
        "condition": condition,
        "sha": sha,
        "ground_truth_count": len(ground_truth_files),
        "predicted_count": len(predicted_files),
        "true_positives": len(true_positives),
        "false_positives": len(false_positives),
        "false_negatives": len(false_negatives),
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "symbols_mentioned": len(mentioned_symbols),
        "hallucinated_symbols": len(hallucinated_symbols),
        "hallucination_rate": round(hallucination_rate, 4),
        "hallucinated_names": hallucinated_symbols[:10],
    }


def main():
    parser = argparse.ArgumentParser(
        description="LLM Hallucination Reduction Evaluation Harness"
    )
    parser.add_argument(
        "--tasks", required=True,
        help="Path to refactor_tasks.json from mine_django_refactors.py",
    )
    parser.add_argument(
        "--django-repo", required=True,
        help="Path to the Django git repository",
    )
    parser.add_argument(
        "--api-key", required=True,
        help="OpenAI or Anthropic API key",
    )
    parser.add_argument(
        "--model", default="gpt-4o",
        help="Model to use (default: gpt-4o)",
    )
    parser.add_argument(
        "--max-tasks", type=int, default=20,
        help="Maximum tasks to evaluate (default: 20)",
    )
    parser.add_argument(
        "--output", default="eval_results.json",
        help="Output JSON file for results",
    )
    parser.add_argument(
        "--conditions", default="A,B,C",
        help="Comma-separated conditions to run (default: A,B,C)",
    )
    args = parser.parse_args()

    # Load tasks
    with open(args.tasks, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    tasks = tasks[:args.max_tasks]
    conditions = [c.strip() for c in args.conditions.split(",")]

    print("=" * 60)
    print("🧠 LLM Hallucination Reduction Evaluation Harness")
    print(f"   Model: {args.model}")
    print(f"   Tasks: {len(tasks)}")
    print(f"   Conditions: {conditions}")
    print("=" * 60)

    all_results = []
    original_branch = "main"

    try:
        for i, task in enumerate(tasks):
            print(f"\n{'─'*60}")
            print(f"📋 Task {i+1}/{len(tasks)}: [{task['sha'][:8]}] {task['subject'][:50]}")
            print(f"   Files changed: {task['python_files_changed']}, "
                  f"Functions: {task.get('affected_functions', [])[:3]}")

            for cond in conditions:
                print(f"   ▸ Running Condition {cond}...", end=" ", flush=True)
                try:
                    result = evaluate_condition(
                        cond, task, args.django_repo, args.api_key, args.model
                    )
                    all_results.append(result)
                    print(
                        f"R={result['recall']:.0%} P={result['precision']:.0%} "
                        f"H={result['hallucination_rate']:.0%}"
                    )
                except Exception as e:
                    print(f"❌ Error: {e}")
                    all_results.append({
                        "condition": cond,
                        "sha": task["sha"],
                        "error": str(e),
                    })

                # Rate limiting
                time.sleep(1)

    finally:
        # Restore the original branch
        subprocess.run(
            ["git", "-C", args.django_repo, "checkout", original_branch, "--force"],
            capture_output=True, text=True,
        )

    # Compute aggregate metrics
    print("\n\n" + "=" * 70)
    print("📈 AGGREGATE RESULTS")
    print("=" * 70)
    print(f"{'Condition':<15} {'Avg Recall':<15} {'Avg Precision':<15} "
          f"{'Avg Halluc.':<15} {'N Tasks':<10}")
    print("-" * 70)

    for cond in conditions:
        cond_results = [r for r in all_results
                        if r.get("condition") == cond and "error" not in r]
        if not cond_results:
            print(f"  {cond:<15} — no successful runs —")
            continue

        avg_recall = sum(r["recall"] for r in cond_results) / len(cond_results)
        avg_precision = sum(r["precision"] for r in cond_results) / len(cond_results)
        avg_halluc = sum(r["hallucination_rate"] for r in cond_results) / len(cond_results)

        labels = {"A": "No-tool", "B": "Vector-RAG", "C": "N3MO"}
        label = labels.get(cond, cond)
        print(
            f"  {label:<15} {avg_recall:<15.1%} {avg_precision:<15.1%} "
            f"{avg_halluc:<15.1%} {len(cond_results):<10}"
        )

    print("=" * 70)

    # Save results
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({
            "model": args.model,
            "task_count": len(tasks),
            "conditions": conditions,
            "results": all_results,
        }, f, indent=2)
    print(f"\n💾 Results saved to {args.output}")


if __name__ == "__main__":
    main()
