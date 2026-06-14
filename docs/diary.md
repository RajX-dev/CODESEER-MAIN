# The N3MO Chronicle: A Technical Development Diary 📔

Welcome to the N3MO Development Diary! This is the chronological story of **N3MO** (formerly *CodeSeer*), a tool I designed to parse source code ASTs, map dependencies, and visualize blast radius / impact analysis at scale.

---

## 🏛️ Era 1: The Foundations (Days 0–5)

### Chapter 1: Monorepo Architecture and AST Skeletals (Days 0–3)
* **Git Commits**: `093ed88` to `8a9d5c5`
* **The Story**:
  I initialized the monorepo structure. On Day 0, I stood up the infrastructure skeleton and initial parsing APIs. Over the next couple of days, I mapped out the database schema to hold relational call graph structures:
  - **`projects`**: Tracks repositories by their unique name and target path.
  - **`symbols`**: Tracks classes and functions, recording parent-child hierarchy scopes.
  - **`imports`**: Tracks module imports (module names, aliases, and imported symbols).
  - **`calls`**: Tracks function calls, capturing the source symbol and target call name.
  
  I added the AGPL-3.0 License (`d5921e7`) and set up the first parser wrappers, laying the groundwork for reading code skeletons.

### Chapter 2: Service Orchestration & Environmental Recovery (Days 4–5)
* **Git Commits**: `8a44556` and `f1fd403`
* **The Story**:
  To support large-scale code indexing, I dockerized the database environments. On Day 4, I configured PostgreSQL for storage and experimented with Elasticsearch for full-text indexing of extracted symbol signatures. On Day 5, I focused on recovering system configurations, fixing environment variable routing, and stabilizing container health, ensuring database tables were initialized correctly upon container boot-up.

---

## ⚙️ Era 2: Code Extraction & Multi-Language Exploration (Days 6–24)

### Chapter 3: The Clang C++ Parsing Engine (Day 6)
* **Git Commits**: `ed882f9`
* **The Story**:
  I explored multi-language parsing. On Day 6, I implemented a C++ analysis engine leveraging Clang AST bindings on WSL/Linux. The engine traversed C++ AST headers, extracting function definitions and calls. Although this proved the parser architecture's flexibility, I decided to streamline and focus the core pipeline optimizations on Python, JavaScript, and TypeScript, where dynamic dependencies create complex call graphs.

### Chapter 4: Professional Split-Pane UI & IDE Deep-Linking (Day 24)
* **Git Commits**: `ca4cc51` and `7913c62`
* **The Story**:
  I replaced the basic graph page with a professional, split-pane dashboard leveraging Vis.js. 
  - **IDE Deep-Linking**: I configured click handlers on graph nodes that trigger `vscode://file/{abs_path}:{line}` protocol deep links. Clicking any node in the browser immediately opens the exact source code line in the user's local VS Code.
  - **Concentric Layouts**: I staggered nodes on concentric orbits (offsetting by 45px intervals) and added angle offsets to ensure long function labels never overlapped.

---

## 🏎️ Era 3: Performance & Scale (Phase 2)

### Chapter 5: Renaming to N3MO & Connection Pooling
* **Git Commits**: `ff656b3` and `fd15397`
* **The Story**:
  I officially renamed the project from *CodeSeer* to **N3MO**. 
  
  During performance runs, I realized the parser was spawning and closing database connections for every single file. This connection overhead severely throttled performance. I replaced this with `psycopg2.pool.ThreadedConnectionPool` (maintaining 2 to 10 connections), bypassing TCP socket handshake limits and allowing connections to be reused across indexing operations.

