---
sidebar_position: 4
title: AI Agents & MCP
---

# Model Context Protocol (MCP)

N3MO includes a native MCP server that exposes repository analysis and graph traversal tools to LLM agents (like Claude, Cursor, or Windsurf).

### Automatic Claude Desktop Setup
```bash
# Navigate to the workspace you want Claude to analyze, then run:
n3mo mcp install
```
This registers N3MO and sets up the paths automatically. Restart Claude Desktop and you're ready!

### Cursor Setup
1. Go to **Settings → Models → MCP**.
2. Click **+ Add New MCP Server**.
3. Set the configuration details:
   * **Name**: `n3mo`
   * **Type**: `command`
   * **Command**: `n3mo mcp start` (or `uvx n3mo mcp start` to run directly)
   * **Environment Variables**: `TARGET_CODE_DIR=/absolute/path/to/your/active/workspace`
4. Click Save, and Cursor will instantly be able to index and query your workspace blast radius.

### Available MCP Tools

| Tool | Description |
|:---|:---|
| `n3mo_index` | Ingests and indexes the codebase |
| `n3mo_search_symbol` | Locates the definition of a symbol across the workspace (file path, line number) |
| `n3mo_get_dependencies` | Finds all external symbols that a given symbol calls (forward-dependency graph) |
| `n3mo_get_file_symbols` | Lists all classes and functions defined inside a specific file |
| `n3mo_get_blast_radius` | Traces the transitive impact/call graph of a code symbol |
