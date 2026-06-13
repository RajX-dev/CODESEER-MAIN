import os
import sys
import shutil
import time

# Reconfigure stdout to use utf-8 for Windows emoji support
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from src.run_indexer import main as run_indexer
from src.database import get_connection, release_connection


def create_dummy_repo(repo_dir):
    os.makedirs(repo_dir, exist_ok=True)
    
    # Create 20 dummy Python files with classes and functions calling each other
    for i in range(20):
        filepath = os.path.join(repo_dir, f"module_{i}.py")
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# Module {i}\n")
            f.write(f"def func_{i}_1():\n")
            f.write(f"    print('Hello from function 1 in module {i}')\n\n")
            f.write(f"def func_{i}_2():\n")
            f.write(f"    func_{i}_1()\n")
            if i > 0:
                f.write(f"    from module_{i-1} import func_{i-1}_2\n")
                f.write(f"    func_{i-1}_2()\n")

def modify_one_file(repo_dir):
    filepath = os.path.join(repo_dir, "module_5.py")
    with open(filepath, "a", encoding="utf-8") as f:
        f.write("\n\ndef func_new_addition():\n")
        f.write("    print('This is a new addition!')\n")

def wipe_db_for_clean_slate(repo_url):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM projects WHERE repo_url = %s", (repo_url,))
            conn.commit()
    finally:
        release_connection(conn)

def main():
    bench_dir = os.path.dirname(os.path.abspath(__file__))
    dummy_repo_dir = os.path.join(bench_dir, "dummy_repo")
    dummy_repo_abs = os.path.abspath(dummy_repo_dir)

    print("📊 Starting N3MO Indexing Performance Benchmark...")
    print(f"📁 Creating dummy repository at: {dummy_repo_abs}")
    create_dummy_repo(dummy_repo_abs)

    # Set environment variable for target dir
    os.environ["TARGET_CODE_DIR"] = dummy_repo_abs

    # Ensure a completely clean slate (no projects indexed at all)
    wipe_db_for_clean_slate(dummy_repo_abs)

    print("\n--- 1. Running Full Index (First Run) ---")
    start_time = time.time()
    run_indexer()
    full_index_time = time.time() - start_time

    print("\n--- 2. Running Incremental Index (No Changes) ---")
    start_time = time.time()
    run_indexer()
    incr_no_changes_time = time.time() - start_time

    print("\n--- 3. Modifying 1 File ---")
    modify_one_file(dummy_repo_abs)

    print("\n--- 4. Running Incremental Index (1 File Changed) ---")
    start_time = time.time()
    run_indexer()
    incr_one_change_time = time.time() - start_time

    # Cleanup dummy repo
    print(f"\n🧹 Cleaning up dummy repository...")
    if os.path.exists(dummy_repo_abs):
        shutil.rmtree(dummy_repo_abs)

    # Output results
    print("\n" + "=" * 50)
    print("📈 BENCHMARK RESULTS")
    print("=" * 50)
    print(f"Full Index (20 files):          {full_index_time:.4f} seconds (1.0x)")
    print(f"Incremental (0 changes):        {incr_no_changes_time:.4f} seconds ({full_index_time / max(0.0001, incr_no_changes_time):.1f}x speedup)")
    print(f"Incremental (1 file modified):  {incr_one_change_time:.4f} seconds ({full_index_time / max(0.0001, incr_one_change_time):.1f}x speedup)")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()
