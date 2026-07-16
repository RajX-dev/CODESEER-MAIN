
mcp_path = r"c:\Users\Raj shekhar\Documents\raj\project\main project\n3mo\n3mo\mcp_server.py"

with open(mcp_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add schemas to list_tools
schema_addition = """            ),
            types.Tool(
                name="n3mo_search_symbol",
                description="Search the indexed codebase for the exact location and definition of a symbol (class or function).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol_name": {
                            "type": "string",
                            "description": "Name of the function or class to search for."
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Absolute path to workspace directory (default: current directory)."
                        }
                    },
                    "required": ["symbol_name"]
                }
            ),
            types.Tool(
                name="n3mo_get_dependencies",
                description="Find all external symbols that a given symbol calls (the forward-dependency graph).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol_name": {
                            "type": "string",
                            "description": "Name of the function or class to inspect."
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Absolute path to workspace directory (default: current directory)."
                        }
                    },
                    "required": ["symbol_name"]
                }
            ),
            types.Tool(
                name="n3mo_get_file_symbols",
                description="List all symbols (classes/functions) defined inside a specific file.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "Absolute path to the file to inspect (or a substring match)."
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Absolute path to workspace directory (default: current directory)."
                        }
                    },
                    "required": ["file_path"]
                }
            )"""

content = content.replace("            )\n        ]", schema_addition + "\n        ]")

# Add db helper
db_helper = """
        def get_db_conn():
            from n3mo.core.database import get_connection
            try:
                return get_connection()
            except Exception as e:
                try:
                    from n3mo.core.run_indexer import start_docker_services, wait_for_postgres_and_schema
                    start_docker_services()
                    if wait_for_postgres_and_schema(timeout=15):
                        return get_connection()
                    else:
                        raise e
                except Exception as ex:
                    raise Exception(f"Database Connection Failed: {ex}. Please verify that Docker Desktop is running and the PostgreSQL container is started.")

        def get_project_id(cur, project_path):
            cur.execute("SELECT id FROM projects WHERE repo_url = %s", (project_path,))
            proj = cur.fetchone()
            if not proj:
                project_name = os.path.basename(project_path)
                cur.execute("SELECT id FROM projects WHERE name = %s", (project_name,))
                proj = cur.fetchone()
            return proj[0] if proj else None
"""

content = content.replace('        if name == "n3mo_index":', db_helper + '\n        if name == "n3mo_index":')


# Replace the DB connection logic in blast radius with the helper
blast_radius_old_db_logic = """            from n3mo.core.database import get_connection, release_connection
            conn = None
            try:
                conn = get_connection()
            except Exception as e:
                try:
                    from n3mo.core.run_indexer import start_docker_services, wait_for_postgres_and_schema
                    start_docker_services()
                    if wait_for_postgres_and_schema(timeout=15):
                        conn = get_connection()
                    else:
                        raise e
                except Exception as ex:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: Database Connection Failed: {ex}\\n"
                                 f"Please verify that Docker Desktop is running and the PostgreSQL container is started."
                        )
                    ]

            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM projects WHERE repo_url = %s", (project_path,))
                    proj = cur.fetchone()
                    if not proj:
                        # Fallback: check by project name match
                        project_name = os.path.basename(project_path)
                        cur.execute("SELECT id FROM projects WHERE name = %s", (project_name,))
                        proj = cur.fetchone()
                        if not proj:
                            return [
                                types.TextContent(
                                    type="text",
                                    text=f"Error: No index found for '{project_path}'. Run the indexer tool first."
                                )
                            ]
                    project_id = proj[0]"""

blast_radius_new_db_logic = """            from n3mo.core.database import release_connection
            conn = None
            try:
                conn = get_db_conn()
            except Exception as ex:
                return [types.TextContent(type="text", text=f"Error: {ex}")]

            try:
                with conn.cursor() as cur:
                    project_id = get_project_id(cur, project_path)
                    if not project_id:
                        return [types.TextContent(type="text", text=f"Error: No index found for '{project_path}'. Run the indexer tool first.")]"""

content = content.replace(blast_radius_old_db_logic, blast_radius_new_db_logic)


# Add the new tools execution logic
new_tools_logic = """
        elif name == "n3mo_search_symbol":
            symbol_name = arguments.get("symbol_name")
            project_path = arguments.get("project_path") or os.getenv("TARGET_CODE_DIR") or os.getcwd()
            from n3mo.core.database import release_connection
            conn = None
            try:
                conn = get_db_conn()
            except Exception as ex:
                return [types.TextContent(type="text", text=f"Error: {ex}")]
            try:
                with conn.cursor() as cur:
                    project_id = get_project_id(cur, project_path)
                    if not project_id:
                        return [types.TextContent(type="text", text=f"Error: No index found for '{project_path}'. Run the indexer tool first.")]
                    
                    cur.execute(
                        "SELECT name, file_path, kind, signature, start_line FROM symbols WHERE name = %s AND project_id = %s",
                        (symbol_name, project_id)
                    )
                    results = cur.fetchall()
                    if not results:
                        return [types.TextContent(type="text", text=f"Symbol '{symbol_name}' not found.")]
                    
                    out = [f"Found {len(results)} definitions for '{symbol_name}':"]
                    for name, file_path, kind, sig, line in results:
                        out.append(f"- {kind} {name} at {file_path}:{line}")
                        if sig:
                            out.append(f"  Signature: {sig}")
                    return [types.TextContent(type="text", text="\\n".join(out))]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error searching symbol: {e}")]
            finally:
                if conn:
                    release_connection(conn)

        elif name == "n3mo_get_dependencies":
            symbol_name = arguments.get("symbol_name")
            project_path = arguments.get("project_path") or os.getenv("TARGET_CODE_DIR") or os.getcwd()
            from n3mo.core.database import release_connection
            conn = None
            try:
                conn = get_db_conn()
            except Exception as ex:
                return [types.TextContent(type="text", text=f"Error: {ex}")]
            try:
                with conn.cursor() as cur:
                    project_id = get_project_id(cur, project_path)
                    if not project_id:
                        return [types.TextContent(type="text", text=f"Error: No index found for '{project_path}'. Run the indexer tool first.")]
                    
                    cur.execute(
                        "SELECT id, file_path, start_line FROM symbols WHERE name = %s AND project_id = %s LIMIT 1",
                        (symbol_name, project_id)
                    )
                    target = cur.fetchone()
                    if not target:
                        return [types.TextContent(type="text", text=f"Symbol '{symbol_name}' not found.")]
                    target_id, target_file, target_line = target

                    query = '''
                    SELECT c.call_name, c.line_number, s.file_path, s.name, s.kind
                    FROM calls c
                    LEFT JOIN symbols s ON c.resolved_symbol_id = s.id
                    WHERE c.source_symbol_id = %s
                    ORDER BY c.line_number ASC
                    '''
                    cur.execute(query, (target_id,))
                    results = cur.fetchall()
                    
                    if not results:
                        return [types.TextContent(type="text", text=f"'{symbol_name}' makes no external calls (or none were resolved).")]
                    
                    out = [f"Dependencies called by '{symbol_name}' ({target_file}:{target_line}):"]
                    for call_name, line, resolved_file, resolved_name, resolved_kind in results:
                        if resolved_name:
                            out.append(f"- Line {line}: Calls {resolved_kind} '{resolved_name}' (resolved to {resolved_file})")
                        else:
                            out.append(f"- Line {line}: Calls '{call_name}' (unresolved)")
                    return [types.TextContent(type="text", text="\\n".join(out))]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error getting dependencies: {e}")]
            finally:
                if conn:
                    release_connection(conn)

        elif name == "n3mo_get_file_symbols":
            file_path = arguments.get("file_path")
            project_path = arguments.get("project_path") or os.getenv("TARGET_CODE_DIR") or os.getcwd()
            from n3mo.core.database import release_connection
            conn = None
            try:
                conn = get_db_conn()
            except Exception as ex:
                return [types.TextContent(type="text", text=f"Error: {ex}")]
            try:
                with conn.cursor() as cur:
                    project_id = get_project_id(cur, project_path)
                    if not project_id:
                        return [types.TextContent(type="text", text=f"Error: No index found for '{project_path}'. Run the indexer tool first.")]
                    
                    cur.execute(
                        "SELECT name, kind, signature, start_line, end_line FROM symbols WHERE file_path LIKE %s AND project_id = %s ORDER BY start_line ASC",
                        ('%' + file_path + '%', project_id)
                    )
                    results = cur.fetchall()
                    
                    if not results:
                        return [types.TextContent(type="text", text=f"No symbols found in file matching '{file_path}'.")]
                    
                    out = [f"Symbols defined in '{file_path}':"]
                    for name, kind, sig, start, end in results:
                        line_info = f"L{start}-L{end}" if end else f"L{start}"
                        out.append(f"- [{line_info}] {kind} {name}")
                        if sig:
                            out.append(f"  {sig}")
                    return [types.TextContent(type="text", text="\\n".join(out))]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error getting file symbols: {e}")]
            finally:
                if conn:
                    release_connection(conn)
"""

content = content.replace("        raise ValueError(f\"Unknown tool: {name}\")", new_tools_logic + '\n        raise ValueError(f"Unknown tool: {name}")')

with open(mcp_path, "w", encoding="utf-8") as f:
    f.write(content)
print("mcp_server.py patched successfully!")
