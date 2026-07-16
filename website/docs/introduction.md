---
sidebar_position: 1
title: What is N3MO?
---

# What is N3MO?

N3MO is a symbol-centric code intelligence layer. Instead of scanning raw text, it parses your source code's ASTs, maps call graphs, and models dependencies in a queryable relational database — deterministically, with **zero LLM calls at index time**.

For engineering leaders and teams, N3MO acts as a **structural insurance policy** for your codebases.

### Why N3MO?

* **Eliminate Regression Risks** — Utility functions are rarely refactored because developers fear unknown side effects. N3MO maps the transitive blast radius of any symbol to arbitrary depth, showing you exactly what will break before you make the edit.
* **Rapid Developer Onboarding** — Instead of senior engineers spending hours explaining codebase flow to new hires, developers run one command to visualize complex call chains and parent-child dependencies interactively.
* **AI-Agent Ready Infrastructure** — Modern LLM agents (Cursor, Claude Desktop) are limited by context windows and text search. N3MO's native MCP server lets agents query the actual code graph, enabling fast, hallucination-free refactoring.
* **No Embeddings, No Drift** — N3MO is pure static analysis: Tree-sitter AST parsing into PostgreSQL. There's no vector index to keep in sync, no embedding cost per repo, and no semantic-similarity guesswork — every edge in the graph is an exact, verifiable relationship.

### How N3MO Compares

| Capability | Grep / Text Search | IDE "Find References" | N3MO Code Graph |
| :--- | :--- | :--- | :--- |
| **Analysis Basis** | Substring matching | AST-based, direct refs only | Relational knowledge graph |
| **Transitive Traversal** | None | Manual, one level at a time | **Instant to arbitrary depth** |
| **Blast Radius Mapping** | None | Flat search-result list | **Interactive visual orbit map** |
| **CI/CD Integration** | None | Bound to IDE runtime | **Dockerized CLI + CTE queries** |
| **AI Agent Integration** | Injected file chunks | Manual context copy | **Native MCP server** |
| **Language Coverage** | Any text file | Language-specific plugins | **27 Tree-sitter grammars** |
| **Indexing Method** | N/A | N/A | **Deterministic AST parse** |

### The Core Problem N3MO Solves

> **N3MO doesn't find text — it understands structure.** It traces the actual call graph, not string matches.

**Questions N3MO answers instantly:**

| | Question | How |
|:---:|:---|:---|
| | What functions and classes exist in this repo? | Full symbol index across 27 languages |
| | Where is this symbol used — directly *and* transitively? | Recursive CTE traversal to arbitrary depth |
| | What is the **blast radius** of changing this function? | Interactive orbit map with depth slider |
| | How do these components actually connect? | Call graph + parent-child hierarchy |
| | Can my AI agent understand this codebase structurally? | Native MCP server for Cursor / Claude |
