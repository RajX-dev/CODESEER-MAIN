# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

"""
Real Multi-Language Repository Benchmark for N3MO.

This script clones real open-source repositories in different languages,
runs the N3MO indexer against each one, and records actual wall-clock time,
symbol counts, call edge counts, and import counts from the database.

Results are printed as a formatted table and saved to a JSON file for
inclusion in the paper.

Usage:
    python benchmarks/benchmark_multilang_repo.py

Prerequisites:
    - Docker must be running with the N3MO PostgreSQL container up.
    - N3MO must be installed (pip install -e .)
    - Git must be available in PATH.
"""

import os
import sys
import json
import time
import shutil
import subprocess
import tempfile

# Reconfigure stdout to use utf-8 for Windows emoji support
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure project root is in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from n3mo.core.run_indexer import run_indexer_for_path  # noqa: E402
from n3mo.core.database import get_connection, release_connection  # noqa: E402


# --- Repositories to benchmark ---
# Each entry: (name, git_url, primary_language, description)
REPOS = [
    (
        "express",
        "https://github.com/expressjs/express.git",
        "JavaScript",
        "Fast, unopinionated, minimalist web framework for Node.js",
    ),
    (
        "spring-petclinic",
        "https://github.com/spring-projects/spring-petclinic.git",
        "Java",
        "A sample Spring application demonstrating Spring Boot, MVC, etc.",
    ),
    (
        "hugo",
        "https://github.com/gohugoio/hugo.git",
        "Go",
        "The world's fastest framework for building websites",
    ),
]


def clone_repo(git_url: str, dest_dir: str) -> bool:
    """Shallow clone a repository. Returns True on success."""
    print(f"   📥 Cloning {git_url} ...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", git_url, dest_dir],
            capture_output=True,
            text=True,
            check=True,
            timeout=300,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Clone failed: {e.stderr[:200]}")
        return False
    except subprocess.TimeoutExpired:
        print("   ❌ Clone timed out (300s limit)")
        return False


def count_source_files(directory: str) -> int:
    """Count all non-hidden, non-test source files."""
    count = 0
    for root, dirs, files in os.walk(directory):
        # Skip hidden dirs and common non-source dirs
        dirs[:] = [
            d for d in dirs
            if not d.startswith('.') and d not in (
                'node_modules', 'vendor', '__pycache__', 'dist', 'build',
                'target', '.git', 'test', 'tests', 'spec', 'specs',
            )
        ]
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in (
                '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.rs',
                '.java', '.cpp', '.c', '.cs', '.kt', '.swift', '.scala',
                '.rb', '.php', '.lua', '.pl', '.hs', '.jl',
            ):
                count += 1
    return count


def get_db_stats(project_id: str) -> dict:
    """Query actual database counts for a project."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM symbols WHERE project_id = %s",
                (project_id,),
            )
            symbol_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM calls WHERE project_id = %s",
                (project_id,),
            )
            call_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM imports WHERE project_id = %s",
                (project_id,),
            )
            import_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM files WHERE project_id = %s",
                (project_id,),
            )
            file_count = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM calls WHERE project_id = %s AND resolved_symbol_id IS NOT NULL",
                (project_id,),
            )
            resolved_calls = cur.fetchone()[0]

            return {
                "files_indexed": file_count,
                "symbols": symbol_count,
                "calls": call_count,
                "resolved_calls": resolved_calls,
                "imports": import_count,
            }
    finally:
        release_connection(conn)


def get_project_id(repo_url: str):
    """Look up project ID by repo_url."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM projects WHERE repo_url = %s", (repo_url,)
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        release_connection(conn)


