# N3MO 
# Copyright (C) 2026 Raj Shekhar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.



import os
from pathlib import Path

# 1. Imports
from n3mo.symbol_extractor import extract_symbols_imports_calls
from n3mo.database import ensure_project, upsert_import, upsert_call, batch_upsert_symbols
from n3mo.resolve_imports import resolve_import_links
from n3mo.resolve_calls import resolve_call_links

# ==========================================
# 🛑 IGNORE LIST (The Speed Boost)
# ==========================================
IGNORE_DIRS = {
    "venv", ".venv", "env", ".env",       # Virtual Environments
    ".git", ".github", ".idea", ".vscode", # Configs & Git
    "__pycache__", "build", "dist",       # Build Artifacts
    "node_modules", "site-packages",      # External Dependencies
    "migrations", "tests", "docs"         # Optional: Skip DB migrations/docs
}

def ingest_repo(repo_path, project_name, repo_url):
    repo_path = os.path.abspath(repo_path)
    print(f"\n🚀 STARTING INGESTION: {project_name}")
    print(f"📂 Scanning: {repo_path}")

    # 2. Define project_id
    project_id = ensure_project(project_name, repo_url)
    print(f"✅ Project ID: {project_id}")

    file_count = 0
    
    # 3. Walk the directory
    # Note: We capture 'dirs' now so we can filter it!
    for root, dirs, files in os.walk(repo_path):
        
        # ----------------------------------------
        # ⚡ CRITICAL OPTIMIZATION
        # Modify 'dirs' in-place to stop os.walk from entering ignored folders
        # ----------------------------------------
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            if file.endswith(".py"):
                full_path = Path(root) / file
                rel_path = os.path.relpath(full_path, repo_path)
                
                # Extra check: Skip hidden files (like .DS_Store or .coverage)
                if file.startswith("."):
                    continue

                try:
                    process_file(full_path, rel_path, project_id)
                    file_count += 1
                    print(f"   Processed: {rel_path}")
                except Exception as e:
                    print(f"❌ Failed to process {rel_path}: {e}")

    # 4. Linking Phases
    print("\n🔗 STARTING LINKING PHASE...")
    
    # Resolve Imports
    resolve_import_links(project_id)
    
    # Resolve Calls
    resolve_call_links(project_id)

    print("\n🏁 INGESTION COMPLETE.")
    print(f"Files: {file_count}")

def process_file(full_path, rel_path, project_id):
    # Read file safely
    try:
        with open(full_path, "rb") as f:
            code_bytes = f.read()
    except Exception as e:
        print(f"⚠️ Could not read {rel_path}: {e}")
        return

    # Extract EVERYTHING
    try:
       symbols, imports, calls = extract_symbols_imports_calls(code_bytes, str(full_path.resolve()))
    except Exception as e:
        print(f"⚠️ Parse Error in {rel_path}: {e}")
        return

    # Save Imports
    for imp in imports:
        upsert_import(project_id, imp)

    # Save Symbols - batch insert classes first, then functions
    temp_to_real_id = {}

    # Split by kind
    classes = [sym for sym in symbols if sym["kind"] == "CLASS"]
    functions = [sym for sym in symbols if sym["kind"] == "FUNCTION"]

    # Insert classes first - get real IDs back
    class_id_map = batch_upsert_symbols(project_id, classes)
    temp_to_real_id.update({sym["id"]: class_id_map.get(sym["name"]) for sym in classes})

    # Update parent IDs for functions
    for sym in functions:
        if sym["parent_id"] and sym["parent_id"] in temp_to_real_id:
            sym["parent_id"] = temp_to_real_id[sym["parent_id"]]

    # Insert functions with correct parent IDs
    func_id_map = batch_upsert_symbols(project_id, functions)
    temp_to_real_id.update({sym["id"]: func_id_map.get(sym["name"]) for sym in functions})
    # Save Calls
    for call in calls:
        if call["source_symbol_id"] in temp_to_real_id:
            call["source_symbol_id"] = temp_to_real_id[call["source_symbol_id"]]
            upsert_call(project_id, call)

if __name__ == "__main__":
    # Standard local run
    ingest_repo(".", "N3MO-Indexer", "http://internal/N3MO")

