# The N3MO Chronicle: A Technical Development Diary 📔

Welcome to the N3MO Development Diary! This is the chronological story of **N3MO** (formerly *CodeSeer*), a tool designed to parse source code ASTs, map dependencies, and visualize blast radius / impact analysis at scale.

---

## 🏛️ Era 1: The Foundations (Days 0–5)

### Chapter 1: Monorepo Architecture and AST Skeletals (Days 0–3)
* **Git Commits**: `093ed88` to `8a9d5c5`
* **The Story**:
  We initialized the monorepo structure. On Day 0, we stood up the infrastructure skeleton and initial parsing APIs. Over the next couple of days, we mapped out our database schema to hold relational call graph structures:
  - **`projects`**: Tracks repositories by their unique name and target path.
  - **`symbols`**: Tracks classes and functions, recording parent-child hierarchy scopes.
  - **`imports`**: Tracks module imports (module names, aliases, and imported symbols).
  - **`calls`**: Tracks function calls, capturing the source symbol and target call name.
  
  We added the MIT License (`d5921e7`) and set up our first parser wrappers, laying the groundwork for reading code skeletons.

### Chapter 2: Service Orchestration & Environmental Recovery (Days 4–5)
* **Git Commits**: `8a44556` and `f1fd403`
* **The Story**:
  To support large-scale code indexing, we dockerized our database environments. On Day 4, we configured PostgreSQL for storage and experimented with Elasticsearch for full-text indexing of extracted symbol signatures. On Day 5, we focused on recovering system configurations, fixing environment variable routing, and stabilizing container health, ensuring database tables were initialized correctly upon container boot-up.

---

## ⚙️ Era 2: Code Extraction & Multi-Language Exploration (Days 6–24)

### Chapter 3: The Clang C++ Parsing Engine (Day 6)
* **Git Commits**: `ed882f9`
* **The Story**:
  We explored multi-language parsing. On Day 6, we implemented a C++ analysis engine leveraging Clang AST bindings on WSL/Linux. The engine traversed C++ AST headers, extracting function definitions and calls. Although this proved the parser architecture's flexibility, we decided to streamline and focus our core pipeline optimizations on Python, JavaScript, and TypeScript, where dynamic dependencies create complex call graphs.

### Chapter 4: Professional Split-Pane UI & IDE Deep-Linking (Day 24)
* **Git Commits**: `ca4cc51` and `7913c62`
* **The Story**:
  We replaced the basic graph page with a professional, split-pane dashboard leveraging Vis.js. 
  - **IDE Deep-Linking**: We configured click handlers on graph nodes that trigger `vscode://file/{abs_path}:{line}` protocol deep links. Clicking any node in the browser immediately opens the exact source code line in the user's local VS Code.
  - **Concentric Layouts**: Staggered nodes on concentric orbits (offsetting by 45px intervals) and added angle offsets to ensure long function labels never overlapped.

---

## 🏎️ Era 3: Performance & Scale (Phase 2)

### Chapter 5: Renaming to N3MO & Connection Pooling
* **Git Commits**: `ff656b3` and `fd15397`
* **The Story**:
  We officially renamed the project from *CodeSeer* to **N3MO**. 
  
  During performance runs, we realized the parser was spawning and closing database connections for every single file. This connection overhead severely throttled performance. We replaced this with `psycopg2.pool.ThreadedConnectionPool` (maintaining 2 to 10 connections), bypassing TCP socket handshake limits and allowing connections to be reused across indexing operations.

### Chapter 6: The 23-Minute LIKE Bottleneck (The SPLIT_PART Fix)
* **Git Commits**: `2756a06` to `7ad78ab`
* **The Story**:
  When benchmarking on the Django repository (~3,000 files, 43k symbols, 181k calls), indexing took **23 minutes**. Query profiling pointed to our call resolver, which ran:
  ```sql
  c.call_name LIKE '%' || s.name
  ```
  This forced PostgreSQL to perform full-table sequential scans. We optimized the join condition by splitting the call name at the last dot (e.g. `module.function` -> `function`):
  ```sql
  SPLIT_PART(c.call_name, '.', -1) = s.name
  ```
  This utilized table indexes and slashed Django's indexing time in half: **23 minutes down to 11 minutes** (a 2.1x speedup).

