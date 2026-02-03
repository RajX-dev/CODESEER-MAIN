import os
from pathlib import Path
from database import ensure_project, upsert_symbol
from symbol_extractor import extract_symbols

def ingest_repo(repo_path, project_name, repo_url):
    print(f"STARTING INGESTION: {project_name}")
    print(f"Scanning: {repo_path}")

    # 1. Create or Get Project ID
    project_id = ensure_project(project_name, repo_url)
    print(f"Project ID: {project_id}")

    # 2. Walk the directory
    file_count = 0
    
    # os.walk finds files recursively
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.endswith(".py"):
                full_path = Path(root) / file
                
                # Get relative path (e.g., "src/main.py")
                rel_path = os.path.relpath(full_path, repo_path)
                
                try:
                    process_file(full_path, rel_path, project_id)
                    file_count += 1
                    print(f"   Processed: {rel_path}")
                except Exception as e:
                    print(f"   Failed to process {rel_path}: {e}")

    print("INGESTION COMPLETE.")
    print(f"Files Processed: {file_count}")

def process_file(full_path, rel_path, project_id):
    # 1. Read Code
    with open(full_path, "rb") as f:
        code_bytes = f.read()

    # 2. Extract Symbols (Tree-sitter)
    # This returns a list sorted by hierarchy
    symbols = extract_symbols(code_bytes, str(rel_path))

    # 3. Insert into DB (Upsert)
    # We use a map to link temporary IDs to real Database UUIDs
    temp_to_real_id = {}

    for sym in symbols:
        # Resolve Parent ID
        if sym["parent_id"]:
            if sym["parent_id"] in temp_to_real_id:
                sym["parent_id"] = temp_to_real_id[sym["parent_id"]]
            else:
                # If parent is missing, skip to avoid foreign key errors
                continue

        # Insert and get the Real UUID
        real_id = upsert_symbol(project_id, sym)
        
        # Update the map for future children
        temp_to_real_id[sym["id"]] = real_id

if __name__ == "__main__":
    # Self-Indexing: Scan the current folder
    ingest_repo(".", "CodeSeer-Indexer", "http://internal/codeseer")