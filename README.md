# N3MO
 
<div align="center">
![N3MO Banner](https://img.shields.io/badge/N3MO-Code%20Intelligence%20Engine-blue?style=for-the-badge)
[![License: AGPL v3.0](https://img.shields.io/badge/license-AGPL%20v3.0-green?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue?style=for-the-badge&logo=python)](https://www.python.org)
[![Docker](https://img.shields.io/badge/docker-required-2496ED?style=for-the-badge&logo=docker)](https://www.docker.com)
[![CI](https://img.shields.io/badge/CI-coming%20soon-lightgrey?style=for-the-badge)]()
 
**A code intelligence engine that answers: "What breaks if I change this?"**
 
[What is N3MO](#what-is-n3mo) • [Architecture](#architecture) • [Installation](#installation) • [Usage](#usage) • [Benchmarks](#benchmarks) • [Roadmap](#roadmap)
 
</div>
---
 
## What is N3MO?
 
Most code search tools answer "where does this appear?" N3MO answers something harder:
 
```
❌ grep / text search:  "Where is authenticate_user defined?"
✅ N3MO:               "What will break across my entire codebase if I change authenticate_user?"
```
 
N3MO parses your repository into a **symbol-level knowledge graph** — functions, classes, methods, their relationships and call chains — stored in PostgreSQL. It then lets you query that graph to understand change impact before you make the change.
 
**Tested on real repositories:**
 
| Repository | LOC | Index time | Symbols extracted |
|------------|-----|------------|-------------------|
| [ScanCode Toolkit](https://github.com/nexB/scancode-toolkit) | ~600k | ~3 min | — |
 
*Benchmarked on Intel i5-13450HX, 24GB RAM. Full benchmark methodology in [BENCHMARKS.md](BENCHMARKS.md) (coming soon).*
 
---
 
## Architecture
 
N3MO builds a symbol-centric knowledge graph using three stages:
 
```
Source Code
    │
    ▼
Tree-sitter (AST Parser)        — error-tolerant, handles real-world messy code
    │
    ▼
Symbol Extractor                — functions, classes, methods, calls, imports
    │
    ▼
PostgreSQL Knowledge Graph      — symbols, relationships, call chains
    │
    ▼
Query Engine (Recursive CTE)    — blast radius, call graph, dependency traversal
    │
    ▼
CLI + HTML Visualizer           — terminal output + interactive graph
```
 
### Data model
 
```sql
projects     — one row per indexed repository
symbols      — every function, class, method (with file + line)
calls        — who calls whom (with line number)
imports      — import statements, resolved to symbols
```
 
The impact query uses a **recursive CTE** in PostgreSQL to walk the call graph to arbitrary depth — no application-level graph traversal, no in-memory state.
 
---
 
## Installation
 
**Requirements:** Docker, Python 3.10+
 
```bash
# 1. Clone
git clone https://github.com/RajX-dev/N3MO.git
cd N3MO
 
# 2. Configure environment
cp .env.example .env
# Edit .env if you want non-default DB credentials
 
# 3. Start infrastructure
docker-compose up -d
 
# 4. Install CLI
pip install -e .
 
# 5. Verify
n3mo --help
```
 
---
 
## Usage
 
### Index a repository
 
```bash
# Navigate to any Python repo
cd /path/to/your/project
 
# Index it
n3mo index
```
 
N3MO will walk the directory, parse every `.py` file with Tree-sitter, extract symbols and call relationships, and store them in PostgreSQL. Virtual environments, build artifacts, and dependency folders are automatically skipped.
 
### Blast radius analysis
 
```bash
# Find everything that will break if you change a function
n3mo impact "authenticate_user"
```
 
**Example output:**
 
```
  ◈ IMPACT ANALYSIS
  ──────────────────────────────────────────────────────────────
  Target:  authenticate_user
  ──────────────────────────────────────────────────────────────
 
  ◉ Direct Callers  (3 symbols)
 
  ▸ login_endpoint             api/auth.py:12
  ▸ refresh_token              api/token.py:23
  ▸ validate_session           middleware/auth.py:89
 
  ◎ Ripple Effects  (5 symbols)
 
    ╰─▸ POST /login              routes.py:67
    ╰─▸ admin_login              admin/views.py:34
    ╰─▸ require_auth             decorators.py:12
    ╰─▸ dashboard_view           views/dashboard.py:8
    ╰─▸ settings_view            views/settings.py:22
 
  ──────────────────────────────────────────────────────────────
  Total impacted: 8 references  │  depth ≤ 3
```
 
### Interactive graph
 
```bash
# Open a visual call graph in your browser
n3mo impact "authenticate_user" --graph
```
 
Launches a local server and opens an interactive vis.js graph with click-to-inspect nodes, zoom controls, and a sidebar showing call site details.
 
---
 
## Technology stack
 
| Component | Technology | Why |
|-----------|-----------|-----|
| Parser | [Tree-sitter](https://tree-sitter.github.io/) | Error-tolerant AST — handles real-world messy Python without crashing |
| Database | PostgreSQL 15 | Recursive CTEs for graph traversal without a graph database |
| Infrastructure | Docker Compose | Reproducible environment, single command setup |
| CLI | Python + argparse | Lightweight, no framework needed at this stage |
| Visualization | vis.js | Zero-dependency interactive graph in a single HTML file |
 
---
 
## Benchmarks
 
**ScanCode Toolkit** (~600k LOC, real run — February 2026)
 
- Hardware: Intel i5-13450HX, 24GB RAM, NVMe SSD
- Index time: ~3 minutes (single-threaded, v0.3)
- Status: multiprocessing in progress — target 4–8x speedup
> Numbers will be updated as optimizations land. No fabricated before/after tables — only measured results.
 
---
 
## Roadmap
 
### Now — v0.3 (current)
- [x] Tree-sitter AST parsing for Python
- [x] Symbol extraction (functions, classes, methods)
- [x] Call graph construction
- [x] Blast radius via recursive CTE
- [x] Docker-first infrastructure
- [x] Interactive HTML visualizer
### Next — v0.4 (May–June 2025)
- [ ] Connection pooling — eliminate per-symbol DB round trips
- [ ] Batch inserts via `execute_values()` — 1 transaction per file
- [ ] SHA-256 file hashing — skip unchanged files on re-index
- [ ] Multiprocessing for AST parsing — `ProcessPoolExecutor`
- [ ] Scope-aware call resolution — use imports table, not name matching
- [ ] CTE cycle guard — prevent infinite loops on circular call graphs
- [ ] Full type annotations + `mypy --strict` clean
- [ ] pytest suite with integration tests against real Postgres
- [ ] GitHub Actions CI
### After — v0.5
- [ ] MCP server — N3MO as a tool for Cursor, Claude Code, and other AI editors
- [ ] FastAPI REST layer — `GET /impact/{symbol}`, `POST /index`
- [ ] JavaScript / TypeScript support via `tree-sitter-javascript`
- [ ] Real-time incremental indexing via git hooks
- [ ] `pgvector` semantic search — "find functions that do X"
---
 
## Design principles
 
**Structure before semantics** — map the code skeleton (AST) before adding AI analysis. A correct graph is worth more than a smart but wrong one.
 
**Database as source of truth** — all state lives in PostgreSQL. No in-memory graph that disappears on restart.
 
**Idempotent operations** — re-indexing produces identical results. Safe to re-run at any time.
 
**Correctness over speed** — the parser must handle syntax errors gracefully. A fast indexer that silently drops symbols is worse than a slow one that gets everything.
 
---
 
## Contributing
 
Contributions welcome. The codebase is being actively cleaned up (see v0.4 roadmap above) — check open issues before starting anything large.
 
```bash
# Dev setup
pip install -e ".[dev]"
 
# Lint
ruff check src/
 
# Type check
mypy src/
 
# Tests (once they exist)
pytest tests/
```
 
---
 
## License
 
**AGPL-3.0** — free for personal and internal use. For commercial deployments or proprietary modifications, contact for licensing options.
 
See [LICENSE](LICENSE) for full details.
 
---
 
## Author
 
**Raj Shekhar** — Delhi Technological University
 
[![GitHub](https://img.shields.io/badge/GitHub-RajX--dev-181717?logo=github)](https://github.com/RajX-dev)
 
---
 
<div align="center">
*Building tools for understanding code at scale.*
 
</div>
 