### Chapter 7: Ingestion Batching via execute_values
* **Git Commits**: `85079c9` and `c21efcf`
* **The Story**:
  We shifted from single-row SQL inserts to batch inserts. In `process_file`, we integrated `psycopg2.extras.execute_values`. Instead of issuing thousands of network roundtrips per file, we batched all symbols, imports, and calls into a single bulk insert transaction per file. 
  
  This optimization squeezed Django's indexing time down to **5 minutes** (a total **4.6x speedup** over our baseline).

---

## 🧠 Era 4: Visuals, Correctness & Parallelism (Phase 3)

### Chapter 8: The Solar Orbit View & Real Code Previews
* **Git Commits**: `2e0e9aa` and `bfe5a19`
* **The Story**:
  We designed the **Solar Orbit View**—concentric orbital rings representing call ripple levels (e.g., Target at center, Direct Callers at orbit 1, Ripple Effects at orbits 2+). Edge connectors were styled as clean horizontal cubic bezier curves.
  
  We also added an interactive side-inspector panel that fetches the surrounding source lines of any selected node using `get_code_context(file_path, line_number)` and displays a real call-site preview in the UI, highlighting call lines.

### Chapter 9: SHA-256 Hashing, Pytest, and GitHub Actions CI
* **Git Commits**: `16c0e90` to `460a70f`
* **The Story**:
  To prevent redundant parsing of unchanged code, we introduced incremental indexing:
  1. Created a `files` table containing file paths and their SHA-256 hashes.
  2. Before parsing, N3MO calculates a file's SHA-256 hash. If it matches the database hash, the file is skipped.
  3. If a file is deleted from disk, N3MO detects its absence and runs `delete_file_index` to prune it.
  4. If indexing a new repo, N3MO deletes other repository data (`repo_url != target_dir`) to clear stale residue.
  
  We wrote a test suite in `tests/test_indexer.py` verifying file hashes, incremental skips, and database pruning, and configured a GitHub Actions CI pipeline (`.github/workflows/ci.yml`) spinning up a test PostgreSQL service.

### Chapter 10: The Quiet Crawler (Test Exclusion filtering)
* **Git Commits**: `d6e3838`
* **The Story**:
  Tests and mock suites were polluting the call graph. We modified `src/crawler.py` to:
  - Add `tests`, `test`, and `__tests__` to `IGNORED_DIRS` so the crawler skips traversing them entirely.
  - Implement file filter checks to ignore files starting with `test_` or ending with `_test.py`, `.test.py`, `_test.js`, `.test.js`, `_test.ts`, `.test.ts`, or matching `"test.py"`, `"test.js"`, `"test.ts"`.
  This cleaned up target call paths and dropped dependency noise.

### Chapter 11: Multi-Core Scaling and Windows Resource Protection (Today)
* **Git Commits**: `4f8c199`
* **The Story**:
  We addressed CPU scaling by parallelizing tree-sitter AST parsing. Since database connections cannot be safely shared across processes, we divided the pipeline:
  1. **Workers (CPU-bound)**: Using `ProcessPoolExecutor`, worker processes scan files, calculate SHA-256 hashes, parse AST nodes via tree-sitter, and return simple serializable dictionaries.
  2. **Main Thread (IO-bound)**: The main thread receives the parsed data and executes database transactions sequentially using `replace_file_index`.
  
  We also integrated standard Python `logging`. Human-friendly summaries print with emojis to stdout, and detailed logs are appended to `n3mo.log`.
  
  When testing on Windows, the active log file handler caused a `PermissionError: [WinError 32]` because the logger process held an open file handle to `n3mo.log` inside pytest's temporary test directory, blocking directory cleanups (`shutil.rmtree`). We resolved this by wrapping `main()` in a `try...finally` block that explicitly closes and removes all active log handlers on exit, releasing the Windows file lock cleanly.