### Chapter 6: The 23-Minute LIKE Bottleneck (The SPLIT_PART Fix)
* **Git Commits**: `2756a06` to `7ad78ab`
* **The Story**:
  When benchmarking on the Django repository (~3,000 files, 43k symbols, 181k calls), indexing took **23 minutes**. Query profiling pointed to the call resolver, which ran:
  ```sql
  c.call_name LIKE '%' || s.name
  ```
  This forced PostgreSQL to perform full-table sequential scans. I optimized the join condition by splitting the call name at the last dot (e.g. `module.function` -> `function`):
  ```sql
  SPLIT_PART(c.call_name, '.', -1) = s.name
  ```
  This utilized table indexes and slashed Django's indexing time in half: **23 minutes down to 11 minutes** (a 2.1x speedup).

### Chapter 7: Ingestion Batching via execute_values
* **Git Commits**: `85079c9` and `c21efcf`
* **The Story**:
  I shifted from single-row SQL inserts to batch inserts. In `process_file`, I integrated `psycopg2.extras.execute_values`. Instead of issuing thousands of network roundtrips per file, I batched all symbols, imports, and calls into a single bulk insert transaction per file. 
  
  This optimization squeezed Django's indexing time down to **5 minutes** (a total **4.6x speedup** over the baseline).

---

## 🧠 Era 4: Visuals, Correctness & Parallelism (Phase 3)

### Chapter 8: The Solar Orbit View & Real Code Previews
* **Git Commits**: `2e0e9aa` and `bfe5a19`
* **The Story**:
  I designed the **Solar Orbit View**—concentric orbital rings representing call ripple levels (e.g., Target at center, Direct Callers at orbit 1, Ripple Effects at orbits 2+). Edge connectors were styled as clean horizontal cubic bezier curves.
  
  I also added an interactive side-inspector panel that fetches the surrounding source lines of any selected node using `get_code_context(file_path, line_number)` and displays a real call-site preview in the UI, highlighting call lines.

### Chapter 9: SHA-256 Hashing, Pytest, and GitHub Actions CI
* **Git Commits**: `16c0e90` to `460a70f`
* **The Story**:
  To prevent redundant parsing of unchanged code, I introduced incremental indexing:
  1. Created a `files` table containing file paths and their SHA-256 hashes.
  2. Before parsing, N3MO calculates a file's SHA-256 hash. If it matches the database hash, the file is skipped.
  3. If a file is deleted from disk, N3MO detects its absence and runs `delete_file_index` to prune it.
  4. If indexing a new repo, N3MO deletes other repository data (`repo_url != target_dir`) to clear stale residue.
  
  I wrote a test suite in `tests/test_indexer.py` verifying file hashes, incremental skips, and database pruning, and configured a GitHub Actions CI pipeline (`.github/workflows/ci.yml`) spinning up a test PostgreSQL service.

### Chapter 10: The Quiet Crawler (Test Exclusion Filtering)
* **Git Commits**: `d6e3838`
* **The Story**:
  Tests and mock suites were polluting the call graph. I modified `src/crawler.py` to:
  - Add `tests`, `test`, and `__tests__` to `IGNORED_DIRS` so the crawler skips traversing them entirely.
  - Implement file filter checks to ignore files starting with `test_` or ending with `_test.py`, `.test.py`, `_test.js`, `.test.js`, `_test.ts`, `.test.ts`, or matching `"test.py"`, `"test.js"`, `"test.ts"`.
  This cleaned up target call paths and dropped dependency noise.

### Chapter 11: Multi-Core Scaling and Windows Resource Protection
* **Git Commits**: `4f8c199`
* **The Story**:
  I addressed CPU scaling by parallelizing tree-sitter AST parsing. Since database connections cannot be safely shared across processes, I divided the pipeline:
  1. **Workers (CPU-bound)**: Using `ProcessPoolExecutor`, worker processes scan files, calculate SHA-256 hashes, parse AST nodes via tree-sitter, and return simple serializable dictionaries.
  2. **Main Thread (IO-bound)**: The main thread receives the parsed data and executes database transactions sequentially using `replace_file_index`.
  
  I also integrated standard Python `logging`. Human-friendly summaries print with emojis to stdout, and detailed logs are appended to `n3mo.log`.
  
  When testing on Windows, the active log file handler caused a `PermissionError: [WinError 32]` because the logger process held an open file handle to `n3mo.log` inside pytest's temporary test directory, blocking directory cleanups (`shutil.rmtree`). I resolved this by wrapping `main()` in a `try...finally` block that explicitly closes and removes all active log handlers on exit, releasing the Windows file lock cleanly.

