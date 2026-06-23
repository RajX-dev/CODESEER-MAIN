# N3MO System Skill for Claude

Use this instruction profile to make Claude (or other LLM agents) aware of the **N3MO Code Intelligence Engine** and enforce impact checking before performing code modifications.

---

## 🤖 System Instructions for Claude

Copy and append these instructions to your Custom System Prompt, Claude Desktop instructions, or Cursor .cursorrules profile:

```markdown
# N3MO Code Intelligence Integration

You have access to N3MO, a symbol-centric code intelligence engine via Model Context Protocol (MCP) tools:
- `n3mo_index`: Ingests and indexes the codebase.
- `n3mo_get_blast_radius`: Traces the transitive impact/call graph of a code symbol.

## Operational Rules

1. **Impact Check Before Editing**: 
   Before you modify, refactor, or delete any class, method, or function in the workspace, you MUST first run the `n3mo_get_blast_radius` tool on the target symbol to trace its downstream callers.
   
2. **Context-Aware Decisions**:
   Analyze the returned impact graph. If a symbol has transitive callers (especially deep nested call chains or high blast radius counts):
   - Notify the user about the impacted components and their respective file paths/line numbers.
   - Refactor calling signatures safely or adapt callers to accommodate the changes.
   
3. **Bootstrap Indexing**:
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
* `n3mo_get_blast_radius`
