import os
import sys

# --- DATABASE IMPORTS ---
from src.database import (
    ensure_project,
    replace_file_index,
)

# --- CRAWLER IMPORT ---
# Using the file 'crawler.py' seen in your screenshot
try:
    from crawler import crawl_directory
except ImportError:
    from src.crawler import crawl_directory

# --- EXTRACTOR IMPORT ---
# Using the file 'symbol_extractor.py' seen in your screenshot
try:
    from src.symbol_extractor import extract_symbols
except ImportError:
    try:
        from src.symbol_extractor import extract_symbols
    except ImportError:
        # Fallback if Python path is tricky
        from extractor import extract_symbols

# --- RESOLVER IMPORT ---
# Using the file 'resolve_calls.py' seen in your screenshot
try:
    from src.resolve_calls import resolve_call_links
except ImportError:
    from src.resolve_calls import resolve_call_links

def main():
    target_dir = os.getenv("TARGET_CODE_DIR", os.getcwd())
    print(f"\n🌊 N3MO: Starting Analysis on {target_dir}...")

    if not os.path.exists(target_dir):
        print(f"❌ Error: Target directory '{target_dir}' does not exist.")
        return

    # Setup Project
    project_name = os.path.basename(target_dir)
    try:
        project_id = ensure_project(project_name, repo_url=target_dir)
        print(f"✅ Project ID: {project_id}")
    except Exception as e:
        print(f"❌ Database Connection Failed: {e}")
        return

    # Crawl
    print("🕷️  Crawling files...")
    files = crawl_directory(target_dir)
    print(f"   Found {len(files)} Python files.")

    # Extract & Index
    print("🧠 Extracting symbols...")
    symbol_count = 0
    call_count = 0
    
    for file_path in files:
        rel_path = os.path.relpath(file_path, target_dir)
        try:
            result = extract_symbols(file_path)
            
            # Unpack safely
            if isinstance(result, tuple) and len(result) == 3:
                symbols, imports, calls = result
            else:
                symbols = result; imports = []; calls = []

            replace_file_index(
                project_id,
                rel_path,
                symbols,
                imports,
                calls,
            )
            symbol_count += len(symbols)
            call_count += len(calls)

        except Exception as exc:
            print(f"Warning: failed to index {rel_path}: {exc}")

    # --- RUN THE LINKER (Using your existing resolve_calls.py) ---
    print("🔗 resolving calls...")
    resolve_call_links(project_id)

    print("-" * 30)
    print(f"✅ Indexing Complete!")
    print(f"📊 Processed: {len(files)} files")
    print(f"📚 Symbols:   {symbol_count}")
    print(f"📞 Calls:     {call_count}")
    print("-" * 30)

if __name__ == "__main__":
    main()
