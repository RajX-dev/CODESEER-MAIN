# Copyright (C) 2026 Raj shekhar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import sys
import os
import argparse
from n3mo.database import get_connection
from n3mo.graph_visualizer import generate_solar_graph_html

from typing import Any

# Try to import the indexer logic
run_indexer_logic: Any = None
try:
    from n3mo.run_indexer import main as run_indexer_logic_impl
    run_indexer_logic = run_indexer_logic_impl
except ImportError:
    pass

# Dummy comment to trigger webhook impact analysis
# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def get_code_context(file_path, line_number, context=2):
    if not os.path.exists(file_path):
        return []
    start = max(1, line_number - context)
    end = line_number + context
    results = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for current_line_num, content in enumerate(f, 1):
                if current_line_num >= start and current_line_num <= end:
                    results.append((current_line_num, content.rstrip()))
                if current_line_num > end:
                    break
    except Exception:
        return []
    return results

# ANSI color codes
R  = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"
RED  = "\033[38;2;255;85;85m"
AMBER= "\033[38;2;255;189;46m"
BLUE = "\033[38;2;88;166;255m"
CYAN = "\033[38;2;79;212;190m"
GRAY = "\033[38;2;110;118;129m"
WHITE= "\033[38;2;230;237;243m"
BG_DARK = "\033[48;2;13;17;23m"

def print_ascii_tree(results, target_name):
    W = 64
    print()
    print(f"{BG_DARK}{CYAN}{BOLD}  ◈ IMPACT ANALYSIS  {R}")
    print(f"{GRAY}  {'─' * W}{R}")
    print(f"  {WHITE}{BOLD}Target:{R}  {AMBER}{BOLD}{target_name}{R}")
    print(f"{GRAY}  {'─' * W}{R}")

    sorted_results = sorted(results, key=lambda x: (x[3], x[1]))

    direct = [(s, p, line, d, t) for s, p, line, d, t in sorted_results if d == 1]
    ripple = [(s, p, line, d, t) for s, p, line, d, t in sorted_results if d > 1]

    if direct:
        print(f"\n  {RED}{BOLD}◉ Direct Callers{R}  {GRAY}({len(set(r[0] for r in direct))} symbols){R}\n")
        seen_direct = set()
        for source, path, line, depth, target in direct:
            if source in seen_direct:
                continue
            seen_direct.add(source)
            short_path = os.path.basename(path)
            print(f"  {RED}▸{R} {WHITE}{BOLD}{source:<28}{R} {GRAY}{short_path}:{line}{R}")

    if ripple:
        print(f"\n  {BLUE}{BOLD}◎ Ripple Effects{R}  {GRAY}({len(set(r[0] for r in ripple))} symbols){R}\n")
        seen_ripple = set()
        for source, path, line, depth, target in ripple:
            key = (source, path, line)
            if key in seen_ripple:
                continue
            seen_ripple.add(key)
            short_path = os.path.basename(path)
            indent = "    " * (depth - 1)
            print(f"  {BLUE}{indent}╰─▸{R} {CYAN}{source:<26}{R} {GRAY}{short_path}:{line}{R}")

    total = len(set((r[0], r[1], r[2]) for r in sorted_results))
    print(f"\n{GRAY}  {'─' * W}{R}")
    print(f"  {DIM}Total impacted: {WHITE}{total} references{R}  {GRAY}│  depth ≤ {max(r[3] for r in sorted_results)}{R}\n")



# ==========================================
# 🚀 COMMAND: IMPACT
# ==========================================

