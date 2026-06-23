# Contributing to N3MO

Thank you for your interest in contributing to N3MO! Contributions from the community help make N3MO a more robust, stable, and feature-rich tool for everyone.

Here is a guide to help you get started with contributing.

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

Before opening a pull request, please ensure all checks pass locally.

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
*Note: Make sure your local PostgreSQL container is running, as some integration tests check database queries.*

---

## 📥 Submitting Changes

1. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   ```
2. **Write tests** for any new features or bug fixes.
3. **Commit your changes** using clear commit messages (e.g., `fix: handle tree-sitter parser compatibility issues safely`).
4. **Push** your branch to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
5. **Open a Pull Request** against the `main` branch of the original N3MO repository.

---

## 🤝 Code of Conduct
Please be respectful and constructive in all issues, pull requests, and discussions. We aim to foster a collaborative and welcoming community.
