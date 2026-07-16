# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

import os
import logging
import threading
import time
import math
import sys
from concurrent.futures import as_completed

# --- DATABASE IMPORTS ---
from n3mo.core.database import (
    ensure_project,
    replace_file_index,
    get_file_hashes,
    upsert_file_hash,
    delete_file_index,
)

# --- CRAWLER IMPORT ---
from n3mo.core.crawler import crawl_directory

# --- EXTRACTOR IMPORT ---
from n3mo.core.symbol_extractor import extract_symbols

# --- RESOLVER IMPORT ---
from n3mo.core.resolve_imports import resolve_import_links
from n3mo.core.resolve_calls import resolve_call_links

# Create module-level logger
logger = logging.getLogger("n3mo")

def setup_logging(target_dir):
    log_file = os.path.join(target_dir, "n3mo.log")
    
    # Configure logger
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    
    # File Handler
    try:
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s [%(process)d]: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"⚠️ Warning: Could not initialize log file at {log_file}: {e}")
        
    # Console Handler (StreamHandler)
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

class SolarSystemAnimation:
    def __init__(self, message="Indexing repository..."):
        self.message = message
        self.running = False
        self.thread = None
        self.height = 13
        self.width = 50
        self.buffered_logs = []
        self._lock = threading.Lock()
        
    def start(self):
        self.running = True
        try:
            sys.stdout.write("\033[?25l") # Hide cursor
            sys.stdout.flush()
        except Exception:
            pass
        self.thread = threading.Thread(target=self._animate, daemon=True)
        self.thread.start()
        
    def stop(self):
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join()
            self._clear_animation()
            try:
                sys.stdout.write("\033[?25h") # Show cursor
                sys.stdout.flush()
            except Exception:
                pass
            
            # Print any logs that were buffered
            with self._lock:
                for log_msg in self.buffered_logs:
                    sys.stdout.write(log_msg + "\n")
                self.buffered_logs.clear()
                
    def add_log(self, msg):
        with self._lock:
            if self.running:
                self.buffered_logs.append(msg)
            else:
                sys.stdout.write(msg + "\n")

    def _clear_animation(self):
        lines_to_clear = self.height + 2
        try:
            sys.stdout.write("\r" + "\033[A" * lines_to_clear + "\033[J")
            sys.stdout.flush()
        except Exception:
            pass

    def _animate(self):
        # Initial space allocation
        try:
            sys.stdout.write("\n" * (self.height + 2))
            sys.stdout.flush()
        except Exception:
            pass
        
        angle = 0.0
        cx, cy = self.width // 2, self.height // 2
        
        C_SUN = "\033[38;2;255;189;46m"
        C_MERCURY = "\033[38;2;170;170;170m"
        C_VENUS = "\033[38;2;255;223;128m"
        C_EARTH = "\033[38;2;88;166;255m"
        C_MARS = "\033[38;2;255;85;85m"
        C_JUPITER = "\033[38;2;240;196;140m"
        C_SATURN = "\033[38;2;218;165;32m"
        C_ORBIT = "\033[38;2;45;45;45m"
        R_RESET = "\033[0m"
        
        planets = [
            (".", 1.8, 1.8, C_MERCURY),
            ("o", 3.0, 1.3, C_VENUS),
            ("O", 4.5, 0.9, C_EARTH),
            ("x", 6.0, 0.7, C_MARS),
            ("@", 7.8, 0.4, C_JUPITER),
            ("⊚", 9.8, 0.2, C_SATURN)
        ]
        
        x_scale = 2.0
        
        while self.running:
            grid = [[" " for _ in range(self.width)] for _ in range(self.height)]
            
            # Draw orbits
            for _, r, _, _ in planets:
                for a_deg in range(0, 360, 5):
                    rad = math.radians(a_deg)
                    ox = int(cx + r * math.cos(rad) * x_scale)
                    oy = int(cy + r * math.sin(rad))
                    if 0 <= ox < self.width and 0 <= oy < self.height:
                        grid[oy][ox] = C_ORBIT + "." + R_RESET

            # Draw Sun
            if 0 <= cx < self.width and 0 <= cy < self.height:
                grid[cy][cx] = C_SUN + "☼" + R_RESET
                
            # Draw planets
            for char, r, speed, color in planets:
                theta = angle * speed
                px = int(cx + r * math.cos(theta) * x_scale)
                py = int(cy + r * math.sin(theta))
                if 0 <= px < self.width and 0 <= py < self.height:
                    grid[py][px] = color + char + R_RESET
                    
            output = []
            output.append(f"\033[36m  ◈ {self.message}\033[0m")
            for row in grid:
                output.append("   " + "".join(row))
            dots = "." * (int(angle * 2.5) % 4)
            output.append(f"   \033[90mCalculating orbits{dots:<3}\033[0m")
            
            frame_str = "\n".join(output) + "\n"
            
            try:
                # Move cursor and print frame in a single write operation to prevent tearing/flickering
                sys.stdout.write("\033[A" * (self.height + 2) + frame_str)
                sys.stdout.flush()
            except Exception:
                pass
            
            angle += 0.05
            time.sleep(0.04)