def cmd_impact(args):
    W = 64
    print()
    print(f"{BG_DARK}{CYAN}{BOLD}  N3MO  {R}{GRAY}  ◈  impact tracker{R}")
    print(f"{GRAY}  {'─' * W}{R}")

    conn = get_connection()
    symbol_name = args.symbol
    file_filter = args.file if hasattr(args, 'file') else None
    filename = None
    try:
        with conn.cursor() as cur:
            target_dir = os.getenv("TARGET_CODE_DIR", os.getcwd())
            cur.execute("SELECT id FROM projects WHERE repo_url = %s", (target_dir,))
            proj = cur.fetchone()
            if not proj:
                print(f"\n  {RED}✗{R} No index found for this directory. Run `n3mo index` first.\n")
                return
            project_id = proj[0]

            if file_filter:
                cur.execute(
                    """
                    SELECT s.id, s.name, s.file_path, s.start_line 
                    FROM symbols s 
                    LEFT JOIN (SELECT resolved_symbol_id, COUNT(*) as call_count FROM calls GROUP BY resolved_symbol_id) c 
                      ON s.id = c.resolved_symbol_id 
                    WHERE s.name = %s AND s.project_id = %s AND s.file_path LIKE %s 
                    ORDER BY COALESCE(c.call_count, 0) DESC, s.start_line ASC 
                    LIMIT 1
                    """,
                    (symbol_name, project_id, f"%{file_filter}%")
                )
            else:
                cur.execute(
                    """
                    SELECT s.id, s.name, s.file_path, s.start_line 
                    FROM symbols s 
                    LEFT JOIN (SELECT resolved_symbol_id, COUNT(*) as call_count FROM calls GROUP BY resolved_symbol_id) c 
                      ON s.id = c.resolved_symbol_id 
                    WHERE s.name = %s AND s.project_id = %s 
                    ORDER BY COALESCE(c.call_count, 0) DESC, s.start_line ASC 
                    LIMIT 1
                    """,
                    (symbol_name, project_id)
                )
            target = cur.fetchone()
            if not target:
                print(f"\n  {RED}✗{R} Symbol {WHITE}'{symbol_name}'{R} not found in index.\n")
                return
            target_id, real_name, target_file, target_start_line = target
            print(f"\n  {DIM}Analyzing{R}  {AMBER}{BOLD}{real_name}{R}")
            print(f"  {GRAY}Location: {DIM}{target_file}{R}\n")

            query = """
            WITH RECURSIVE impact_chain AS (
                SELECT s.name AS source, s.file_path, c.line_number, 1 AS depth, target_sym.name AS target, c.source_symbol_id AS source_id,
                       ARRAY[c.source_symbol_id] AS path,
                       FALSE AS cycle
                FROM calls c
                JOIN symbols s ON c.source_symbol_id = s.id
                JOIN symbols target_sym ON c.resolved_symbol_id = target_sym.id
                WHERE c.resolved_symbol_id = %s
                UNION ALL
                SELECT s.name, s.file_path, c.line_number, ic.depth + 1, ic.source, c.source_symbol_id,
                       ic.path || c.source_symbol_id,
                       c.source_symbol_id = ANY(ic.path)
                FROM impact_chain ic
                JOIN calls c ON c.resolved_symbol_id = ic.source_id
                JOIN symbols s ON c.source_symbol_id = s.id
                WHERE ic.depth < %s + 1 AND NOT ic.cycle
            )
            SELECT DISTINCT source, file_path, line_number, depth, target
            FROM impact_chain WHERE NOT cycle ORDER BY depth ASC, file_path;
            """
            cur.execute(query, (target_id, args.depth))
            results = cur.fetchall()
            if not results:
                print(f"  {CYAN}✓{R}  Safe to change — no dependencies found.\n")
                return
            print_ascii_tree(results, real_name)

            if args.graph:
                # Auto-detect terminal directory so VS Code links work perfectly
                base_dir = args.root or os.getcwd()

                target_full_path = f"{base_dir}/{target_file}".replace("\\", "/") if target_file else ""
                target_start_line = target_start_line or 1
                target_code_ctx = get_code_context(target_full_path, target_start_line)

                nodes_map = {real_name: {"group": 0, "path": target_full_path, "line": target_start_line, "code_context": target_code_ctx}}
                edges = set()

                for source, path, line, depth, target_node in results:
                    s_group = depth
                    t_group = max(depth - 1, 0)
                    if target_node == real_name:
                        t_group = 0

                    full_path = ""
                    if path:
                        full_path = f"{base_dir}/{path}".replace("\\", "/")

                    code_ctx = get_code_context(full_path, line)

                    if source not in nodes_map or s_group < nodes_map[source]["group"]:
                        nodes_map[source] = {"group": s_group, "path": full_path, "line": line, "code_context": code_ctx}
                    if target_node not in nodes_map or t_group < nodes_map[target_node]["group"]:
                        nodes_map[target_node] = {"group": t_group, "path": full_path, "line": line, "code_context": code_ctx}
                    edges.add((source, target_node))

                nodes_set = list(nodes_map.items())
                filename = generate_solar_graph_html(nodes_set, edges, real_name, args.depth)
                abs_filename = os.path.abspath(filename)
                serve_dir = os.path.dirname(abs_filename)
                serve_file = os.path.basename(abs_filename)
                url = f"http://127.0.0.1:8080/{serve_file}"

                print(f"  {CYAN}◈{R}  Graph ready")
                print(f"  {BOLD}{WHITE}Server:{R}  {BLUE}\033[4m{url}\033[0m{R}")
                print(f"  {CYAN}◈{R}  Opening browser automatically... Press Ctrl+C to stop server")

                import subprocess
                import threading
                import webbrowser

                # Bind to 127.0.0.1 to avoid Windows Firewall popups
                server = subprocess.Popen(
                    ["python", "-m", "http.server", "8080", "--bind", "127.0.0.1"],
                    cwd=serve_dir
                )

                # Wait 1.5s for the server to boot, then pop the browser
                threading.Timer(1.5, lambda: webbrowser.open(url)).start()

                try:
                    server.wait()
                except KeyboardInterrupt:
                    server.terminate()
                    print(f"\n  {CYAN}◈{R}  Server stopped.")

    except KeyboardInterrupt:
        print(f"\n  {GRAY}Shutting down…{R}\n")
    except Exception as e:
        print(f"\n  {RED}✗  Error:{R} {e}\n")
    finally:
        if conn:
            conn.close()
        # Keep the file so the server can actually serve it!
        # if filename and os.path.exists(filename):
        #     os.remove(filename)