### Chapter 12: Broadening Horizons with Multi-Language Ingestion
* **Git Commits**: `4f8c199`
* **The Story**:
  I resolved to move N3MO from a Python-centric tool to a true multi-language indexer. I installed and integrated pre-built bindings for **JavaScript, TypeScript, Go, Rust, Java, C++, and C** using standard tree-sitter language extensions.
  
  In `symbol_extractor.py`, I designed a dynamic `get_parser(lang_name)` factory that instantiates the correct language parser per process/thread. I created a generalized, recursive AST visitor (`_visit_generic`) that extracts symbols, imports, and function calls from all supported languages based on their unique node types:
  - **JS/TS**: Maps `function_declaration`, `method_definition`, `class_declaration`, and parent-variable scoped `arrow_function` assignments.
  - **Go**: Scans `function_declaration`, receiver `method_declaration`, and standard Go `import_spec` paths.
  - **Rust**: Extracts `function_item`, `struct_item`/`enum_item`/`trait_item`, and Rust's `use_declaration` paths.
  - **Java**: Extracts classes, methods, invocations, and package-scoped imports.
  - **C/C++**: Leverages helper functions to navigate pointer/reference declarators, extracting C/C++ function definitions/declarations, class specifiers, and `#include` statements.
  
  I expanded `crawler.py` to recognize all of these extensions and filter corresponding mock test file extensions, and added a comprehensive test suite `test_multilanguage_parsing` in `tests/test_indexer.py` verifying correct symbol and call extraction for all target languages. All tests passed!

### Chapter 13: Flawless 27-Language Support and Smart Impact Exclusions
* **Git Commits**: `4f8c199`
* **The Story**:
  I expanded N3MO's language capabilities to cover all 27 requested languages (including C#, Delphi, Perl, PHP, Ruby, Powershell, Groovy, Matlab, Scala, Swift, Julia, Haskell, Lua, Cobol, Dart, VBA, Visual Basic, R, and others). I implemented a safe runtime load check for tree-sitter bindings, enabling graceful degradation for less common languages.
  
  To keep the database clean, I implemented two major features:
  1. **Advanced Directory and File Exclusions**: The crawler now ignores folders like `tests`, `mock`, `spec`, `benchmark`, `example`, `sample`, `fixture`, `temp`, `tmp`, and files matching these test keywords (including Perl `.t` files). I engineered a camelCase-sensitive and separator-aware prefix/suffix matcher so that valid source files like `contest.py`, `mockingbird.py`, or `special.py` are not incorrectly ignored.
  2. **No-Impact Skips and Pruning**: Files that contain 0 symbols, 0 calls, and 0 imports are classified as "no-impact" and skipped from indexing to keep the database footprint lean. If an existing file is cleared or reduced to comments, its index residues and hash are completely pruned from the database.
  
  I appended all 22 successfully installed tree-sitter language bindings to `requirements.txt` and verified the logic using an expanded test suite. All tests pass, and style compliance with Ruff is flawless.