def wipe_project(repo_url: str):
    """Remove a project and all its data from the database."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM projects WHERE repo_url = %s", (repo_url,)
            )
            conn.commit()
    finally:
        release_connection(conn)


def benchmark_repo(name, git_url, language, description):
    """Clone, index, measure, and clean up a single repository."""
    print(f"\n{'='*60}")
    print(f"📊 Benchmarking: {name} ({language})")
    print(f"   {description}")
    print(f"{'='*60}")

    # Create a temp directory for the clone
    temp_dir = tempfile.mkdtemp(prefix=f"n3mo_bench_{name}_")
    clone_dir = os.path.join(temp_dir, name)

    result = {
        "name": name,
        "language": language,
        "git_url": git_url,
        "status": "failed",
    }

    try:
        # Step 1: Clone
        if not clone_repo(git_url, clone_dir):
            result["error"] = "clone_failed"
            return result

        # Count source files before indexing
        source_file_count = count_source_files(clone_dir)
        print(f"   📁 Source files found: {source_file_count}")
        result["source_files_detected"] = source_file_count

        # Step 2: Wipe any previous run for this path
        wipe_project(clone_dir)

        # Step 3: Set TARGET_CODE_DIR and run the indexer
        os.environ["TARGET_CODE_DIR"] = clone_dir

        print(f"   🚀 Running N3MO indexer...")
        start_time = time.time()
        success, summary = run_indexer_for_path(clone_dir)
        elapsed = time.time() - start_time

        result["index_time_seconds"] = round(elapsed, 2)
        result["indexer_success"] = success

        if not success:
            print(f"   ❌ Indexer failed: {summary[:200]}")
            result["error"] = summary[:200]
            return result

        # Step 4: Query real database stats
        project_id = get_project_id(clone_dir)
        if project_id:
            stats = get_db_stats(project_id)
            result.update(stats)
            result["status"] = "success"

            print(f"\n   ✅ Indexing Complete!")
            print(f"   ⏱️  Index Time:       {elapsed:.2f} seconds")
            print(f"   📁 Files Indexed:     {stats['files_indexed']}")
            print(f"   📚 Symbols:           {stats['symbols']}")
            print(f"   📞 Call Edges:        {stats['calls']}")
            print(f"   🔗 Resolved Calls:    {stats['resolved_calls']}")
            print(f"   📦 Imports:           {stats['imports']}")
        else:
            print(f"   ❌ Could not find project in database after indexing")
            result["error"] = "project_not_found_after_index"

        # Step 5: Cleanup project from DB
        wipe_project(clone_dir)

    finally:
        # Cleanup cloned repo from disk
        print(f"   🧹 Cleaning up {temp_dir}...")
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

    return result


def main():
    print("=" * 60)
    print("📊 N3MO Multi-Language Repository Benchmark")
    print("   Real runs on real repositories — no mocked data")
    print("=" * 60)

    all_results = []

    for name, git_url, language, description in REPOS:
        result = benchmark_repo(name, git_url, language, description)
        all_results.append(result)

    # Print summary table
    print("\n\n")
    print("=" * 80)
    print("📈 FINAL BENCHMARK RESULTS")
    print("=" * 80)
    print(
        f"{'Repo':<20} {'Language':<12} {'Time (s)':<12} {'Files':<8} "
        f"{'Symbols':<10} {'Calls':<10} {'Imports':<10} {'Status':<10}"
    )
    print("-" * 80)
    for r in all_results:
        if r["status"] == "success":
            print(
                f"{r['name']:<20} {r['language']:<12} "
                f"{r.get('index_time_seconds', '?'):<12} "
                f"{r.get('files_indexed', '?'):<8} "
                f"{r.get('symbols', '?'):<10} "
                f"{r.get('calls', '?'):<10} "
                f"{r.get('imports', '?'):<10} "
                f"{'✅':<10}"
            )
        else:
            print(
                f"{r['name']:<20} {r['language']:<12} "
                f"{'—':<12} {'—':<8} {'—':<10} {'—':<10} {'—':<10} "
                f"{'❌':<10}"
            )
    print("=" * 80)

    # Save results to JSON
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(output_dir, "multilang_benchmark_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n💾 Results saved to: {output_file}")


if __name__ == "__main__":
    main()
