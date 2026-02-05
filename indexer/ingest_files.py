import os
from pathlib import Path
# FIX: Import the new function name
from symbol_extractor import extract_symbols_and_imports
from database import ensure_project, upsert_symbol, upsert_import
from resolve_imports import resolve_project_imports

def ingest_repo(repo_path, project_name, repo_url):
    print(f"\n🚀 STARTING INGESTION: {project_name}")
    print(f"📂 Scanning: {repo_path}")

    # 1. Create/Get Project ID
    project_id = ensure_project(project_name, repo_url)
    print(f"✅ Project ID: {project_id}")

    # 2. Walk the directory
    file_count = 0
    
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                full_path = Path(root) / file
                rel_path = os.path.relpath(full_path, repo_path)
                
                try:
                    process_file(full_path, rel_path, project_id)
                    file_count += 1
                    print(f"   Processed: {rel_path}")
                except Exception as e:
                    print(f"❌ Failed to process {rel_path}: {e}")

    # --- STARTING LINKING PHASE (Day 21) ---
    print("\n🔗 STARTING LINKING PHASE...")
    resolve_project_imports(project_id)

    print(f"\n🏁 INGESTION COMPLETE.")
    print(f"Files: {file_count}")

def process_file(full_path, rel_path, project_id):
    # 1. Read Code
    with open(full_path, "rb") as f:
        code_bytes = f.read()

    # 2. Extract Symbols AND Imports (Updated function call)
    symbols, imports = extract_symbols_and_imports(code_bytes, str(rel_path))

    # 3. Insert IMPORTS first
    for imp in imports:
        upsert_import(project_id, imp)

    # 4. Insert SYMBOLS
    temp_to_real_id = {}

    for sym in symbols:
        if sym["parent_id"]:
            if sym["parent_id"] in temp_to_real_id:
                sym["parent_id"] = temp_to_real_id[sym["parent_id"]]
            else:
                continue

        real_id = upsert_symbol(project_id, sym)
        temp_to_real_id[sym["id"]] = real_id

if __name__ == "__main__":
    ingest_repo(".", "CodeSeer-Indexer", "http://internal/codeseer")