### Chapter 14: Running N3MO on the MUZIK React App
* **Git Commits**: `4f8c199`
* **The Story**:
  I ran N3MO on the `MUZIK` React web app project located as a sibling folder in the main directory. By setting `TARGET_CODE_DIR` to point to the `MUZIK` folder, I initiated N3MO.
  
  N3MO's crawler and multi-language parser scanned both the Python backend and JSX frontend directories, resulting in the following:
  - **Exclusions**: `backend/mock_data_generator.py` was correctly ignored because it starts with the `mock_` prefix, showing that the filename exclusion rules function perfectly in practice.
  - **No-Impact Skips**: `frontend/src/index.js` was skipped from index database insertion since it produced 0 symbols, imports, and calls.
  - **Multi-language parsing**: Indexing succeeded, successfully extracting 27 symbols and 136 calls from Python backend files (`backend/main.py`, `backend/ml_model.py`) and JS/React files (`frontend/src/App.jsx`). The calls were resolved and linked successfully in PostgreSQL.

### Chapter 15: Warm Beige Theme and Dynamic Canvas Dark Mode
* **Git Commits**: `4f8c199` (updated)
* **The Story**:
  The default visualizer layout was too bright. To improve user comfort, I completely refactored the UI design to have a premium, warm beige aesthetic inspired by Anthropic's website (using Google Serif font Lora, custom fonts, rounded badges, and subtle borders).
  
  Additionally, I introduced an interactive Theme Toggle button. Clicking the button toggles between Light Mode and Dark Mode, saving the user's preference in browser `localStorage`. When the theme changes:
  1. CSS variables dynamically switch the dashboard background, panel, borders, search input, and code preview colors.
  2. A JavaScript theme handler immediately updates all Vis.js canvas nodes (adjusting node backgrounds and borders), edges (adjusting connector and highlight colors), text labels (ensuring perfect readability on the dark background), and dotted concentric orbit lines in real-time.
  
  I indexed the `MUZIK` React project and successfully generated `impact_graph.html` demonstrating the seamless transition between the warm light and dark mode styles. All tests and ruff compliance checks continue to pass cleanly.

---

## 🚀 Era 5: Distribution & Polish (Phase 4)

### Chapter 16: MCP Server — Making N3MO an AI-Native Tool
* **The Story**:
  This was a big conceptual shift. I built a native Model Context Protocol (MCP) server so that LLM agents like Claude Desktop, Cursor, and Windsurf could directly query N3MO's code graph — no copy-pasting, no injecting file chunks.
  
  The MCP server (`n3mo/mcp_server.py`) exposes N3MO's core capabilities as structured tools: `index_repository`, `get_impact`, `list_symbols`, and `search_symbols`. I also built an `n3mo mcp install` command that auto-configures Claude Desktop's `claude_desktop_config.json` with the correct paths, so setup is literally one command.
  
  This felt like the right direction for N3MO. Instead of competing with text search, I'm giving AI agents a structural understanding of codebases — they can ask "what breaks if I change this function?" and get a precise answer from the actual call graph, not a guess from pattern matching.

### Chapter 17: FastAPI REST Layer & Git Hook Integration
* **The Story**:
  I added two more distribution channels to make N3MO useful in real workflows:
  
  1. **FastAPI REST API** (`n3mo/api_server.py`): A lightweight HTTP layer exposing `GET /health`, `GET /impact/{symbol_name}`, and `POST /index`. This lets CI pipelines, dashboards, or custom scripts query N3MO programmatically. I registered the `n3mo api` subcommand in the CLI to start the server.
  
  2. **Git Post-Commit Hook** (`n3mo/git_hooks.py`): Running `n3mo git-hook install` writes a post-commit hook to `.git/hooks/` that automatically re-indexes the repository after every commit. This means the code graph stays fresh without any manual intervention — commit your code, and N3MO silently updates the database in the background.