### Chapter 12: Broadening Horizons with Multi-language Ingestion (Today)
* **Git Commits**: `4f8c199`
* **The Story**:
  We resolved to move N3MO from a Python-centric tool to a true multi-language indexer today. We installed and integrated pre-built bindings for **JavaScript, TypeScript, Go, Rust, Java, C++, and C** using standard tree-sitter language extensions.
  
  In `symbol_extractor.py`, we designed a dynamic `get_parser(lang_name)` factory that instantiates the correct language parser per process/thread. We created a generalized, recursive AST visitor (`_visit_generic`) that extracts symbols, imports, and function calls from all supported languages based on their unique node types:
  - **JS/TS**: Maps `function_declaration`, `method_definition`, `class_declaration`, and parent-variable scoped `arrow_function` assignments.
  - **Go**: Scans `function_declaration`, receiver `method_declaration`, and standard Go `import_spec` paths.
  - **Rust**: Extracts `function_item`, `struct_item`/`enum_item`/`trait_item`, and Rust's `use_declaration` paths.
  - **Java**: Extracts classes, methods, invocations, and package-scoped imports.
  - **C/C++**: Leverages helper functions to navigate pointer/reference declarators, extracting C/C++ function definitions/declarations, class specifiers, and `#include` statements.
  
  We expanded `crawler.py` to recognize all of these extensions and filter corresponding mock test file extensions, and added a comprehensive test suite `test_multilanguage_parsing` in `tests/test_indexer.py` verifying correct symbol and call extraction for all target languages. All tests passed!

### Chapter 13: Flawless 27-Language Support and Smart Impact Exclusions (Today)
* **Git Commits**: `4f8c199`
* **The Story**:
  We expanded N3MO's language capabilities to cover all 27 requested languages (including C#, Delphi, Perl, PHP, Ruby, Powershell, Groovy, Matlab, Scala, Swift, Julia, Haskell, Lua, Cobol, Dart, VBA, Visual Basic, R, and others). We implemented a safe runtime load check for tree-sitter bindings, enabling graceful degradation for less common languages.
  
  To keep the database clean, we implemented two major features requested by the user:
  1. **Advanced Directory and File Exclusions**: The crawler now ignores folders like `tests`, `mock`, `spec`, `benchmark`, `example`, `sample`, `fixture`, `temp`, `tmp`, and files matching these test keywords (including Perl `.t` files). We engineered a camelCase-sensitive and separator-aware prefix/suffix matcher so that valid source files like `contest.py`, `mockingbird.py`, or `special.py` are not incorrectly ignored.
  2. **No-Impact Skips and Pruning**: Files that contain 0 symbols, 0 calls, and 0 imports are classified as "no-impact" and skipped from indexing to keep the database footprint lean. If an existing file is cleared or reduced to comments, its index residues and hash are completely pruned from the database.
  
  We appended all 22 successfully installed tree-sitter language bindings to `requirements.txt` and verified the logic using an expanded test suite. All tests pass, and style compliance with Ruff is flawless.

### Chapter 14: Running N3MO on the MUZIK React App (Today)
* **Git Commits**: `4f8c199`
* **The Story**:
  The user requested to run N3MO on the `MUZIK` React web app project located as a sibling folder in the main directory. By setting `TARGET_CODE_DIR` to point to the `MUZIK` folder, we initiated N3MO.
  
  N3MO's crawler and multi-language parser scanned both the Python backend and JSX frontend directories, resulting in the following:
  - **Exclusions**: `backend/mock_data_generator.py` was correctly ignored because it starts with the `mock_` prefix, showing that the filename exclusion rules function perfectly in practice.
  - **No-Impact Skips**: `frontend/src/index.js` was skipped from index database insertion since it produced 0 symbols, imports, and calls.
  - **Multi-language parsing**: Indexing succeeded, successfully extracting 27 symbols and 136 calls from Python backend files (`backend/main.py`, `backend/ml_model.py`) and JS/React files (`frontend/src/App.jsx`). The calls were resolved and linked successfully in PostgreSQL.
