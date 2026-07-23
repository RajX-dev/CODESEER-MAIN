# Contributing to N3MO

First off, thank you for considering contributing to N3MO! 🎉 

N3MO is an **Open Core** platform. Contributions from the community are what make our structural code intelligence layer robust, stable, and feature-rich across dozens of programming languages.

Whether you're fixing a bug, adding a new Tree-sitter grammar, or improving our documentation, we want to make your experience as smooth as possible.

---

## 🗺️ Where to Start: Community & Communication

Since we are building this in public, communication is key. Please follow these guidelines on where to post:

* **Questions & Ideas:** If you need help using N3MO, want to discuss architectural changes, or have an idea for a feature, please use [GitHub Discussions](https://github.com/RajX-dev/N3MO/discussions) or join our [Discord Server](https://discord.gg/cTgZKHf2G).
* **Bug Reports:** If you found a confirmed bug in the parsing engine, CLI, or MCP server, open a [GitHub Issue](https://github.com/RajX-dev/N3MO/issues) using the Bug Report template.
* **Good First Issues:** If you're new to the codebase, check the `good first issue` or `help wanted` tags in the issue tracker. Drop a comment saying "I'd like to work on this!" so we can assign it to you.

### ⚠️ Scope Boundary Clause (Strict Open Core Policy)
N3MO operates on a strict Open Core model to protect our commercial infrastructure while fostering a vibrant open-source ecosystem. 

* **What we accept PRs for:** The core local CLI parser, the Tree-sitter AST mapping engine, Postgres graph schemas, and local MCP server interfaces.
* **What we DO NOT accept PRs for:** Any features attempting to implement local CI/CD webhooks, multi-tenant database scaling, enterprise single sign-on (SSO), or automated GitHub timeline integrations. These are proprietary components managed exclusively by our commercial team at **[n3mo.shop](https://n3mo.shop)**. Please respect this commercial boundary.

---

## 🛠️ Development Setup

To contribute code changes, you will need to set up N3MO locally on your machine.

### Prerequisites
* **Python 3.10+**
* **Docker & Docker Compose** (required to run the PostgreSQL database locally)
* **Git**

### Installation Steps
1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/N3MO.git
   cd N3MO
   ```
3. Set up a virtual environment and install N3MO in editable mode with development dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows, use `.venv\Scripts\activate`
   pip install -e ".[dev]"
   ```
4. Start the local database services and verify the schema setup:
   ```bash
   n3mo setup
   ```

---

## 🧪 Testing & Code Quality

Before opening a pull request, please ensure all checks pass locally. We enforce strict quality standards to ensure the graph database remains deterministic.

### Linting & Formatting
We use **Ruff** for linting and formatting. Run:
```bash
ruff check n3mo/
ruff format n3mo/
```

### Static Type Checking
We enforce static type annotations. Run **Mypy** to check types:
```bash
mypy n3mo/
```

### Running Tests
We use **pytest** for testing. Run the test suite:
```bash
pytest tests/
```
*Note: Make sure your local PostgreSQL container is running, as integration tests rely on actual database queries and CTE evaluation.*

---

## 📥 Submitting Changes

1. **Create a branch** for your work from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Write tests** for any new features or bug fixes. If you alter the AST traversal logic, you *must* include test cases proving the graph edges remain intact.
3. **Commit your changes** using clear, descriptive commit messages (e.g., `fix: handle python async function edge case in symbol extractor`).
4. **Push** your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Open a Pull Request** against the `main` branch of the original N3MO repository. Fill out the PR template completely and link the issue you are fixing.

---

## 🤝 Code of Conduct
Please be respectful and constructive in all issues, pull requests, and discussions. We aim to foster a collaborative, ego-free, and welcoming community for developers of all skill levels.
