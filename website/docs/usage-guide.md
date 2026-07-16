---
sidebar_position: 3
title: Usage Guide
---

# Usage

### Index a repository

```bash
cd /path/to/your/project
n3mo index
```

**What gets indexed:**
* Source files in all 27 supported languages
* Virtual environments (`venv/`, `.venv/`) — excluded
* Dependencies (`node_modules/`, `site-packages/`) — excluded
* Build artifacts (`.git/`, `__pycache__/`, `dist/`) — excluded
* Test / fixture directories (`tests/`, `mocks/`, `specs/`) — excluded

### Interactive Visualizer

Run the impact command with the `--graph` flag to launch the visualizer in your browser:

```bash
n3mo impact "your_function_name" --graph
```

#### Dark Mode — Radial Layout
![Dark Mode Radial Layout](/img/dark_mode_radial.png)

#### Horizontal Tree View
![Horizontal Tree View](/img/horizontal_tree.png)

### Terminal Output
If you don't use the `--graph` flag, N3MO prints a clean report to your terminal:

```
  IMPACT ANALYSIS
  ──────────────────────────────────────────────────────────────────
  Target:  authenticate_user
  ──────────────────────────────────────────────────────────────────

  Direct Callers  (3 symbols)

  login_endpoint             api/auth.py:12
  refresh_token              api/token.py:23
  validate_session           middleware/auth.py:89

  Ripple Effects  (5 symbols)

    POST /login              routes.py:67
    admin_login              admin/views.py:34
    require_auth             decorators.py:12
    dashboard_view           views/dashboard.py:8
    settings_view            views/settings.py:22

  ──────────────────────────────────────────────────────────────────
  Total impacted: 8 references  |  depth <= 3
```
