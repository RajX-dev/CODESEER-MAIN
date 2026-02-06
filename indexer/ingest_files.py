import os
from pathlib import Path
# FIX: Import the new extractor name
from symbol_extractor import extract_symbols_imports_calls
# FIX: Import upsert_call
from database import ensure_project, upsert_symbol, upsert_import, upsert_call
from resolve_imports import resolve_project_imports

def ingest_repo(repo_path, project_name, repo_url):
    print(f"\n🚀 STARTING INGESTION: {project_name}")
    
    project_id = ensure_project(project_name, repo_url)
    print(f"✅ Project ID: {project_id}")

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

    print("\n🔗 STARTING LINKING PHASE...")
    resolve_project_imports(project_id)

    print(f"\n🏁 INGESTION COMPLETE. Files: {file_count}")

def process_file(full_path, rel_path, project_id):
    with open(full_path, "rb") as f:
        code_bytes = f.read()

    # 1. Extract EVERYTHING (Symbols, Imports, Calls)
    symbols, imports, calls = extract_symbols_imports_calls(code_bytes, str(rel_path))

    # 2. Save Imports
    for imp in imports:
        upsert_import(project_id, imp)

    # 3. Save Symbols
    temp_to_real_id = {}
    for sym in symbols:
        if sym["parent_id"] and sym["parent_id"] in temp_to_real_id:
            sym["parent_id"] = temp_to_real_id[sym["parent_id"]]
        real_id = upsert_symbol(project_id, sym)
        temp_to_real_id[sym["id"]] = real_id

    # 4. Save Calls (NEW)
    for call in calls:
        # Check: Does the caller exist in our map?
        if call["source_symbol_id"] in temp_to_real_id:
            # Swap temp ID for Real DB UUID
            call["source_symbol_id"] = temp_to_real_id[call["source_symbol_id"]]
            upsert_call(project_id, call)

if __name__ == "__main__":
    ingest_repo(".", "CodeSeer-Indexer", "http://internal/codeseer")