import os

# --- DATABASE IMPORTS ---
from src.database import (
    ensure_project,
    replace_file_index,
    get_file_hashes,
    upsert_file_hash,
    delete_file_index,
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

def start_docker_services():
    import subprocess
    import os
    
    print("🐳 Checking Docker services...")
    n3mo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    compose_path = os.path.join(n3mo_root, "docker-compose.yml")
    
    if not os.path.exists(compose_path):
        print(f"⚠️ Warning: docker-compose.yml not found at {compose_path}. Skipping automatic Docker startup.")
        return
        
    cmd = ["docker", "compose", "-f", compose_path, "up", "-d"]
    try:
        print(f"🚀 Running: {' '.join(cmd)}")
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Docker services started successfully.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        cmd_fallback = ["docker-compose", "-f", compose_path, "up", "-d"]
        try:
            print(f"🚀 Running fallback: {' '.join(cmd_fallback)}")
            subprocess.run(cmd_fallback, capture_output=True, text=True, check=True)
            print("✅ Docker services started successfully (using docker-compose).")
        except Exception as ex:
            print(f"❌ Failed to run docker compose: {ex}")
            print("⚠️ Please ensure Docker Desktop is running and docker compose is installed.")

def wait_for_postgres_and_schema(timeout=30):
    import time
    from src.database import get_connection, release_connection
    
    print("⏳ Waiting for PostgreSQL database and schema to be ready...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'projects'")
                exists = cur.fetchone()
                if not exists:
                    print("🗄️ Database empty. Initializing schema from db/schema.sql...")
                    n3mo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    schema_path = os.path.join(n3mo_root, "db", "schema.sql")
                    if os.path.exists(schema_path):
                        with open(schema_path, "r", encoding="utf-8") as f:
                            schema_sql = f.read()
                        cur.execute(schema_sql)
                        conn.commit()
                        print("✅ Database schema initialized successfully.")

                cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'projects'")
                exists = cur.fetchone()
                if exists:
                    # Automatically ensure files table is created
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS files (
                            project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                            file_path TEXT NOT NULL,
                            sha256 TEXT NOT NULL,
                            PRIMARY KEY (project_id, file_path)
                        )
                    """)
                    conn.commit()
                    print("✅ PostgreSQL database and schema are ready!")
                    return True
        except Exception:
            pass
        finally:
            if conn:
                try:
                    release_connection(conn)
                except Exception:
                    pass
        time.sleep(1.0)
            
    print("❌ Timeout waiting for PostgreSQL/schema to start. Please check container health.")
    return False

def clear_all_data(exclude_url=None):
    from src.database import get_connection, release_connection
    print("🧹 Cleaning database of other projects to ensure no residues...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if exclude_url:
                cur.execute("DELETE FROM projects WHERE repo_url != %s", (exclude_url,))
            else:
                cur.execute("DELETE FROM projects")
            conn.commit()
            print("✅ Database cleaned successfully.")
    except Exception as e:
        print(f"⚠️ Warning: Could not clear database: {e}")
    finally:
        release_connection(conn)

def calculate_sha256(file_path):
    import hashlib
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        print(f"⚠️ Warning: Could not calculate hash for {file_path}: {e}")
        return ""

def main():
    target_dir = os.getenv("TARGET_CODE_DIR", os.getcwd())
    print(f"\n🌊 N3MO: Starting Analysis on {target_dir}...")

    if not os.path.exists(target_dir):
        print(f"❌ Error: Target directory '{target_dir}' does not exist.")
        return

    # Automatically start Docker container and wait for Postgres readiness
    start_docker_services()
    if not wait_for_postgres_and_schema():
        print("❌ Aborting indexing due to database unreadiness.")
        return

    # Clear previous residues from OTHER repositories
    clear_all_data(exclude_url=target_dir)

    # Setup Project
    project_name = os.path.basename(target_dir)
    try:
        project_id = ensure_project(project_name, repo_url=target_dir)
        print(f"✅ Project ID: {project_id}")
    except Exception as e:
        print(f"❌ Database Connection Failed: {e}")
        return

    # Fetch existing file hashes
    existing_hashes = get_file_hashes(project_id)

    # Crawl
    print("🕷️  Crawling files...")
    files = crawl_directory(target_dir)
    print(f"   Found {len(files)} Python files.")

    # Detect deleted files (in database hash list, but not present in current crawl list)
    current_rel_paths = {os.path.relpath(f, target_dir) for f in files}
    deleted_files = [path for path in existing_hashes if path not in current_rel_paths]

    if deleted_files:
        print(f"🗑️  Pruning {len(deleted_files)} deleted files from index...")
        for path in deleted_files:
            try:
                delete_file_index(project_id, path)
            except Exception as e:
                print(f"   Warning: Failed to delete index for {path}: {e}")

    # Extract & Index
    print("🧠 Extracting symbols...")
    symbol_count = 0
    call_count = 0
    skipped_count = 0
    indexed_count = 0
    
    for file_path in files:
        rel_path = os.path.relpath(file_path, target_dir)
        current_hash = calculate_sha256(file_path)
        
        # Incremental check
        if rel_path in existing_hashes and existing_hashes[rel_path] == current_hash:
            skipped_count += 1
            continue

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
            
            if current_hash:
                upsert_file_hash(project_id, rel_path, current_hash)

            symbol_count += len(symbols)
            call_count += len(calls)
            indexed_count += 1

        except Exception as exc:
            print(f"Warning: failed to index {rel_path}: {exc}")

    # --- RUN THE LINKER (Using your existing resolve_calls.py) ---
    print("🔗 resolving calls...")
    resolve_call_links(project_id)

    print("-" * 30)
    print("✅ Indexing Complete!")
    print(f"📊 Processed: {len(files)} files")
    print(f"   Indexed:   {indexed_count} files (new/modified)")
    print(f"   Skipped:   {skipped_count} files (unchanged)")
    if indexed_count > 0:
        print(f"📚 Symbols:   {symbol_count} (newly indexed)")
        print(f"📞 Calls:     {call_count} (newly indexed)")
    print("-" * 30)

if __name__ == "__main__":
    main()