### Chapter 18: Scope-Aware Call Resolution, CTE Cycle Guards & Mypy CI
* **The Story**:
  I tackled three correctness issues that had been bugging me:
  
  1. **Scope-Aware Call Resolution** (`n3mo/resolve_calls.py`, `n3mo/resolve_imports.py`): The old call resolver was naive — it just matched function names globally. I rewrote it with a priority-based strategy: class scope > local file scope > imports > qualified dot paths > global. This dramatically reduced false positive call links, especially in larger codebases where multiple files define functions with the same name.
  
  2. **CTE Cycle Guards**: The recursive CTE query for blast radius analysis could theoretically loop infinitely on circular call graphs. I added a `visited` array to the recursive query that tracks already-seen node IDs and terminates traversal when a cycle is detected. This is a safety net — it doesn't change results for clean graphs, but prevents hangs on pathological ones.
  
  3. **Mypy Integration**: I added full type annotations across the codebase and configured `mypy` in the GitHub Actions CI pipeline. Every PR now gets static type checking alongside linting and tests. I had to fix a bunch of `Optional` returns and `Any` types, but the codebase is now `mypy`-clean.
  
  I also expanded the test suite to 9 tests covering all of these new features. All pass cleanly.

### Chapter 19: README Overhaul & Product Polish (June 14, 2026)
* **The Story**:
  With all four phases of the roadmap complete, I stepped back and looked at the README with fresh eyes. It had grown organically as I built features, and it showed — duplicate capability lists, outdated screenshots, a `pgvector` line marked as "❌ Replaced" that looked like a failure, and a benchmarks section that undersold the product.
  
  I did a full rewrite:
  - **Removed the pgvector reference entirely**. My thinking is that with the native MCP server, there's no need for vector similarity search. People who use N3MO know what to ask — they don't need fuzzy semantic matching, they need structural precision.
  - **Redesigned the "Core Problem" section** with a side-by-side before/after comparison table showing grep (647 useless matches) vs N3MO (3 direct callers, full blast radius in <50ms). Much more impactful than the old two-line code block.
  - **Consolidated capabilities** into organized categories (Ingestion, Analysis, Performance, Integration) instead of a wall of checkboxes.
  - **Added a Supported Languages showcase** — a grid of 27 badge icons. This was a hidden feature buried in a bullet point before.
  - **Overhauled the benchmarks** — added a Unicode progress bar chart for the Django optimization history (23min → 2.5min, 9× speedup), incremental re-index benchmarks (<1 second for unchanged repos), and query latency numbers (<50ms for full blast radius).
  - **Updated the architecture diagrams** to reflect the current system. The old ER diagram only showed `PROJECT` and `SYMBOL` with wrong column names. The new one shows all 5 tables (`PROJECT`, `SYMBOL`, `CALL`, `IMPORT`, `FILE`) with exact column names matching the schema. I also added MCP Server, REST API, and Git Hooks to the flow diagram.
  - **Replaced the old light-mode screenshots** with new dark-mode captures of the radial layout visualization.
  - **Changed the status badge** from "active development" (which sounds unfinished) to "stable" (which is what it is now).
  
  The roadmap table now shows all phases as ✅ Complete with no "❌ Replaced" lines. It finally feels like a product page, not a work-in-progress doc.

### Chapter 20: Aligned ASCII Art Logo & Visual Polish (June 14, 2026)
* **The Story**:
  I addressed a visual layout issue in the README's ASCII art logo. The block characters suffered from minor character alignment/width warping depending on the browser's font rendering, causing visible indentation skews.
  
  To solve this, I mathematically aligned the bounding box columns of each letter (`N`, `3`, `M`, `O`) across all lines:
  - Ensured consistent 3-character horizontal spacing between letters.
  - Aligned the right/left boundaries of every curve and line.
  - Appended padding spaces to match the 47-character width of the sub-text.
  - Centered the sub-text "C O D E   I N T E L L I G E N C E   E N G I N E" flush under the logo.
  
  I also reorganised the README layout: I placed the newly recorded walkthrough GIF (`n3mo_intro.gif`) right at the top of the document for an immediate, high-impact visual introduction, and relocated the aligned ASCII art logo to the footer as a signature ending block.
  
  This preserves the classic developer ASCII art aesthetic in a balanced footer layout while ensuring it remains perfectly rectangular and skew-free in all preview environments, while presenting a highly professional dynamic intro at the top.




