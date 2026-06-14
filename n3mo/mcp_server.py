import sys
import logging
import os
from typing import List, Any

# Setup simple logger
logger = logging.getLogger("n3mo.mcp")

Server: Any = None
stdio_server: Any = None
types: Any = None
server: Any = None

try:
    from mcp.server import Server as MCPServer # type: ignore
    from mcp.server.stdio import stdio_server as MCPStdioServer # type: ignore
    import mcp.types as MCPTypes # type: ignore
    Server = MCPServer
    stdio_server = MCPStdioServer
    types = MCPTypes
except ImportError:
    logger.error("The 'mcp' SDK is not installed. Run 'pip install mcp' to use the MCP Server.")


# Define the N3MO MCP Server if library is installed
if Server is not None:
    server = Server("n3mo-server")

    @server.list_tools()
    async def handle_list_tools() -> List[types.Tool]:
        """
        List N3MO analysis tools available to the LLM agent.
        """
        return [
            types.Tool(
                name="n3mo_index",
                description="Trigger N3MO to crawl and index the active workspace folder.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {
                            "type": "string",
                            "description": "Absolute path to workspace directory."
                        }
                    },
                    "required": ["project_path"]
                }
            ),
            types.Tool(
                name="n3mo_get_blast_radius",
                description="Query the impact analysis / blast radius of a code symbol (class or function).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "symbol_name": {
                            "type": "string",
                            "description": "Name of the function or class to trace."
                        },
                        "depth": {
                            "type": "integer",
                            "description": "Traversal depth limit (default: 3).",
                            "default": 3
                        },
                        "project_path": {
                            "type": "string",
                            "description": "Absolute path to workspace directory (default: current directory)."
                        }
                    },
                    "required": ["symbol_name"]
                }
            )
        ]

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict) -> List[types.TextContent]:
        """
        Execute tool calls requested by the LLM agent.
        """
        if name == "n3mo_index":
            project_path = arguments.get("project_path") or os.getenv("TARGET_CODE_DIR") or os.getcwd()
            if not project_path:
                return [types.TextContent(type="text", text="Error: project_path is required.")]
            
            try:
                from n3mo.run_indexer import run_indexer_for_path
                success, message = run_indexer_for_path(project_path)
                return [types.TextContent(type="text", text=message)]
            except Exception as e:
                return [types.TextContent(type="text", text=f"Error indexing workspace: {e}")]

        elif name == "n3mo_get_blast_radius":
            symbol_name = arguments.get("symbol_name")
            depth = arguments.get("depth", 3)
            project_path = arguments.get("project_path") or os.getenv("TARGET_CODE_DIR") or os.getcwd()

            from n3mo.database import get_connection, release_connection
            conn = None
            try:
                conn = get_connection()
            except Exception as e:
                try:
                    from n3mo.run_indexer import start_docker_services, wait_for_postgres_and_schema
                    start_docker_services()
                    if wait_for_postgres_and_schema(timeout=15):
                        conn = get_connection()
                    else:
                        raise e
                except Exception as ex:
                    return [
                        types.TextContent(
                            type="text",
                            text=f"Error: Database Connection Failed: {ex}\n"
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
                    project_id = proj[0]

                    cur.execute(
                        "SELECT id, name, file_path, start_line FROM symbols WHERE name = %s AND project_id = %s LIMIT 1",
                        (symbol_name, project_id)
                    )
                    target = cur.fetchone()
                    if not target:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Symbol '{symbol_name}' not found in the index for this workspace."
                            )
                        ]
                    target_id, real_name, target_file, target_start_line = target

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
                    cur.execute(query, (target_id, depth))
                    results = cur.fetchall()

                    if not results:
                        return [
                            types.TextContent(
                                type="text",
                                text=f"Impact Analysis for '{real_name}' (located in {target_file}:{target_start_line}):\n"
                                     f"Safe to change - no callers found in the database."
                            )
                        ]

                    # Format the results
                    sorted_results = sorted(results, key=lambda x: (x[3], x[1]))
                    direct = [r for r in sorted_results if r[3] == 1]
                    ripple = [r for r in sorted_results if r[3] > 1]

                    output_lines = []
                    output_lines.append(f"◈ IMPACT ANALYSIS FOR: {real_name}")
                    output_lines.append(f"  Location: {target_file}:{target_start_line}")
                    output_lines.append(f"  Depth: <= {depth}")
                    output_lines.append("=" * 60)

                    if direct:
                        output_lines.append(f"\n◉ Direct Callers ({len(set(r[0] for r in direct))} symbols):")
                        seen_direct = set()
                        for source, path, line, d, t in direct:
                            if source in seen_direct:
                                continue
                            seen_direct.add(source)
                            output_lines.append(f"  ▸ {source:<28} {path}:{line}")

                    if ripple:
                        output_lines.append(f"\n◎ Ripple Effects ({len(set(r[0] for r in ripple))} symbols):")
                        seen_ripple = set()
                        for source, path, line, d, t in ripple:
                            key = (source, path, line)
                            if key in seen_ripple:
                                continue
                            seen_ripple.add(key)
                            indent = "    " * (d - 1)
                            output_lines.append(f"  {indent}╰─▸ {source:<26} {path}:{line}")

                    output_lines.append("=" * 60)
                    total_refs = len(set((r[0], r[1], r[2]) for r in sorted_results))
                    output_lines.append(f"Total impacted: {total_refs} references")

                    return [types.TextContent(type="text", text="\n".join(output_lines))]

            except Exception as e:
                return [types.TextContent(type="text", text=f"Error running impact analysis: {e}")]
            finally:
                if conn:
                    release_connection(conn)

        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server over stdio transport."""
    if Server is None or stdio_server is None:
        print("Error: MCP SDK not installed. Please run 'pip install mcp' first.", file=sys.stderr)
        sys.exit(1)

    if sys.stdin.isatty():
        print("\n\033[1;33m⚠️  N3MO MCP Server - Interactive Terminal Warning\033[0m", file=sys.stderr)
        print("----------------------------------------------------------------", file=sys.stderr)
        print("The MCP server runs over STDIO transport, which expects a JSON-RPC", file=sys.stderr)
        print("host (like Cursor or Claude Desktop) and cannot be run interactively.", file=sys.stderr)
        print("\nTo integrate with Cursor:", file=sys.stderr)
        print("  1. Open Cursor settings: Settings -> Models -> MCP", file=sys.stderr)
        print("  2. Add a new MCP server:", file=sys.stderr)
        print("     - Name: n3mo", file=sys.stderr)
        print("     - Type: command", file=sys.stderr)
        print(f"     - Command: {sys.executable} -m n3mo.mcp_server", file=sys.stderr)
        print("\nTo automatically register with Cursor and Claude Desktop, run:", file=sys.stderr)
        print("  \033[1;36mn3mo mcp install\033[0m\n", file=sys.stderr)
        sys.exit(1)

    logger.info("Starting N3MO MCP Server...")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
else:
    # Basic fallback module definition if imported
    server = None