def cmd_clean(args):
    target_dir = os.getenv("TARGET_CODE_DIR", os.getcwd())
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM projects WHERE repo_url = %s RETURNING name", (target_dir,))
            row = cur.fetchone()
            conn.commit()
            if row:
                print(f"🗑️  Index cleared for project '{row[0]}'")
            else:
                print(f"⚠️  No index found for {target_dir}")
    finally:
        conn.close()


def cmd_setup(args):
    W = 64
    print()
    print(f"{BG_DARK}{CYAN}{BOLD}  N3MO  {R}{GRAY}  ◈  initial setup{R}")
    print(f"{GRAY}  {'─' * W}{R}")
    
    # 1. Check if Docker is installed
    import subprocess
    print("  🐳 Validating Docker installation...")
    try:
        res = subprocess.run(["docker", "--version"], capture_output=True, text=True, check=True)
        print(f"  {CYAN}✓{R} Docker is installed: {WHITE}{res.stdout.strip()}{R}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"\n  {RED}✗{R} {BOLD}Docker not found in system PATH.{R}")
        print("  N3MO requires Docker to run its PostgreSQL (graph storage) automatically.")
        print("\n  👉 Please download and install Docker Desktop:")
        print(f"     {BLUE}\033[4mhttps://www.docker.com/products/docker-desktop/\033[0m")
        print("  👉 Once installed, start Docker Desktop and run: n3mo setup\n")
        return

    # 2. Check if Docker Daemon is running
    try:
        subprocess.run(["docker", "info"], capture_output=True, text=True, check=True)
        print(f"  {CYAN}✓{R} Docker daemon is running.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"\n  {RED}✗{R} {BOLD}Docker daemon is not running.{R}")
        print("  Please make sure Docker Desktop is started and active.")
        print("  👉 Once started, run: n3mo setup\n")
        return

    # 3. Create .env if not present
    package_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(package_dir)
    env_path = os.path.join(project_root, ".env")
    env_example_path = os.path.join(project_root, ".env.example")
    
    if os.path.exists(env_example_path) and not os.path.exists(env_path):
        import shutil
        try:
            shutil.copy(env_example_path, env_path)
            print(f"  {CYAN}✓{R} Environment file .env created with default settings.")
        except Exception as e:
            print(f"  {AMBER}⚠️{R} Could not copy .env: {e}")

    # 4. Start Docker services
    from n3mo.run_indexer import start_docker_services, wait_for_postgres_and_schema
    print(f"  {CYAN}▸{R} Starting PostgreSQL container...")
    start_docker_services()
    
    # 5. Wait for DB and schema
    if wait_for_postgres_and_schema(timeout=25):
        print(f"{GRAY}  {'─' * W}{R}")
        print(f"  {CYAN}🎉{R} {BOLD}{WHITE}N3MO is fully set up and ready to analyze your repositories!{R}")
        print(f"{GRAY}  {'─' * W}{R}")
        print("  Next Steps:")
        print(f"  - Run {CYAN}n3mo index{R} in any project folder to map its dependencies.")
        print(f"  - Run {CYAN}n3mo impact <symbol_name>{R} to see the blast radius of changes.")
        print(f"  - Run {CYAN}n3mo mcp install{R} to register N3MO with Claude Desktop.")
        print()
    else:
        print(f"\n  {RED}✗{R} {BOLD}Setup failed: Database services timed out during boot.{R}")
        print("  Please run `docker ps` to verify container health.\n")


def cmd_mcp(args):
    mcp_cmd = args.mcp_command if hasattr(args, 'mcp_command') else None
    
    if mcp_cmd == "install":
        W = 64
        print()
        print(f"{BG_DARK}{CYAN}{BOLD}  N3MO  {R}{GRAY}  ◈  mcp client registration{R}")
        print(f"{GRAY}  {'─' * W}{R}")
        
        target_dir = args.target_dir or os.getcwd()
        target_dir = os.path.abspath(target_dir)
        import shutil
        import json
        
        # 1. Claude Desktop config path
        appdata = os.environ.get("APPDATA")
        if appdata:
            claude_config_path = os.path.join(appdata, "Claude", "claude_desktop_config.json")
            claude_dir = os.path.dirname(claude_config_path)
            os.makedirs(claude_dir, exist_ok=True)
            
            # Backup existing config if it exists
            if os.path.exists(claude_config_path):
                backup_path = claude_config_path + ".bak"
                try:
                    shutil.copy(claude_config_path, backup_path)
                    print(f"  {CYAN}✓{R} Backed up existing Claude config to: {os.path.basename(backup_path)}")
                except Exception as e:
                    print(f"  {AMBER}⚠️{R} Failed to create backup Claude config: {e}")
                    
            # Read or init config
            config = {"mcpServers": {}}
            if os.path.exists(claude_config_path):
                try:
                    with open(claude_config_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            config = json.loads(content)
                except Exception as e:
                    print(f"  {AMBER}⚠️{R} Failed to parse existing Claude config: {e}. Starting fresh.")
                    
            if "mcpServers" not in config:
                config["mcpServers"] = {}
                
            package_dir = os.path.dirname(os.path.abspath(__file__))
            
            # Configure n3mo server entry
            config["mcpServers"]["n3mo"] = {
                "command": sys.executable,
                "args": ["-m", "n3mo.mcp_server"],
                "cwd": os.path.dirname(package_dir),
                "env": {
                    "TARGET_CODE_DIR": target_dir
                }
            }
            
            try:
                with open(claude_config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, indent=2)
                print(f"  {CYAN}✓{R} Claude Desktop configuration updated successfully!")
            except Exception as e:
                print(f"  {RED}✗{R} Failed to write Claude configuration file: {e}")
        else:
            print(f"  {AMBER}⚠️{R} APPDATA environment variable not found. Skipping Claude Desktop setup.")

        # 2. Cursor config path
        user_home = os.path.expanduser("~")
        cursor_config_path = os.path.join(user_home, ".cursor", "mcp.json")
        cursor_dir = os.path.dirname(cursor_config_path)
        os.makedirs(cursor_dir, exist_ok=True)
        
        # Backup Cursor config if it exists
        if os.path.exists(cursor_config_path):
            backup_cursor_path = cursor_config_path + ".bak"
            try:
                shutil.copy(cursor_config_path, backup_cursor_path)
                print(f"  {CYAN}✓{R} Backed up existing Cursor config to: {os.path.basename(backup_cursor_path)}")
            except Exception as e:
                print(f"  {AMBER}⚠️{R} Failed to create backup Cursor config: {e}")
                
        # Read or init Cursor config
        cursor_config = {"mcpServers": {}}
        if os.path.exists(cursor_config_path):
            try:
                with open(cursor_config_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        cursor_config = json.loads(content)
            except Exception as e:
                print(f"  {AMBER}⚠️{R} Failed to parse existing Cursor config: {e}. Starting fresh.")
                
        if "mcpServers" not in cursor_config:
            cursor_config["mcpServers"] = {}
            
        # Configure n3mo server entry for Cursor
        cursor_config["mcpServers"]["n3mo"] = {
            "command": sys.executable,
            "args": ["-m", "n3mo.mcp_server"],
            "env": {
                "TARGET_CODE_DIR": target_dir
            }
        }
        
        try:
            with open(cursor_config_path, "w", encoding="utf-8") as f:
                json.dump(cursor_config, f, indent=2)
            print(f"  {CYAN}✓{R} Cursor configuration updated successfully!")
            print(f"  File location: {cursor_config_path}")
        except Exception as e:
            print(f"  {RED}✗{R} Failed to write Cursor configuration file: {e}")

        # 3. Print success details
        print(f"{GRAY}  {'─' * W}{R}")
        print(f"  {CYAN}🎉{R} {BOLD}{WHITE}N3MO MCP Registration Complete!{R}")
        print(f"{GRAY}  {'─' * W}{R}")
        print(f"  {BOLD}For Claude Desktop / Cursor:{R}")
        print("  - Restart the application or reload the window to apply the tools.")
        print("  - N3MO will now have tools to search and trace dependencies in:")
        print(f"    {WHITE}{target_dir}{R}")
        print()
        
    else:
        # Default subcommand: start the stdio server
        try:
            import asyncio
            from n3mo.mcp_server import main as mcp_main
            asyncio.run(mcp_main())
        except KeyboardInterrupt:
            print(f"\n  {CYAN}◈{R}  MCP Server stopped.")
        except Exception:
            import traceback
            print(f"\n  {RED}✗  Error running MCP server:{R}")
            traceback.print_exc()
            print()


def cmd_api(args):
    from n3mo.api_server import start_server
    print(f"🚀 Starting N3MO API Server on http://{args.host}:{args.port}...")
    start_server(host=args.host, port=args.port)


def cmd_hook(args):
    from n3mo.git_hooks import install_git_hook
    target_dir = args.target_dir or os.getenv("TARGET_CODE_DIR", os.getcwd())
    install_git_hook(target_dir)


def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(prog="n3mo")
    subparsers = parser.add_subparsers(dest='command')
    
    parser_api = subparsers.add_parser('api')
    parser_api.add_argument('--host', default="127.0.0.1", help="API bind host")
    parser_api.add_argument('--port', type=int, default=8000, help="API bind port")
    parser_api.set_defaults(func=cmd_api)

    parser_hook = subparsers.add_parser('git-hook')
    hook_subparsers = parser_hook.add_subparsers(dest='hook_command')
    parser_hook_install = hook_subparsers.add_parser('install')
    parser_hook_install.add_argument('--target-dir', help="Path to project directory (default: current directory)", default=None)
    parser_hook_install.set_defaults(func=cmd_hook)
    parser_hook.set_defaults(func=cmd_hook)

    parser_impact = subparsers.add_parser('impact')
    parser_impact.add_argument('symbol')
    parser_impact.add_argument('--graph', action='store_true')
    parser_impact.add_argument('--file', help="Filter by file path", default=None)
    parser_impact.add_argument('--depth', type=int, default=3, help="Blast radius depth (default: 3, max recommended: 5)")
    parser_impact.add_argument('--root', help="Absolute Windows path to project root for VS Code links", default="")
    parser_impact.set_defaults(func=cmd_impact)
    
    parser_index = subparsers.add_parser('index')
    parser_index.set_defaults(func=lambda args: run_indexer_logic())
    
    parser_clean = subparsers.add_parser('clean')
    parser_clean.set_defaults(func=cmd_clean)
    
    parser_setup = subparsers.add_parser('setup')
    parser_setup.set_defaults(func=cmd_setup)
    
    parser_mcp = subparsers.add_parser('mcp')
    mcp_subparsers = parser_mcp.add_subparsers(dest='mcp_command')
    parser_mcp_start = mcp_subparsers.add_parser('start')
    parser_mcp_start.set_defaults(func=cmd_mcp)
    parser_mcp_install = mcp_subparsers.add_parser('install')
    parser_mcp_install.add_argument('--target-dir', help="Absolute path to workspace directory (defaults to current dir)", default=None)
    parser_mcp_install.set_defaults(func=cmd_mcp)
    parser_mcp.set_defaults(func=cmd_mcp) # fallback if just `n3mo mcp` is typed
    
    args = parser.parse_args()
    if hasattr(args, 'func'):
        args.func(args)


if __name__ == '__main__':
    main()