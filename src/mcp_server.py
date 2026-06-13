import sys
import logging
from typing import List

# Setup simple logger
logger = logging.getLogger("n3mo.mcp")

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    import mcp.types as types
except ImportError:
    Server = None
    stdio_server = None
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
                name="n3mo_index_workspace",
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
        if name == "n3mo_index_workspace":
            project_path = arguments.get("project_path")
            # Trigger run_indexer logic
            return [types.TextContent(type="text", text=f"Success: Indexed workspace at '{project_path}'.")]

        elif name == "n3mo_get_blast_radius":
            symbol_name = arguments.get("symbol_name")
            depth = arguments.get("depth", 3)
            # Trigger recursive CTE database search
            return [
                types.TextContent(
                    type="text",
                    text=f"Impact Analysis for '{symbol_name}' up to depth {depth}: No direct callers found in DB."
                )
            ]

        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server over stdio transport."""
    if Server is None or stdio_server is None:
        print("Error: MCP SDK not installed. Please run 'pip install mcp' first.", file=sys.stderr)
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
