---
name: "N3MO Code Intelligence"
description: "Use N3MO's MCP tools to search symbols, find dependencies, and check blast radius. This skill enforces using MCP over CLI commands."
---

# N3MO Code Intelligence Skill

You have access to N3MO, a symbol-centric code intelligence layer via Model Context Protocol (MCP) tools.
You MUST use these MCP tools to navigate and understand the codebase rather than running `n3mo` CLI commands in the terminal (which output human-readable GUI artifacts).

## Available MCP Tools

When working in this repository, you have access to the following tools via the `n3mo` MCP server:
- `n3mo_index`: Ingests and indexes the codebase.
- `n3mo_search_symbol`: Locates the definition of a symbol across the workspace (file path, line number).
- `n3mo_get_dependencies`: Finds all external symbols that a given symbol calls (the forward-dependency graph).
- `n3mo_get_file_symbols`: Lists all classes and functions defined inside a specific file.
- `n3mo_get_blast_radius`: Traces the transitive impact/call graph of a code symbol (who calls this symbol).

## Operational Rules

1. **Strictly use MCP Tools**: DO NOT run CLI commands like `n3mo impact` or `n3mo index` in the terminal. Always use the MCP tools provided above, as they return clean, structured context optimized for LLMs.
2. **Bootstrap Indexing**: If you receive a "No index found" error from any of the tools, run `n3mo_index` to crawl and ingest the workspace folder structure first.
3. **Impact Check Before Editing**: Before you modify, refactor, or delete any class, method, or function in the workspace, you MUST first run the `n3mo_get_blast_radius` tool on the target symbol to trace its downstream callers and prevent regressions.
4. **Context-Aware Decisions**: Analyze the returned data. If a symbol has transitive callers (especially deep nested call chains or high blast radius counts):
   - Notify the user about the impacted components and their respective file paths/line numbers.
   - Refactor calling signatures safely or adapt callers to accommodate the changes.
5. **Explore Dependencies**: When trying to understand how a complex function works, use `n3mo_get_dependencies` to see what sub-components it relies on.
