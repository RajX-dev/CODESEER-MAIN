# CodeSeer

**A code intelligence engine that transforms repositories into queryable knowledge graphs of code symbols, enabling deep code understanding, dependency analysis, and AI-assisted reasoning.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-316192.svg)](https://www.postgresql.org/)

---

## Overview

CodeSeer addresses a fundamental challenge in software engineering: **understanding large codebases**. Unlike simple code search tools that rely on text matching, CodeSeer models code structure first—capturing symbols, their relationships, and their semantics—enabling precise queries about dependencies, impact analysis, and architectural patterns.

### The Problem

Large codebases are difficult to navigate because:
- Text search is imprecise and context-unaware
- Dependencies are implicit and undocumented
- Architectural knowledge exists only in engineers' minds
- Impact analysis requires deep manual investigation

### The Solution

CodeSeer answers critical questions that traditional tools cannot:
- *What functions exist in this repository?*
- *Where is this class being used?*
- *What will break if I modify this function?*
- *How do these components actually connect?*

---

## Core Design Philosophy

> **Structure before semantics.**

Code must be understood as a graph of symbols and relationships before meaning-based search or AI reasoning can be trusted. This principle drives every architectural decision in CodeSeer.

---

## Architecture

### Knowledge Graph Model

CodeSeer builds a **symbol-centric knowledge graph** stored in PostgreSQL:

```
Project
  └── Symbols (UUID-based)
      ├── Functions
      ├── Classes
      ├── Methods
      └── Variables
          │
          ▼
      Relations (Typed, Directed Edges)
      ├── CALLS
      ├── USES
      ├── INHERITS
      └── DEFINES
```

### Key Design Decisions

- **SQL-first schema**: Leverages PostgreSQL's ACID guarantees and query optimization
- **Stable UUID identity**: Enables consistent symbol tracking across repository changes
- **Idempotent ingestion**: Re-indexing never creates duplicates
- **Resolution-aware relationships**: Captures both syntactic and semantic dependencies
- **Cascade-safe integrity**: Graph operations maintain referential consistency

---

## Current Capabilities

<<<<<<< HEAD
* **Core Backend:** Python 3.9+ (FastAPI)
* **Performance Module:** C++ 17 (CMake)
* **Infrastructure:** Docker, Docker Compose
* **Data:** PostgreSQL (Metadata), Elasticsearch (Search), [OPTIONAL] FAISS
=======
### ✅ Repository Crawling
- Recursive project tree traversal
- Source file identification and normalization
- Language detection via file extensions
- Path canonicalization

### ✅ Knowledge Graph Schema
- Implemented in PostgreSQL with full ACID compliance
- Symbol storage with rich metadata
- Typed relationship edges
- Efficient graph traversal queries

### ✅ CLI-First Architecture
- Command-line driven operation
- Scriptable and automatable workflows
- Designed for CI/CD integration
- UI layer to be added in later phases

>>>>>>> 77ab5fcbb295106a05b0f2e8a179ee3dfa8a8f08
---

## What CodeSeer Is *Not*

- ❌ A regex-based code search tool
- ❌ A Copilot-style code generator  
- ❌ A language-specific linter or analyzer
- ❌ A visualization-only project

These capabilities can be *built on top* of CodeSeer's knowledge graph—they are not the foundation.

---

## Roadmap

### Phase 0 — Foundations ✅
- Repository structure
- CLI entry point
- Semantic search prototype
- Dockerized development environment

### Phase 1 — Knowledge Model ✅
- Symbol taxonomy definition
- Relationship vocabulary
- PostgreSQL schema design
- Core data model locked

### Phase 2 — Parsing & Ingestion 🚧 *In Progress*
- File crawling implementation
- Symbol-only ingestion (first pass)
- Idempotent database population
- Tree-sitter integration (planned)

### Phase 3 — Query Engine 🔜
- Call graph traversal
- Dependency chain analysis
- Impact analysis queries
- Bounded graph exploration

### Phase 4 — Semantic Layer 🔜
- Symbol-aligned code chunking
- Vector embeddings integration
- Intent-based semantic search

### Phase 5 — Interface 🔜
- Enhanced CLI with rich queries
- REST API (optional)
- Web-based visualization
- Dependency graph rendering

### Phase 6 — Intelligence Layer 🔜
- Architecture summarization
- AI-powered change impact reasoning
- Intelligent code navigation

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Core Language** | Python 3.9+ |
| **Analysis Modules** | C++ (for performance-critical paths) |
| **Database** | PostgreSQL 13+ |
| **Schema Management** | SQL-first approach |
| **Parsing** | Tree-sitter (planned) |
| **Semantic Search** | Vector embeddings (planned) |
| **Deployment** | Docker, CLI-first |

---

## Getting Started

### Prerequisites

```bash
# Required
- Python 3.9+
- PostgreSQL 13+
- Docker (recommended)
```

### Installation

```bash
# Clone the repository
git clone https://github.com/RajX-dev/CODESEER-MAIN.git
cd CODESEER-MAIN

# Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials if needed

# Set up environment
docker-compose up -d

# Initialize database schema
python cli.py init

# Index a repository
python cli.py index /path/to/your/repo
```

### Basic Usage

```bash
# Index a codebase
python cli.py index /path/to/your/project

# Query for a specific symbol
python cli.py query --symbol "MyClass"

# Find all callers of a function
python cli.py query --callers "process_data"

# Analyze dependencies
python cli.py deps --from "module.function"

# Get symbol information
python cli.py info --symbol "UserService.authenticate"
```

> **Note:** Query commands shown are representative of planned functionality. Current implementation focuses on ingestion pipeline.

---

## Project Status

**Active Development** | **Sprint-Based Phases**

- ✅ Schema design completed and locked
- 🚧 Ingestion pipeline under construction
- 📋 Query engine in design phase

This project prioritizes **correctness, debuggability, and long-term scalability** over short-term demos.

---

## Design Principles

1. **Build for understanding, not just search** — CodeSeer models how code works, not just what it says
2. **Structure is queryable truth** — Relationships matter more than content
3. **CLI-first, UI-later** — Automation and scripting before visualization
4. **Correct before clever** — Solve the hard problem correctly first
5. **Scale from day one** — Architecture designed for enterprise-scale codebases

---

## Guiding Philosophy

> *If we cannot explain the system to a senior engineer, the system is not finished.*

CodeSeer is being built as a **production-grade systems project**, not a proof of concept. Every phase is designed to survive refactors, scale to millions of lines of code, and stand up to rigorous technical scrutiny.

---

## Contributing

This project is currently in active development. Contributions, feedback, and architectural discussions are welcome.

---

## License

MIT License (see LICENSE file for details)

---

## Author

**Raj** | [GitHub](https://github.com/RajX-dev)

*Building tools for understanding code at scale.*
