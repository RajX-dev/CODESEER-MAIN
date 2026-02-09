import os
from pathlib import Path
# 1. Imports
from symbol_extractor import extract_symbols_imports_calls
from database import ensure_project, upsert_symbol, upsert_import, upsert_call
from resolve_imports import resolve_project_imports
from resolve_calls import resolve_project_calls  # <--- New Day 23 Import

def ingest_repo(repo_path, project_name, repo_url):
    print(f"\n🚀 STARTING INGESTION: {project_name}")
    print(f"📂 Scanning: {repo_path}")

    # 2. Define project_id (This was likely missing)
    project_id = ensure_project(project_name, repo_url)
    print(f"✅ Project ID: {project_id}")

    file_count = 0
    
    # 3. Walk the directory
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

    # 4. Linking Phases
    print("\n🔗 STARTING LINKING PHASE...")
    
    # Day 21: Resolve Imports
    resolve_project_imports(project_id)
    
    # Day 23: Resolve Calls (NEW)
    resolve_project_calls(project_id)

    print(f"\n🏁 INGESTION COMPLETE.")
    print(f"Files: {file_count}")

def process_file(full_path, rel_path, project_id):
    with open(full_path, "rb") as f:
        code_bytes = f.read()

    # Extract EVERYTHING
    symbols, imports, calls = extract_symbols_imports_calls(code_bytes, str(rel_path))

    # Save Imports
    for imp in imports:
        upsert_import(project_id, imp)

    # Save Symbols
    temp_to_real_id = {}
    for sym in symbols:
        if sym["parent_id"] and sym["parent_id"] in temp_to_real_id:
            sym["parent_id"] = temp_to_real_id[sym["parent_id"]]
        real_id = upsert_symbol(project_id, sym)
        temp_to_real_id[sym["id"]] = real_id

    # Save Calls
    for call in calls:
        if call["source_symbol_id"] in temp_to_real_id:
            call["source_symbol_id"] = temp_to_real_id[call["source_symbol_id"]]
            upsert_call(project_id, call)

if __name__ == "__main__":
    ingest_repo(".", "CodeSeer-Indexer", "http://internal/codeseer")