# N3MO System Skill for Claude

Use this instruction profile to make Claude (or other LLM agents) aware of the **N3MO Code Intelligence Layer** and enforce using its Model Context Protocol (MCP) server instead of standard CLI tools.

---

## 🤖 System Instructions for Claude

Copy and append these instructions to your Custom System Prompt, Claude Desktop instructions, or Cursor .cursorrules profile:

```markdown
# N3MO Code Intelligence Integration

You have access to N3MO, a symbol-centric code intelligence layer via Model Context Protocol (MCP) tools:
- `n3mo_index`: Ingests and indexes the codebase.
- `n3mo_search_symbol`: Locates the definition of a symbol across the workspace (file path, line number).
- `n3mo_get_dependencies`: Finds all external symbols that a given symbol calls (the forward-dependency graph).
- `n3mo_get_file_symbols`: Lists all classes and functions defined inside a specific file.
- `n3mo_get_blast_radius`: Traces the transitive impact/call graph of a code symbol.

## Operational Rules

1. **Strictly use MCP Tools**: DO NOT run CLI commands like `n3mo impact` or `n3mo index` in the terminal. Always use the MCP tools provided above, as they return clean, structured context optimized for LLMs.
2. **Impact Check Before Editing**: 
   Before you modify, refactor, or delete any class, method, or function in the workspace, you MUST first run the `n3mo_get_blast_radius` tool on the target symbol to trace its downstream callers.
3. **Context-Aware Decisions**:
   Analyze the returned impact graph. If a symbol has transitive callers (especially deep nested call chains or high blast radius counts):
   - Notify the user about the impacted components and their respective file paths/line numbers.
   - Refactor calling signatures safely or adapt callers to accommodate the changes.
4. **Bootstrap Indexing**:
   If the workspace has not been indexed, or if you receive a "No index found" error, run `n3mo_index` to crawl and ingest the workspace folder structure first.
```

---

## ⚙️ Configuration Setup

### Claude Desktop Setup
N3MO is a registered MCP Server. To install it automatically, run:
```bash
n3mo mcp install
```

Alternatively, configure it manually by adding the following block to your `claude_desktop_config.json` (located at `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "n3mo": {
      "command": "python",
      "args": [
        "-m",
        "n3mo.mcp_server"
      ]
    }
  }
}
```

### Verification
Once configured, you will see a plug icon (🔌) in Claude Desktop, exposing:
* `n3mo_index`
* `n3mo_search_symbol`
* `n3mo_get_dependencies`
* `n3mo_get_file_symbols`
* `n3mo_get_blast_radius`
