# Copyright (C) 2026 Raj shekhar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

import os
import sys
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add parent directory to path so we can import n3mo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from n3mo.run_indexer import main as run_indexer
from n3mo.database import get_connection, release_connection

def wipe_db_for_clean_slate(repo_url):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM projects WHERE repo_url = %s", (repo_url,))
            conn.commit()
    finally:
        release_connection(conn)

def main():
    if len(sys.argv) < 2:
        print("Usage: python benchmark_massive.py <path_to_repo>")
        sys.exit(1)

    target_dir = os.path.abspath(sys.argv[1])
    
    if not os.path.exists(target_dir):
        print(f"❌ Target directory does not exist: {target_dir}")
        sys.exit(1)

    print("📊 Starting N3MO Massive Codebase Benchmark...")
    print(f"📁 Target Repository: {target_dir}")
    
    # Set environment variable for target dir
    os.environ["TARGET_CODE_DIR"] = target_dir

    print("\n🧹 Wiping database state for this repository to ensure a cold start...")
    wipe_db_for_clean_slate(target_dir)

    print("\n🚀 --- RUNNING FULL INDEX ---")
    start_time = time.time()
    
    # Run the indexer
    try:
        run_indexer()
    except Exception as e:
        print(f"\n❌ Indexing failed: {e}")
        sys.exit(1)
        
    full_index_time = time.time() - start_time

    # Output results
    print("\n" + "=" * 60)
    print("📈 BENCHMARK RESULTS")
    print("=" * 60)
    print(f"Target Repository:  {target_dir}")
    print(f"Full Index Time:    {full_index_time:.4f} seconds ({full_index_time/60:.2f} minutes)")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    main()