class BufferHandler(logging.Handler):
    def __init__(self, animation):
        super().__init__()
        self.animation = animation
        
    def emit(self, record):
        try:
            msg = self.format(record)
            self.animation.add_log(msg)
        except Exception:
            self.handleError(record)

def parse_single_file(file_path):
    """
    Worker function to run CPU-bound tree-sitter AST parsing in parallel.
    Returns: (file_path, symbols, imports, calls, error_message)
    """
    try:
        result = extract_symbols(file_path)
        # Unpack safely
        if isinstance(result, tuple) and len(result) == 3:
            symbols, imports, calls = result
        else:
            symbols = result
            imports = []
            calls = []
        return file_path, symbols, imports, calls, None
    except Exception as e:
        import traceback
        return file_path, [], [], [], f"{e}\n{traceback.format_exc()}"

def start_docker_services():
    import subprocess
    import os
    
    logger.info("🐳 Checking Docker services...")
    package_dir = os.path.dirname(os.path.abspath(__file__))
    compose_path = os.path.join(package_dir, "docker-compose.yml")
    
    if not os.path.exists(compose_path):
        # Fallback to parent directory if running in dev mode
        parent_dir = os.path.dirname(package_dir)
        compose_path = os.path.join(parent_dir, "docker-compose.yml")
        
    if not os.path.exists(compose_path):
        logger.warning("⚠️ Warning: docker-compose.yml not found. Skipping automatic Docker startup.")
        return
        
    cmd = ["docker", "compose", "-f", compose_path, "up", "-d"]
    try:
        logger.info(f"🚀 Running: {' '.join(cmd)}")
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info("✅ Docker services started successfully.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        cmd_fallback = ["docker-compose", "-f", compose_path, "up", "-d"]
        try:
            logger.info(f"🚀 Running fallback: {' '.join(cmd_fallback)}")
            subprocess.run(cmd_fallback, capture_output=True, text=True, check=True)
            logger.info("✅ Docker services started successfully (using docker-compose).")
        except Exception as ex:
            logger.error(f"❌ Failed to run docker compose: {ex}")
            logger.warning("⚠️ Please ensure Docker Desktop is running and docker compose is installed.")

def wait_for_postgres_and_schema(timeout=30):
    import time
    from n3mo.core.database import get_connection, release_connection
    
    logger.info("⏳ Waiting for PostgreSQL database and schema to be ready...")
    start_time = time.time()
    while time.time() - start_time < timeout:
        conn = None
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'projects'")
                exists = cur.fetchone()
                if not exists:
                    package_dir = os.path.dirname(os.path.abspath(__file__))
                    logger.info("🗄️ Database empty. Initializing schema from db/schema.sql...")
                    schema_path = os.path.join(package_dir, "db", "schema.sql")
                    if not os.path.exists(schema_path):
                        # Fallback for dev mode
                        schema_path = os.path.join(os.path.dirname(package_dir), "db", "schema.sql")
                    if os.path.exists(schema_path):
                        with open(schema_path, "r", encoding="utf-8") as f:
                            schema_sql = f.read()
                        cur.execute(schema_sql)
                        conn.commit()
                        logger.info("✅ Database schema initialized successfully.")

                cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'projects'")
                exists = cur.fetchone()
                if exists:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS files (
                            project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
                            file_path TEXT NOT NULL,
                            sha256 TEXT NOT NULL,
                            PRIMARY KEY (project_id, file_path)
                        )
                    """)
                    conn.commit()
                    logger.info("✅ PostgreSQL database and schema are ready!")
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
            
    logger.error("❌ Timeout waiting for PostgreSQL/schema to start. Please check container health.")
    return False

def clear_all_data(exclude_url=None):
    from n3mo.core.database import get_connection, release_connection
    logger.info("🧹 Cleaning database of other projects to ensure no residues...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            if exclude_url:
                cur.execute("DELETE FROM projects WHERE repo_url != %s", (exclude_url,))
            else:
                cur.execute("DELETE FROM projects")
            conn.commit()
            logger.info("✅ Database cleaned successfully.")
    except Exception as e:
        logger.warning(f"⚠️ Warning: Could not clear database: {e}")
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
        logger.warning(f"⚠️ Warning: Could not calculate hash for {file_path}: {e}")
        return ""


def run_indexer_for_path(target_dir):
    setup_logging(target_dir)

    # Configure Windows Console / UTF-8
    if os.name == 'nt':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            hStdOut = kernel32.GetStdHandle(-11) # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(hStdOut, ctypes.byref(mode)):
                kernel32.SetConsoleMode(hStdOut, mode.value | 0x0004)
        except Exception:
            pass

    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    # Redirect console handlers to buffer during animation
    console_handlers = []
    for h in list(logger.handlers):
        if isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler):
            console_handlers.append(h)
            logger.removeHandler(h)
            
    is_ci = os.environ.get("GITHUB_ACTIONS") == "true"
    
    if not is_ci:
        animation = SolarSystemAnimation("Indexing repository...")
        buffer_handler = BufferHandler(animation)
        buffer_handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(buffer_handler)
        animation.start()

    try:
        logger.info(f"\n🌊 N3MO: Starting Analysis on {target_dir}...")

        if not os.path.exists(target_dir):
            logger.error(f"❌ Error: Target directory '{target_dir}' does not exist.")
            return False, f"Error: Target directory '{target_dir}' does not exist."

        # Automatically start Docker container and wait for Postgres readiness
        if not is_ci:
            start_docker_services()
            if not wait_for_postgres_and_schema():
                logger.error("❌ Aborting indexing due to database unreadiness.")
                return False, "Aborting indexing due to database unreadiness."
        else:
            # In CI, just check if the database is reachable
            try:
                from n3mo.core.database import get_connection, release_connection
                conn = get_connection()
                release_connection(conn)
            except Exception as e:
                logger.error(f"❌ Aborting indexing due to database connection error: {e}")
                return False, f"Database connection error: {e}"

        # Clear previous residues from OTHER repositories
        clear_all_data(exclude_url=target_dir)

        # Setup Project
        project_name = os.path.basename(target_dir)
        try:
            project_id = ensure_project(project_name, repo_url=target_dir)
            logger.info(f"✅ Project ID: {project_id}")
        except Exception as e:
            logger.error(f"❌ Database Connection Failed: {e}")
            return False, f"Database Connection Failed: {e}"

        # Fetch existing file hashes
        existing_hashes = get_file_hashes(project_id)

        # Crawl
        logger.info("🕷️  Crawling files...")
        files = crawl_directory(target_dir)
        logger.info(f"   Found {len(files)} source files.")

        # Detect deleted files (in database hash list, but not present in current crawl list)
        current_rel_paths = {os.path.relpath(f, target_dir) for f in files}
        deleted_files = [path for path in existing_hashes if path not in current_rel_paths]

        if deleted_files:
            logger.info(f"🗑️  Pruning {len(deleted_files)} deleted files from index...")
            for path in deleted_files:
                try:
                    delete_file_index(project_id, path)
                except Exception as e:
                    logger.warning(f"   Warning: Failed to delete index for {path}: {e}")

        # Identify files to index (new / modified)
        files_to_index = []
        skipped_count = 0
        for file_path in files:
            rel_path = os.path.relpath(file_path, target_dir)
            current_hash = calculate_sha256(file_path)
            
            # Incremental check
            if rel_path in existing_hashes and existing_hashes[rel_path] == current_hash:
                skipped_count += 1
                continue
                
            files_to_index.append((file_path, rel_path, current_hash))

        symbol_count = 0
        call_count = 0
        indexed_count = 0

        if files_to_index:
            logger.info(f"🧠 Extracting symbols in parallel using ThreadPool ({min(len(files_to_index), os.cpu_count() or 2)} workers)...")
            
            from concurrent.futures import ThreadPoolExecutor
            max_workers = min(len(files_to_index), os.cpu_count() or 2)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit only the files that need parsing
                future_to_file = {
                    executor.submit(parse_single_file, fpath): (fpath, rpath, chash)
                    for fpath, rpath, chash in files_to_index
                }
                
                for future in as_completed(future_to_file):
                    fpath, rpath, chash = future_to_file[future]
                    try:
                        fpath_ret, symbols, imports, calls, error = future.result()
                        if error:
                            logger.warning(f"Warning: failed to parse {rpath}: {error}")
                            continue
                            
                        # If a file has no impact (0 symbols, 0 imports, 0 calls), delete it from DB and skip indexing
                        if len(symbols) == 0 and len(imports) == 0 and len(calls) == 0:
                            delete_file_index(project_id, rpath)
                            logger.info(f"   Skipped no-impact file: {rpath}")
                            continue

                        # Save results to DB on main thread (safe and keeps DB code simple)
                        replace_file_index(
                            project_id,
                            rpath,
                            symbols,
                            imports,
                            calls,
                        )
                        
                        if chash:
                            upsert_file_hash(project_id, rpath, chash)

                        symbol_count += len(symbols)
                        call_count += len(calls)
                        indexed_count += 1
                    except Exception as exc:
                        logger.warning(f"Warning: failed to index {rpath}: {exc}")

        # --- RUN THE LINKER ---
        logger.info("🔗 resolving imports...")
        resolve_import_links(project_id)
        logger.info("🔗 resolving calls...")
        resolve_call_links(project_id)

        logger.info("-" * 30)
        logger.info("✅ Indexing Complete!")
        logger.info(f"📊 Processed: {len(files)} files")
        logger.info(f"   Indexed:   {indexed_count} files (new/modified)")
        logger.info(f"   Skipped:   {skipped_count} files (unchanged)")
        if indexed_count > 0:
            logger.info(f"📚 Symbols:   {symbol_count} (newly indexed)")
            logger.info(f"📞 Calls:     {call_count} (newly indexed)")
        logger.info("-" * 30)
        
        summary = (
            f"Success: Indexed workspace at '{target_dir}'.\n"
            f"Processed: {len(files)} files\n"
            f"Indexed:   {indexed_count} files (new/modified)\n"
            f"Skipped:   {skipped_count} files (unchanged)\n"
            f"Symbols:   {symbol_count} (newly indexed)\n"
            f"Calls:     {call_count} (newly indexed)"
        )
        return True, summary
    finally:
        # Stop animation and restore original console logger handlers
        if 'animation' in locals():
            try:
                animation.stop()
            except Exception:
                pass
        if 'buffer_handler' in locals() and not is_ci:
            try:
                logger.removeHandler(buffer_handler)
            except Exception:
                pass
        if 'console_handlers' in locals():
            for h in console_handlers:
                try:
                    logger.addHandler(h)
                except Exception:
                    pass
        # Shutdown logger handlers to release file handles (important on Windows)
        for handler in list(logger.handlers):
            try:
                handler.close()
                logger.removeHandler(handler)
            except Exception:
                pass

def main():
    target_dir = os.getenv("TARGET_CODE_DIR", os.getcwd())
    run_indexer_for_path(target_dir)


if __name__ == "__main__":
    main()
