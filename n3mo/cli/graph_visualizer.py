# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

import json


def generate_solar_graph_html(nodes, edges, target_name, max_depth=3):
    nodes_list = [
        {
            "id": name,
            "label": name,
            "group": data["group"],
            "path": data.get("path", ""),
            "line": data.get("line", 0),
            "code_context": data.get("code_context", []),
        }
        for name, data in nodes
    ]
    edges_list = [
        {"id": f"edge-{index}", "from": source, "to": target}
        for index, (source, target) in enumerate(edges)
    ]

    page = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>N3MO — Impact Graph</title>
  <meta name="description" content="N3MO blast radius impact graph visualization for code dependency analysis">
  <script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.2/dist/vis-network.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,700;12..96,800&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    /* ============================================================
       DESIGN SYSTEM TOKENS
       ============================================================ */
    :root {
      /* Dark theme (default) */
      --bg-base: #09090b;
      --bg-surface: #18181b;
      --bg-elevated: #27272a;
      --bg-overlay: rgba(9, 9, 11, 0.85);
      --border: rgba(255, 255, 255, 0.06);
      --border-hover: rgba(255, 255, 255, 0.12);
      --border-focus: rgba(245, 158, 11, 0.5);
      --text-primary: #fafafa;
      --text-secondary: #a1a1aa;
      --text-tertiary: #71717a;
      --accent: #f59e0b;
      --accent-hover: #d97706;
      --accent-muted: rgba(245, 158, 11, 0.12);
      --red: #f43f5e;
      --red-muted: rgba(244, 63, 94, 0.12);
      --cyan: #06b6d4;
      --cyan-muted: rgba(6, 182, 212, 0.12);
      --amber: #f59e0b;
      --amber-muted: rgba(245, 158, 11, 0.12);
      --indigo: #6366f1;
      --indigo-muted: rgba(99, 102, 241, 0.12);
      --green: #10b981;
      --green-muted: rgba(16, 185, 129, 0.12);
      --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.3);
      --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.4);
      --shadow-lg: 0 12px 40px rgba(0, 0, 0, 0.5);
      --radius-sm: 6px;
      --radius-md: 8px;
      --radius-lg: 12px;
      --font-ui: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
      --font-display: 'Bricolage Grotesque', sans-serif;
      --ease: cubic-bezier(0.4, 0, 0.2, 1);
      --ease-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
      --canvas-dot: rgba(255, 255, 255, 0.04);
    }

    body.light-mode {
      --bg-base: #fafafa;
      --bg-surface: #ffffff;
      --bg-elevated: #f4f4f5;
      --bg-overlay: rgba(250, 250, 250, 0.9);
      --border: rgba(0, 0, 0, 0.06);
      --border-hover: rgba(0, 0, 0, 0.12);
      --border-focus: rgba(217, 119, 6, 0.5);
      --text-primary: #09090b;
      --text-secondary: #71717a;
      --text-tertiary: #a1a1aa;
      --accent: #d97706;
      --accent-hover: #b45309;
      --accent-muted: rgba(217, 119, 6, 0.08);
      --red: #e11d48;
      --red-muted: rgba(225, 29, 72, 0.08);
      --cyan: #0891b2;
      --cyan-muted: rgba(8, 145, 178, 0.08);
      --amber: #b45309;
      --amber-muted: rgba(180, 83, 9, 0.08);
      --indigo: #4f46e5;
      --indigo-muted: rgba(79, 70, 229, 0.08);
      --green: #059669;
      --green-muted: rgba(5, 150, 105, 0.08);
      --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
      --shadow-md: 0 4px 12px rgba(0, 0, 0, 0.08);
      --shadow-lg: 0 12px 40px rgba(0, 0, 0, 0.12);
      --canvas-dot: rgba(0, 0, 0, 0.05);
    }

    /* ============================================================
       RESET & BASE
       ============================================================ */
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    html, body { width: 100%; height: 100%; overflow: hidden; }
    body {
      font-family: var(--font-ui);
      font-size: 13px;
      color: var(--text-primary);
      background: var(--bg-base);
      -webkit-font-smoothing: antialiased;
      -moz-osx-font-smoothing: grayscale;
      transition: background-color 0.2s var(--ease), color 0.2s var(--ease);
    }

    /* Custom scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--border-hover); border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: var(--text-tertiary); }

    /* Focus ring */
    :focus-visible {
      outline: 2px solid var(--border-focus);
      outline-offset: 2px;
    }

    /* ============================================================
       LAYOUT SHELL
       ============================================================ */
    #app {
      display: flex;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
    }

    /* ---- Left Panel ---- */
    #left-panel {
      width: 248px;
      flex-shrink: 0;
      background: var(--bg-surface);
      border-right: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      z-index: 20;
      transition: margin-left 0.25s var(--ease), opacity 0.25s var(--ease);
    }
    #left-panel.collapsed { margin-left: -248px; }

    .lp-header {
      height: 48px;
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 0 16px;
      border-bottom: 1px solid var(--border);
      flex-shrink: 0;
    }

    .lp-logo {
      display: flex;
      align-items: center;
      gap: 8px;
      text-decoration: none;
      color: var(--text-primary);
    }

    .lp-logo-text {
      font-family: var(--font-display);
      font-size: 15px;
      font-weight: 800;
      letter-spacing: 0.06em;
    }

    .lp-scroll { flex: 1; overflow-y: auto; padding: 8px 0; }

    .lp-section {
      padding: 12px 12px 16px;
    }
    .lp-section + .lp-section { border-top: 1px solid var(--border); }

    .lp-section-title {
      font-family: var(--font-display);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: var(--text-tertiary);
      margin-bottom: 10px;
      padding: 0 4px;
    }

    /* Controls */
    .ctrl-group { padding: 0 4px; }
    .ctrl-group + .ctrl-group { margin-top: 12px; }

    .ctrl-label {
      display: block;
      font-size: 11px;
      font-weight: 500;
      color: var(--text-secondary);
      margin-bottom: 6px;
    }

    .ctrl-select {
      width: 100%;
      height: 32px;
      padding: 0 10px;
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      color: var(--text-primary);
      font-family: var(--font-ui);
      font-size: 12px;
      cursor: pointer;
      transition: border-color 0.15s var(--ease);
      appearance: none;
      background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2371717a' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
      background-repeat: no-repeat;
      background-position: right 10px center;
    }
    .ctrl-select:hover { border-color: var(--border-hover); }
    .ctrl-select:focus { border-color: var(--accent); outline: none; }

    .ctrl-slider-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }

    .ctrl-slider-val {
      font-family: var(--font-mono);
      font-size: 12px;
      font-weight: 500;
      color: var(--accent);
    }

    .ctrl-range {
      width: 100%;
      accent-color: var(--accent);
      cursor: pointer;
      height: 4px;
    }

    .ctrl-btn {
      width: 100%;
      height: 32px;
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      color: var(--text-secondary);
      font-family: var(--font-ui);
      font-size: 12px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.15s var(--ease);
    }
    .ctrl-btn:hover {
      color: var(--text-primary);
      border-color: var(--border-hover);
      background: var(--bg-surface);
    }
    .ctrl-btn.active {
      color: var(--accent);
      border-color: var(--accent);
      background: var(--accent-muted);
    }

    /* Legend */
    .legend-items { display: flex; flex-direction: column; gap: 6px; padding: 0 4px; }

    .legend-item {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 11px;
      color: var(--text-secondary);
    }

    .legend-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    /* Stats */
    .stats-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
      padding: 0 4px;
    }

    .stat-cell {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 8px;
      text-align: center;
    }

    .stat-val {
      font-family: var(--font-mono);
      font-size: 16px;
      font-weight: 500;
      color: var(--text-primary);
    }

    .stat-label {
      font-size: 9px;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--text-tertiary);
      margin-top: 2px;
    }

    /* Left panel footer */
    .lp-footer {
      margin-top: auto;
      padding: 12px;
      border-top: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .lp-footer-btn {
      width: 100%;
      height: 30px;
      background: transparent;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      color: var(--text-tertiary);
      font-family: var(--font-ui);
      font-size: 11px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.15s var(--ease);
    }
    .lp-footer-btn:hover {
      color: var(--text-secondary);
      border-color: var(--border-hover);
    }

    .lp-version {
      font-size: 10px;
      color: var(--text-tertiary);
      text-align: center;
      opacity: 0.5;
    }

    /* System info rows */
    .sys-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      padding: 4px;
    }
    .sys-row-label { color: var(--text-tertiary); }
    .sys-row-val { color: var(--text-secondary); font-weight: 500; }

    /* ---- Main Area ---- */
    #main-area {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
    }

    /* ---- Topbar ---- */
    #topbar {
      height: 48px;
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      flex-shrink: 0;
      z-index: 15;
    }

    .tb-left {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }

    .tb-icon-btn {
      width: 32px;
      height: 32px;
      background: transparent;
      border: 1px solid transparent;
      border-radius: var(--radius-sm);
      color: var(--text-tertiary);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s var(--ease);
      flex-shrink: 0;
    }
    .tb-icon-btn:hover {
      color: var(--text-primary);
      background: var(--bg-elevated);
      border-color: var(--border);
    }

    .tb-breadcrumb {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      min-width: 0;
    }

    .tb-bc-root {
      color: var(--text-tertiary);
      font-weight: 500;
      flex-shrink: 0;
    }

    .tb-bc-sep {
      color: var(--text-tertiary);
      opacity: 0.4;
      flex-shrink: 0;
    }

    .tb-bc-target {
      font-family: var(--font-mono);
      font-size: 13px;
      font-weight: 500;
      color: var(--text-primary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .tb-right {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }

    /* Pill badges in topbar */
    .tb-pill {
      height: 24px;
      padding: 0 10px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 4px;
      white-space: nowrap;
      border: 1px solid var(--border);
      background: var(--bg-elevated);
      color: var(--text-secondary);
    }
    .tb-pill .pill-val {
      font-family: var(--font-mono);
      font-weight: 600;
      color: var(--text-primary);
    }

    .tb-pill.risk-high { border-color: var(--red); color: var(--red); background: var(--red-muted); }
    .tb-pill.risk-medium { border-color: var(--amber); color: var(--amber); background: var(--amber-muted); }
    .tb-pill.risk-low { border-color: var(--green); color: var(--green); background: var(--green-muted); }

    .tb-divider {
      width: 1px;
      height: 20px;
      background: var(--border);
      flex-shrink: 0;
    }

    /* ---- Canvas Area ---- */
    #canvas-area {
      flex: 1;
      position: relative;
      display: flex;
      min-height: 0;
      overflow: hidden;
    }

    #graph-canvas {
      flex: 1;
      position: relative;
      overflow: hidden;
      background: var(--bg-base);
      /* Dot grid pattern */
      background-image: radial-gradient(circle, var(--canvas-dot) 1px, transparent 1px);
      background-size: 24px 24px;
    }

    #vis-container {
      position: absolute;
      inset: 0;
      z-index: 2;
    }

    /* ---- Floating Search ---- */
    .search-wrap {
      position: absolute;
      top: 12px;
      left: 12px;
      z-index: 10;
      width: 280px;
    }

    .search-box {
      position: relative;
    }

    .search-input {
      width: 100%;
      height: 36px;
      padding: 0 12px 0 34px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      color: var(--text-primary);
      font-family: var(--font-ui);
      font-size: 13px;
      outline: none;
      box-shadow: var(--shadow-md);
      transition: border-color 0.15s var(--ease), box-shadow 0.15s var(--ease);
    }
    .search-input:focus {
      border-color: var(--accent);
      box-shadow: var(--shadow-md), 0 0 0 3px var(--accent-muted);
    }
    .search-input::placeholder { color: var(--text-tertiary); }

    .search-icon {
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-tertiary);
      pointer-events: none;
    }

    .search-kbd {
      position: absolute;
      right: 8px;
      top: 50%;
      transform: translateY(-50%);
      padding: 2px 6px;
      font-family: var(--font-mono);
      font-size: 10px;
      color: var(--text-tertiary);
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 4px;
      pointer-events: none;
    }

    .search-results {
      position: absolute;
      top: calc(100% + 4px);
      left: 0;
      right: 0;
      max-height: 240px;
      overflow-y: auto;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-lg);
      display: none;
      z-index: 11;
    }
    .search-results.visible { display: block; }

    .search-result-item {
      padding: 8px 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      color: var(--text-secondary);
      transition: background 0.1s var(--ease);
    }
    .search-result-item:hover,
    .search-result-item.active {
      background: var(--bg-elevated);
      color: var(--text-primary);
    }
    .search-result-item .sr-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      flex-shrink: 0;
    }
    .search-result-item .sr-name {
      font-family: var(--font-mono);
      font-size: 12px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .search-result-item .sr-path {
      font-size: 10px;
      color: var(--text-tertiary);
      margin-left: auto;
      flex-shrink: 0;
    }

    /* ---- Floating Canvas Toolbar ---- */
    .canvas-toolbar {
      position: absolute;
      bottom: 16px;
      right: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 4px;
      display: flex;
      flex-direction: column;
      gap: 2px;
      box-shadow: var(--shadow-md);
      z-index: 10;
    }

    .ct-btn {
      width: 32px;
      height: 32px;
      background: transparent;
      border: none;
      border-radius: var(--radius-sm);
      color: var(--text-tertiary);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s var(--ease);
    }
    .ct-btn:hover {
      color: var(--text-primary);
      background: var(--bg-elevated);
    }
    .ct-sep {
      width: 20px;
      height: 1px;
      background: var(--border);
      margin: 2px auto;
    }

    /* ---- Floating Legend ---- */
    .canvas-legend {
      position: absolute;
      bottom: 16px;
      left: 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      padding: 10px 14px;
      box-shadow: var(--shadow-md);
      z-index: 10;
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .cl-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .cl-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    .cl-label {
      font-size: 11px;
      color: var(--text-tertiary);
      white-space: nowrap;
    }

    /* ---- Minimap ---- */
    .minimap-wrap {
      position: absolute;
      bottom: 60px;
      right: 16px;
      width: 140px;
      height: 100px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-md);
      z-index: 10;
      overflow: hidden;
      opacity: 0.7;
      transition: opacity 0.15s var(--ease);
    }
    .minimap-wrap:hover { opacity: 1; }
    .minimap-canvas {
      width: 100%;
      height: 100%;
    }

    /* ---- Inspector Panel (right slide-in) ---- */
    #inspector {
      position: absolute;
      right: 0;
      top: 0;
      bottom: 0;
      width: 370px;
      background: var(--bg-surface);
      border-left: 1px solid var(--border);
      box-shadow: var(--shadow-lg);
      z-index: 25;
      display: flex;
      flex-direction: column;
      transform: translateX(100%);
      transition: transform 0.25s var(--ease);
    }
    #inspector.open { transform: translateX(0); }

    .insp-header {
      height: 48px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 16px;
      border-bottom: 1px solid var(--border);
      flex-shrink: 0;
    }

    .insp-title {
      font-size: 12px;
      font-weight: 600;
      color: var(--text-secondary);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .insp-title svg { color: var(--accent); }

    .insp-close {
      width: 28px;
      height: 28px;
      background: transparent;
      border: none;
      border-radius: var(--radius-sm);
      color: var(--text-tertiary);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s var(--ease);
    }
    .insp-close:hover {
      color: var(--text-primary);
      background: var(--bg-elevated);
    }

    .insp-body {
      flex: 1;
      overflow-y: auto;
      padding: 16px;
    }

    /* Inspector cards */
    .insp-card {
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      padding: 12px;
      margin-bottom: 12px;
      transition: border-color 0.15s var(--ease);
    }
    .insp-card:hover { border-color: var(--border-hover); }

    .insp-card-label {
      font-size: 10px;
      font-weight: 600;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--text-tertiary);
      margin-bottom: 6px;
    }

    .insp-symbol {
      font-family: var(--font-mono);
      font-size: 14px;
      font-weight: 500;
      color: var(--text-primary);
      word-break: break-all;
      line-height: 1.4;
    }

    .insp-badge {
      display: inline-flex;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.03em;
    }
    .insp-badge.target { color: var(--red); background: var(--red-muted); }
    .insp-badge.inner { color: var(--cyan); background: var(--cyan-muted); }
    .insp-badge.mid { color: var(--amber); background: var(--amber-muted); }
    .insp-badge.outer { color: var(--indigo); background: var(--indigo-muted); }

    .insp-location {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-secondary);
      word-break: break-all;
      line-height: 1.5;
    }

    /* Code preview */
    .code-preview {
      background: var(--bg-base);
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      overflow: hidden;
      margin-top: 8px;
    }

    .code-head {
      background: var(--bg-elevated);
      padding: 6px 10px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .code-filename {
      font-family: var(--font-mono);
      font-size: 10px;
      color: var(--text-tertiary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 65%;
    }
    .code-line-tag {
      font-family: var(--font-mono);
      font-size: 9px;
      color: var(--text-secondary);
      background: var(--bg-surface);
      padding: 2px 6px;
      border-radius: 3px;
    }

    .code-body {
      padding: 8px 0;
      overflow-x: auto;
    }

    .code-line {
      display: flex;
      padding: 1px 12px;
      line-height: 1.65;
    }
    .code-line.hl {
      background: var(--accent-muted);
      border-left: 2px solid var(--accent);
      padding-left: 10px;
    }
    .code-ln {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-tertiary);
      text-align: right;
      min-width: 28px;
      user-select: none;
      margin-right: 12px;
      opacity: 0.5;
    }
    .code-text {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-primary);
      white-space: pre;
    }

    /* Inspector actions */
    .insp-actions {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 16px;
    }

    .insp-action {
      height: 32px;
      border: 1px solid var(--border);
      border-radius: var(--radius-sm);
      background: var(--bg-elevated);
      color: var(--text-secondary);
      font-family: var(--font-ui);
      font-size: 11px;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      text-decoration: none;
      transition: all 0.15s var(--ease);
    }
    .insp-action:hover {
      color: var(--text-primary);
      border-color: var(--border-hover);
    }
    a.insp-action { display: flex; }

    .insp-action.primary {
      background: var(--accent);
      border-color: var(--accent);
      color: #000;
      font-weight: 600;
    }
    .insp-action.primary:hover {
      background: var(--accent-hover);
      border-color: var(--accent-hover);
    }

    /* Inspector empty state */
    .insp-empty {
      padding: 40px 16px;
      text-align: center;
      color: var(--text-tertiary);
    }
    .insp-empty svg {
      margin-bottom: 12px;
      opacity: 0.3;
    }
    .insp-empty p {
      font-size: 12px;
      line-height: 1.6;
    }

    /* ---- Context Menu ---- */
    .ctx-menu {
      position: fixed;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-md);
      box-shadow: var(--shadow-lg);
      min-width: 180px;
      padding: 4px;
      z-index: 100;
      display: none;
    }
    .ctx-menu.visible { display: block; }

    .ctx-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 7px 10px;
      font-size: 12px;
      color: var(--text-secondary);
      border-radius: 4px;
      cursor: pointer;
      transition: all 0.1s var(--ease);
    }
    .ctx-item:hover {
      background: var(--bg-elevated);
      color: var(--text-primary);
    }
    .ctx-item svg { flex-shrink: 0; }
    .ctx-sep {
      height: 1px;
      background: var(--border);
      margin: 4px 0;
    }

    /* ---- Toast ---- */
    #toast {
      position: fixed;
      bottom: 24px;
      left: 50%;
      transform: translate(-50%, 12px);
      padding: 8px 16px;
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: 20px;
      color: var(--text-primary);
      font-size: 12px;
      font-weight: 500;
      box-shadow: var(--shadow-md);
      z-index: 200;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.2s var(--ease), transform 0.2s var(--ease);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    #toast.visible {
      opacity: 1;
      transform: translate(-50%, 0);
    }

    /* ---- Keyboard shortcuts overlay ---- */
    .kbd-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.6);
      z-index: 300;
      display: none;
      align-items: center;
      justify-content: center;
    }
    .kbd-overlay.visible { display: flex; }

    .kbd-modal {
      background: var(--bg-surface);
      border: 1px solid var(--border);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow-lg);
      padding: 24px;
      width: 380px;
      max-height: 80vh;
      overflow-y: auto;
    }
    .kbd-modal-title {
      font-family: var(--font-display);
      font-size: 16px;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 16px;
    }
    .kbd-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 6px 0;
      font-size: 12px;
      color: var(--text-secondary);
    }
    .kbd-key {
      font-family: var(--font-mono);
      font-size: 11px;
      padding: 2px 6px;
      background: var(--bg-elevated);
      border: 1px solid var(--border);
      border-radius: 4px;
      color: var(--text-primary);
    }

    /* ---- Responsive ---- */
    @media (max-width: 900px) {
      #left-panel { position: absolute; left: 0; top: 0; bottom: 0; z-index: 30; box-shadow: var(--shadow-lg); }
      #left-panel.collapsed { margin-left: -248px; }
      #inspector { width: 100%; }
    }

    @media (prefers-reduced-motion: reduce) {
      *, *::before, *::after { transition-duration: 0.01ms !important; animation-duration: 0.01ms !important; }
    }
  </style>
</head>
<body>
  <!-- Context Menu -->
  <div class="ctx-menu" id="ctx-menu">
    <div class="ctx-item" id="ctx-focus">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>
      Focus node
    </div>
    <div class="ctx-item" id="ctx-trace">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
      Trace to target
    </div>
    <div class="ctx-sep"></div>
    <div class="ctx-item" id="ctx-copy">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
      Copy symbol name
    </div>
    <div class="ctx-item" id="ctx-editor">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
      Open in editor
    </div>
  </div>

  <!-- Keyboard Shortcuts Modal -->
  <div class="kbd-overlay" id="kbd-overlay">
    <div class="kbd-modal">
      <div class="kbd-modal-title">Keyboard Shortcuts</div>
      <div class="kbd-row"><span>Search symbols</span><span class="kbd-key">/</span></div>
      <div class="kbd-row"><span>Command palette</span><span><span class="kbd-key">Ctrl</span> <span class="kbd-key">K</span></span></div>
      <div class="kbd-row"><span>Fit to viewport</span><span class="kbd-key">F</span></div>
      <div class="kbd-row"><span>Solar layout</span><span class="kbd-key">1</span></div>
      <div class="kbd-row"><span>Force layout</span><span class="kbd-key">2</span></div>
      <div class="kbd-row"><span>Tree layout</span><span class="kbd-key">3</span></div>
      <div class="kbd-row"><span>Group by file</span><span class="kbd-key">G</span></div>
      <div class="kbd-row"><span>Toggle sidebar</span><span class="kbd-key">B</span></div>
      <div class="kbd-row"><span>Clear selection</span><span class="kbd-key">Esc</span></div>
      <div class="kbd-row"><span>Toggle theme</span><span class="kbd-key">T</span></div>
      <div class="kbd-row"><span>Show shortcuts</span><span class="kbd-key">?</span></div>
    </div>
  </div>

  <!-- Toast -->
  <div id="toast"></div>

  <!-- App Shell -->
  <div id="app">
    <!-- Left Panel -->
    <aside id="left-panel">
      <div class="lp-header">
        <a href="https://n3mo.shop" class="lp-logo" target="_blank" rel="noopener">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="160 30 130 130" width="22" height="22">
            <defs><linearGradient id="ng" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="#facc15"/><stop offset="100%" stop-color="#f59e0b"/></linearGradient></defs>
            <path fill="none" stroke="url(#ng)" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" d="M 190 140 L 190 50 L 270 140 L 270 50"/>
            <circle fill="var(--bg-base)" stroke="url(#ng)" stroke-width="4" cx="190" cy="140" r="7"/>
            <circle fill="var(--bg-base)" stroke="url(#ng)" stroke-width="4" cx="190" cy="50" r="7"/>
            <circle fill="var(--bg-base)" stroke="url(#ng)" stroke-width="4" cx="270" cy="140" r="7"/>
            <circle fill="var(--bg-base)" stroke="url(#ng)" stroke-width="4" cx="270" cy="50" r="7"/>
          </svg>
          <span class="lp-logo-text">N3MO</span>
        </a>
      </div>

      <div class="lp-scroll">
        <div class="lp-section">
          <div class="lp-section-title">Layout</div>
          <div class="ctrl-group">
            <label class="ctrl-label" for="layout-select">Graph layout</label>
            <select id="layout-select" class="ctrl-select">
              <option value="solar">Radial Orbital</option>
              <option value="force">Force Directed</option>
              <option value="tree">Impact Tree</option>
            </select>
          </div>
          <div class="ctrl-group">
            <button class="ctrl-btn" id="btn-group" type="button">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
              Group by file
            </button>
          </div>
        </div>

        <div class="lp-section">
          <div class="lp-section-title">Depth</div>
          <div class="ctrl-group">
            <div class="ctrl-slider-row">
              <label class="ctrl-label" for="depth-slider" style="margin:0">Visible depth</label>
              <span class="ctrl-slider-val" id="depth-label">__MAX_DEPTH__</span>
            </div>
            <input id="depth-slider" class="ctrl-range" type="range" min="1" max="__MAX_DEPTH__" value="__MAX_DEPTH__">
          </div>
        </div>

        <div class="lp-section">
          <div class="lp-section-title">Legend</div>
          <div class="legend-items">
            <div class="legend-item"><span class="legend-dot" style="background:var(--red)"></span>Target</div>
            <div class="legend-item"><span class="legend-dot" style="background:var(--cyan)"></span>Direct (Depth 1)</div>
            <div class="legend-item"><span class="legend-dot" style="background:var(--amber)"></span>Indirect (Depth 2)</div>
            <div class="legend-item"><span class="legend-dot" style="background:var(--indigo)"></span>Deep (Depth ≥ 3)</div>
          </div>
        </div>

        <div class="lp-section">
          <div class="lp-section-title">Statistics</div>
          <div class="stats-grid">
            <div class="stat-cell">
              <div class="stat-val" id="stat-direct">0</div>
              <div class="stat-label">Direct</div>
            </div>
            <div class="stat-cell">
              <div class="stat-val" id="stat-total">0</div>
              <div class="stat-label">Total</div>
            </div>
            <div class="stat-cell">
              <div class="stat-val" id="stat-files">0</div>
              <div class="stat-label">Files</div>
            </div>
            <div class="stat-cell">
              <div class="stat-val" id="stat-depth">0</div>
              <div class="stat-label">Max Depth</div>
            </div>
          </div>
        </div>

        <div class="lp-section">
          <div class="lp-section-title">System</div>
          <div class="sys-row"><span class="sys-row-label">Engine</span><span class="sys-row-val">PostgreSQL</span></div>
          <div class="sys-row"><span class="sys-row-label">Parser</span><span class="sys-row-val">Tree-sitter</span></div>
          <div class="sys-row"><span class="sys-row-label">License</span><span class="sys-row-val">PolyForm NC</span></div>
        </div>
      </div>

      <div class="lp-footer">
        <button class="lp-footer-btn" id="btn-shortcuts" type="button">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M6 8h.001M10 8h.001M14 8h.001M18 8h.001M8 12h.001M12 12h.001M16 12h.001M18 16H6"/></svg>
          Shortcuts
        </button>
        <div class="lp-version">v2.1.0</div>
      </div>
    </aside>

    <!-- Main Content -->
    <main id="main-area">
      <!-- Topbar -->
      <header id="topbar">
        <div class="tb-left">
          <button class="tb-icon-btn" id="nav-toggle" aria-label="Toggle sidebar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/></svg>
          </button>
          <div class="tb-breadcrumb">
            <span class="tb-bc-root">Impact Graph</span>
            <svg class="tb-bc-sep" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            <span class="tb-bc-target" id="target-name"></span>
          </div>
        </div>
        <div class="tb-right">
          <div class="tb-pill"><span>Nodes</span>&nbsp;<span class="pill-val" id="pill-nodes">0</span></div>
          <div class="tb-pill"><span>Edges</span>&nbsp;<span class="pill-val" id="pill-edges">0</span></div>
          <div class="tb-pill" id="risk-pill">—</div>
          <div class="tb-divider"></div>
          <button class="tb-icon-btn" id="btn-theme" aria-label="Toggle theme" title="Toggle theme (T)">
            <svg id="theme-icon-sun" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
            <svg id="theme-icon-moon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:none"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
          </button>
          <button class="tb-icon-btn" id="btn-export-top" aria-label="Export PNG" title="Export PNG">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
          </button>
        </div>
      </header>

      <!-- Canvas Area -->
      <div id="canvas-area">
        <div id="graph-canvas">
          <div id="vis-container"></div>

          <!-- Search -->
          <div class="search-wrap">
            <div class="search-box">
              <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
              <input id="symbol-search" class="search-input" type="text" placeholder="Search symbols..." autocomplete="off" spellcheck="false">
              <span class="search-kbd">/</span>
            </div>
            <div class="search-results" id="search-results"></div>
          </div>

          <!-- Legend (compact horizontal) -->
          <div class="canvas-legend">
            <div class="cl-item"><span class="cl-dot" style="background:var(--red)"></span><span class="cl-label">Target</span></div>
            <div class="cl-item"><span class="cl-dot" style="background:var(--cyan)"></span><span class="cl-label">Direct</span></div>
            <div class="cl-item"><span class="cl-dot" style="background:var(--amber)"></span><span class="cl-label">Indirect</span></div>
            <div class="cl-item"><span class="cl-dot" style="background:var(--indigo)"></span><span class="cl-label">Deep</span></div>
          </div>

          <!-- Minimap -->
          <div class="minimap-wrap" id="minimap-wrap">
            <canvas class="minimap-canvas" id="minimap-canvas"></canvas>
          </div>

          <!-- Toolbar -->
          <div class="canvas-toolbar">
            <button class="ct-btn" id="btn-zoom-in" title="Zoom in" aria-label="Zoom in">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
            <button class="ct-btn" id="btn-zoom-out" title="Zoom out" aria-label="Zoom out">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>
            </button>
            <div class="ct-sep"></div>
            <button class="ct-btn" id="btn-fit" title="Fit to viewport (F)" aria-label="Fit to viewport">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
            </button>
            <button class="ct-btn" id="btn-reset" title="Reset view" aria-label="Reset view">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
            </button>
          </div>
        </div>

        <!-- Inspector Panel -->
        <aside id="inspector">
          <div class="insp-header">
            <div class="insp-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
              Inspector
            </div>
            <button class="insp-close" id="insp-close" aria-label="Close inspector">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </div>
          <div class="insp-body" id="insp-body">
            <div class="insp-empty">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
              <p>Select a node in the graph to inspect its call telemetry, source location, and code context.</p>
            </div>
          </div>
        </aside>
      </div>
    </main>
  </div>

  <script>
    /* ============================================================
       DATA & CONFIG
       ============================================================ */
    const targetName = __TARGET_JSON__;
    const nodesData = __NODES_JSON__;
    const edgesData = __EDGES_JSON__;
    const configuredMaxDepth = __MAX_DEPTH__;
    const actualMaxDepth = Math.max(1, ...nodesData.map(n => n.group));

    let currentDepth = Math.min(configuredMaxDepth, actualMaxDepth);
    let currentLayout = 'solar';
    let groupByFile = false;
    let selectedId = null;
    let ctxNodeId = null;

    /* ============================================================
       THEME SYSTEM
       ============================================================ */
    const themeConfig = {
      dark: {
        text: '#fafafa',
        stroke: '#09090b',
        edge: 'rgba(255,255,255,0.06)',
        edgeHover: 'rgba(255,255,255,0.2)',
        orbit: 'rgba(255,255,255,0.03)',
        palette: ['#818cf8', '#60a5fa', '#34d399', '#fbbf24', '#f472b6', '#a78bfa'],
        nodes: {
          target: { bg: '#1c1917', border: '#f43f5e' },
          inner:  { bg: '#0c1a1f', border: '#06b6d4' },
          mid:    { bg: '#1a1506', border: '#f59e0b' },
          outer:  { bg: '#111318', border: '#6366f1' }
        }
      },
      light: {
        text: '#09090b',
        stroke: '#ffffff',
        edge: 'rgba(0,0,0,0.06)',
        edgeHover: 'rgba(0,0,0,0.15)',
        orbit: 'rgba(0,0,0,0.03)',
        palette: ['#4f46e5', '#2563eb', '#059669', '#d97706', '#db2777', '#7c3aed'],
        nodes: {
          target: { bg: '#fef2f2', border: '#e11d48' },
          inner:  { bg: '#ecfeff', border: '#0891b2' },
          mid:    { bg: '#fffbeb', border: '#b45309' },
          outer:  { bg: '#eef2ff', border: '#4f46e5' }
        }
      }
    };

    function isDark() { return !document.body.classList.contains('light-mode'); }
    function getTheme() { return isDark() ? themeConfig.dark : themeConfig.light; }

    /* ============================================================
       POPULATE STATS
       ============================================================ */
    document.getElementById('target-name').textContent = targetName;
    const directCount = nodesData.filter(n => n.group === 1).length;
    const totalImpacted = nodesData.filter(n => n.group > 0).length;
    const fileCount = new Set(nodesData.filter(n => n.path).map(n => n.path)).size;
    document.getElementById('stat-direct').textContent = directCount;
    document.getElementById('stat-total').textContent = totalImpacted;
    document.getElementById('stat-files').textContent = fileCount;
    document.getElementById('stat-depth').textContent = actualMaxDepth;
    document.getElementById('pill-nodes').textContent = nodesData.length;
    document.getElementById('pill-edges').textContent = edgesData.length;

    const riskPill = document.getElementById('risk-pill');
    if (totalImpacted > 100) { riskPill.textContent = 'High Impact'; riskPill.className = 'tb-pill risk-high'; }
    else if (totalImpacted > 20) { riskPill.textContent = 'Moderate'; riskPill.className = 'tb-pill risk-medium'; }
    else { riskPill.textContent = 'Low Impact'; riskPill.className = 'tb-pill risk-low'; }

    /* ============================================================
       NODE & EDGE BUILDERS
       ============================================================ */
    function fileColor(path) {
      let hash = 0;
      for (const c of path || 'x') hash = ((hash << 5) - hash) + c.charCodeAt(0);
      const pal = getTheme().palette;
      return pal[Math.abs(hash) % pal.length];
    }

    function buildNode(node) {
      const g = node.group;
      const t = getTheme();
      const nt = g === 0 ? t.nodes.target : g === 1 ? t.nodes.inner : g === 2 ? t.nodes.mid : t.nodes.outer;
      const border = groupByFile && g !== 0 ? fileColor(node.path) : nt.border;
      const clean = { ...node }; delete clean.group;
      return {
        ...clean,
        depth: g,
        level: g,
        shape: 'dot',
        size: g === 0 ? 24 : g === 1 ? 12 : g === 2 ? 9 : Math.max(6, 10 - g),
        borderWidth: g === 0 ? 3 : 1.5,
        borderWidthSelected: 3,
        font: {
          face: 'JetBrains Mono, monospace',
          color: t.text,
          size: g === 0 ? 12 : 10,
          strokeWidth: 3,
          strokeColor: t.stroke
        },
        color: {
          background: nt.bg,
          border: border,
          highlight: { background: border, border: t.text },
          hover: { background: nt.bg, border: t.text }
        }
      };
    }

    function buildEdge(edge, idx) {
      const t = getTheme();
      return {
        ...edge,
        id: edge.id || `edge-${idx}`,
        arrows: { to: { enabled: true, scaleFactor: 0.4 } },
        color: { color: t.edge, highlight: t.nodes.target.border, hover: t.edgeHover, opacity: 0.7 },
        width: 0.8,
        selectionWidth: 1.5,
        hoverWidth: 1,
        smooth: currentLayout === 'tree'
          ? { enabled: true, type: 'cubicBezier', forceDirection: 'horizontal', roundness: 0.5 }
          : { enabled: true, type: 'curvedCW', roundness: 0.06 }
      };
    }

    /* ============================================================
       VIS NETWORK INIT
       ============================================================ */
    const nodes = new vis.DataSet(nodesData.map(buildNode));
    const edges = new vis.DataSet(edgesData.map(buildEdge));
    const container = document.getElementById('vis-container');

    const network = new vis.Network(container, { nodes, edges }, {
      autoResize: true,
      physics: false,
      interaction: {
        hover: true,
        multiselect: false,
        navigationButtons: false,
        keyboard: { enabled: false },
        zoomView: true,
        dragView: true
      },
      layout: { improvedLayout: false }
    });

    /* ============================================================
       LAYOUT ENGINES
       ============================================================ */
    function solarPositions() {
      const pos = {};
      const visible = nodesData.filter(n => n.group <= currentDepth);
      pos[targetName] = { x: 0, y: 0 };
      let baseR = 160;
      for (let d = 1; d <= currentDepth; d++) {
        const ring = visible.filter(n => n.group === d);
        ring.sort((a, b) => a.label.localeCompare(b.label));
        if (!ring.length) continue;
        const maxPer = 10 + d * 5;
        const subs = Math.ceil(ring.length / maxPer);
        ring.forEach((n, i) => {
          const si = i % subs;
          const r = baseR + si * 45;
          const cnt = Math.ceil(ring.length / subs);
          const ni = Math.floor(i / subs);
          const off = (d % 2 === 0 ? Math.PI / 5 : -Math.PI / 2) + si * (Math.PI / 10);
          const a = off + (Math.PI * 2 * ni) / Math.max(cnt, 1);
          pos[n.id] = { x: Math.cos(a) * r, y: Math.sin(a) * r };
        });
        baseR += subs * 45 + 80;
      }
      return pos;
    }

    function visibleGraph() {
      const vn = nodesData.filter(n => n.group <= currentDepth).map(buildNode);
      const ids = new Set(vn.map(n => n.id));
      const ve = edgesData.filter(e => ids.has(e.from) && ids.has(e.to)).map((e, i) => buildEdge(e, i));
      nodes.clear(); edges.clear();
      nodes.add(vn); edges.add(ve);
      const s = network.getScale();
      updateLabels(s > 0.45, true);
    }

    function disableHierarchical() {
      network.setOptions({ layout: { hierarchical: { enabled: false } } });
    }

    function applySolarLayout(animate = true) {
      currentLayout = 'solar';
      disableHierarchical();
      network.setOptions({ physics: false });
      visibleGraph();
      const pos = solarPositions();
      nodes.update(nodes.get().map(n => ({ id: n.id, x: pos[n.id]?.x || 0, y: pos[n.id]?.y || 0, fixed: { x: true, y: true } })));
      setTimeout(() => network.fit({ animation: animate ? { duration: 500, easingFunction: 'easeInOutQuad' } : false }), 30);
    }

    function applyForceLayout() {
      currentLayout = 'force';
      disableHierarchical();
      visibleGraph();
      nodes.update(nodes.get().map(n => ({ id: n.id, fixed: false })));
      network.setOptions({
        physics: {
          enabled: true,
          solver: 'forceAtlas2Based',
          forceAtlas2Based: { gravitationalConstant: -55, centralGravity: 0.012, springLength: 125, springConstant: 0.055, damping: 0.5 },
          stabilization: { enabled: true, iterations: 150, fit: true }
        }
      });
    }

    function applyTreeLayout() {
      currentLayout = 'tree';
      disableHierarchical();
      visibleGraph();
      nodes.update(nodes.get().map(n => ({ id: n.id, fixed: false })));
      network.setOptions({
        physics: { enabled: false },
        layout: {
          hierarchical: {
            enabled: true, direction: 'LR', sortMethod: 'directed',
            levelSeparation: 180, nodeSpacing: 80,
            parentCentralization: true, blockShifting: true, edgeMinimization: true
          }
        }
      });
      setTimeout(() => network.fit({ animation: { duration: 400 } }), 50);
    }

    network.on('stabilizationIterationsDone', () => {
      if (currentLayout === 'force') {
        network.setOptions({ physics: false });
        showToast('Layout stabilized');
      }
    });

    /* ============================================================
       LABEL VISIBILITY (zoom-dependent)
       ============================================================ */
    let prevLabels = true;
    function updateLabels(show, force = false) {
      if (show === prevLabels && !force) return;
      prevLabels = show;
      nodes.update(nodes.get().map(n => {
        const isT = n.depth === 0;
        const isS = n.id === selectedId;
        return { id: n.id, font: { size: (show || isT || isS) ? (isT ? 12 : 10) : 0 } };
      }));
    }

    network.on('zoom', () => updateLabels(network.getScale() > 0.45));

    /* ============================================================
       ORBIT DRAWING (solar layout circles)
       ============================================================ */
    network.on('beforeDrawing', ctx => {
      if (currentLayout !== 'solar') return;
      ctx.save();
      ctx.setLineDash([4, 8]);
      ctx.lineWidth = 0.8 / network.getScale();
      ctx.strokeStyle = getTheme().orbit;
      const visible = nodesData.filter(n => n.group <= currentDepth);
      let baseR = 160;
      for (let d = 1; d <= currentDepth; d++) {
        const ring = visible.filter(n => n.group === d);
        if (!ring.length) continue;
        const subs = Math.ceil(ring.length / (10 + d * 5));
        for (let s = 0; s < subs; s++) {
          ctx.beginPath();
          ctx.arc(0, 0, baseR + s * 45, 0, Math.PI * 2);
          ctx.stroke();
        }
        baseR += subs * 45 + 80;
      }
      ctx.restore();
    });

    /* ============================================================
       PATH TRACING
       ============================================================ */
    function traceToTarget(startId) {
      const tn = new Set();
      const te = new Set();
      const path = [];
      function find(id) {
        path.push(id);
        if (id === targetName) {
          path.forEach(n => tn.add(n));
          for (let i = 0; i < path.length - 1; i++) {
            const e = edgesData.find(x => x.from === path[i] && x.to === path[i+1]);
            if (e) te.add(e.id || `edge-${edgesData.indexOf(e)}`);
          }
          path.pop(); return;
        }
        for (const e of edgesData.filter(x => x.from === id)) {
          if (!path.includes(e.to)) find(e.to);
        }
        path.pop();
      }
      find(startId);
      if (!tn.size) { tn.add(startId); tn.add(targetName); }

      const s = network.getScale();
      const show = s > 0.45;
      nodes.update(nodes.get().map(n => ({
        id: n.id,
        opacity: tn.has(n.id) ? 1 : 0.1,
        font: { size: (show || n.depth === 0 || n.id === selectedId || n.id === startId) ? (n.depth === 0 ? 12 : 10) : 0 }
      })));
      const t = getTheme();
      edges.update(edges.get().map(e => ({
        id: e.id,
        color: te.has(e.id) ? { color: t.nodes.target.border, opacity: 1 } : { color: t.edge, opacity: 0.08 },
        width: te.has(e.id) ? 2 : 0.8
      })));
    }

    function clearTrace() {
      const s = network.getScale();
      const show = s > 0.45;
      nodes.update(nodes.get().map(n => ({
        id: n.id,
        opacity: 1,
        font: { size: (show || n.depth === 0 || n.id === selectedId) ? (n.depth === 0 ? 12 : 10) : 0 }
      })));
      const t = getTheme();
      edges.update(edges.get().map(e => ({
        id: e.id,
        color: { color: t.edge, highlight: t.nodes.target.border, hover: t.edgeHover, opacity: 0.7 },
        width: 0.8
      })));
    }

    /* ============================================================
       INSPECTOR PANEL
       ============================================================ */
    function escapeHtml(v) {
      return String(v).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;');
    }
    function basename(p) { if (!p) return ''; const s = p.split('/'); return s[s.length-1]; }

    function renderCode(node) {
      if (!node.code_context || !node.code_context.length) return '';
      const lines = node.code_context.map(([ln, lc]) => {
        const hl = ln === node.line;
        return `<div class="code-line ${hl ? 'hl' : ''}"><span class="code-ln">${ln}</span><span class="code-text">${escapeHtml(lc)}</span></div>`;
      }).join('');
      return `
        <div class="insp-card">
          <div class="insp-card-label">Code Preview</div>
          <div class="code-preview">
            <div class="code-head">
              <span class="code-filename" title="${escapeHtml(node.path)}">${escapeHtml(basename(node.path))}</span>
              <span class="code-line-tag">L${node.line}</span>
            </div>
            <div class="code-body">${lines}</div>
          </div>
        </div>`;
    }

    const emptyState = `<div class="insp-empty"><svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg><p>Select a node in the graph to inspect its call telemetry, source location, and code context.</p></div>`;

    function inspectNode(id) {
      const node = nodesData.find(n => n.id === id);
      if (!node) return;
      selectedId = id;
      document.getElementById('inspector').classList.add('open');
      traceToTarget(id);

      const cls = node.group === 0 ? 'target' : node.group === 1 ? 'inner' : node.group === 2 ? 'mid' : 'outer';
      const clsText = node.group === 0 ? 'Target' : node.group === 1 ? 'Direct · Depth 1' : node.group === 2 ? 'Indirect · Depth 2' : `Deep · Depth ${node.group}`;
      const loc = node.path ? `${node.path}:${node.line || 1}` : 'Target definition';
      const edLink = node.path ? `vscode://file/${encodeURI(node.path)}:${node.line || 1}` : '#';

      document.getElementById('insp-body').innerHTML = `
        <div class="insp-card">
          <div class="insp-card-label">Symbol</div>
          <div class="insp-symbol">${escapeHtml(node.label)}</div>
        </div>
        <div class="insp-card">
          <div class="insp-card-label">Impact Depth</div>
          <span class="insp-badge ${cls}">${clsText}</span>
        </div>
        <div class="insp-card">
          <div class="insp-card-label">Location</div>
          <div class="insp-location">${escapeHtml(loc)}</div>
        </div>
        ${renderCode(node)}
        <div class="insp-actions">
          <a class="insp-action primary" href="${edLink}">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            Editor
          </a>
          <button class="insp-action" id="act-focus" type="button">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>
            Focus
          </button>
          <button class="insp-action" id="act-copy" type="button">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
            Copy
          </button>
          <button class="insp-action" id="act-clear" type="button">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            Clear
          </button>
        </div>`;

      document.getElementById('act-focus').onclick = () => network.focus(id, { scale: 1.35, animation: { duration: 400 } });
      document.getElementById('act-copy').onclick = async () => { await navigator.clipboard.writeText(loc); showToast('Path copied'); };
      document.getElementById('act-clear').onclick = () => clearSelection();
    }

    function clearSelection() {
      selectedId = null;
      network.unselectAll();
      clearTrace();
      document.getElementById('insp-body').innerHTML = emptyState;
      document.getElementById('inspector').classList.remove('open');
    }

    /* ============================================================
       NETWORK EVENTS
       ============================================================ */
    network.on('click', p => {
      if (p.nodes.length) inspectNode(p.nodes[0]);
      else clearSelection();
    });

    network.on('hoverNode', p => {
      nodes.update({ id: p.node, font: { size: p.node === targetName ? 12 : 10 } });
      if (!selectedId) traceToTarget(p.node);
    });

    network.on('blurNode', p => {
      const s = network.getScale();
      if (s <= 0.45 && p.node !== targetName && p.node !== selectedId) {
        nodes.update({ id: p.node, font: { size: 0 } });
      }
      if (!selectedId) clearTrace();
    });

    /* ============================================================
       SEARCH
       ============================================================ */
    const searchInput = document.getElementById('symbol-search');
    const searchResults = document.getElementById('search-results');
    let searchIdx = -1;

    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim().toLowerCase();
      clearTrace();
      if (!q) {
        searchResults.classList.remove('visible');
        searchResults.innerHTML = '';
        return;
      }
      const matches = nodesData.filter(n => n.label.toLowerCase().includes(q)).slice(0, 20);
      if (!matches.length) {
        searchResults.classList.remove('visible');
        searchResults.innerHTML = '';
        // dim all
        nodes.update(nodes.get().map(n => ({ id: n.id, opacity: 0.1, font: { size: n.depth === 0 ? 12 : 0 } })));
        return;
      }

      const mIds = new Set(matches.map(m => m.id));
      nodes.update(nodes.get().map(n => ({
        id: n.id,
        opacity: mIds.has(n.id) ? 1 : 0.08,
        font: { size: (mIds.has(n.id) || n.depth === 0) ? (n.depth === 0 ? 12 : 10) : 0 }
      })));

      const dotColor = n => n.group === 0 ? 'var(--red)' : n.group === 1 ? 'var(--cyan)' : n.group === 2 ? 'var(--amber)' : 'var(--indigo)';
      searchResults.innerHTML = matches.map((m, i) => `
        <div class="search-result-item" data-id="${escapeHtml(m.id)}" data-idx="${i}">
          <span class="sr-dot" style="background:${dotColor(m)}"></span>
          <span class="sr-name">${escapeHtml(m.label)}</span>
          <span class="sr-path">${escapeHtml(basename(m.path))}</span>
        </div>
      `).join('');
      searchResults.classList.add('visible');
      searchIdx = -1;

      searchResults.querySelectorAll('.search-result-item').forEach(el => {
        el.addEventListener('click', () => {
          const nid = el.dataset.id;
          network.selectNodes([nid]);
          inspectNode(nid);
          network.focus(nid, { scale: 1.25, animation: true });
          searchResults.classList.remove('visible');
          searchInput.blur();
        });
      });

      if (matches.length === 1) {
        network.selectNodes([matches[0].id]);
        inspectNode(matches[0].id);
        network.focus(matches[0].id, { scale: 1.25, animation: true });
      }
    });

    searchInput.addEventListener('keydown', e => {
      const items = searchResults.querySelectorAll('.search-result-item');
      if (!items.length) return;
      if (e.key === 'ArrowDown') { e.preventDefault(); searchIdx = Math.min(searchIdx + 1, items.length - 1); highlightSearchItem(items); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); searchIdx = Math.max(searchIdx - 1, 0); highlightSearchItem(items); }
      else if (e.key === 'Enter' && searchIdx >= 0) { e.preventDefault(); items[searchIdx].click(); }
    });

    function highlightSearchItem(items) {
      items.forEach((el, i) => el.classList.toggle('active', i === searchIdx));
      if (searchIdx >= 0) items[searchIdx].scrollIntoView({ block: 'nearest' });
    }

    searchInput.addEventListener('blur', () => {
      setTimeout(() => searchResults.classList.remove('visible'), 150);
    });

    /* ============================================================
       CONTEXT MENU
       ============================================================ */
    const ctxMenu = document.getElementById('ctx-menu');

    container.addEventListener('contextmenu', e => {
      e.preventDefault();
      const nodeAt = network.getNodeAt({ x: e.offsetX, y: e.offsetY });
      if (!nodeAt) { ctxMenu.classList.remove('visible'); return; }
      ctxNodeId = nodeAt;
      ctxMenu.style.left = e.clientX + 'px';
      ctxMenu.style.top = e.clientY + 'px';
      ctxMenu.classList.add('visible');
    });

    document.addEventListener('click', () => ctxMenu.classList.remove('visible'));

    document.getElementById('ctx-focus').onclick = () => {
      if (ctxNodeId) network.focus(ctxNodeId, { scale: 1.35, animation: { duration: 400 } });
    };
    document.getElementById('ctx-trace').onclick = () => {
      if (ctxNodeId) { inspectNode(ctxNodeId); network.selectNodes([ctxNodeId]); }
    };
    document.getElementById('ctx-copy').onclick = async () => {
      if (ctxNodeId) { await navigator.clipboard.writeText(ctxNodeId); showToast('Symbol copied'); }
    };
    document.getElementById('ctx-editor').onclick = () => {
      if (!ctxNodeId) return;
      const n = nodesData.find(x => x.id === ctxNodeId);
      if (n?.path) window.open(`vscode://file/${encodeURI(n.path)}:${n.line || 1}`);
    };

    /* ============================================================
       MINIMAP
       ============================================================ */
    const mmCanvas = document.getElementById('minimap-canvas');
    const mmCtx = mmCanvas.getContext('2d');

    function drawMinimap() {
      const wrap = document.getElementById('minimap-wrap');
      const w = wrap.clientWidth;
      const h = wrap.clientHeight;
      mmCanvas.width = w * 2; mmCanvas.height = h * 2;
      mmCtx.scale(2, 2);
      mmCtx.clearRect(0, 0, w, h);

      const allPos = network.getPositions();
      const ids = Object.keys(allPos);
      if (!ids.length) return;

      let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
      ids.forEach(id => {
        const p = allPos[id];
        if (p.x < minX) minX = p.x; if (p.x > maxX) maxX = p.x;
        if (p.y < minY) minY = p.y; if (p.y > maxY) maxY = p.y;
      });

      const pad = 20;
      const rangeX = (maxX - minX) || 1;
      const rangeY = (maxY - minY) || 1;
      const scaleX = (w - pad * 2) / rangeX;
      const scaleY = (h - pad * 2) / rangeY;
      const sc = Math.min(scaleX, scaleY);

      const cx = w / 2 - (minX + rangeX / 2) * sc;
      const cy = h / 2 - (minY + rangeY / 2) * sc;

      // Draw nodes
      ids.forEach(id => {
        const p = allPos[id];
        const nd = nodesData.find(n => n.id === id);
        if (!nd) return;
        const x = p.x * sc + cx;
        const y = p.y * sc + cy;
        mmCtx.fillStyle = nd.group === 0 ? 'var(--red)' : nd.group === 1 ? '#06b6d4' : nd.group === 2 ? '#f59e0b' : '#6366f1';
        mmCtx.globalAlpha = nd.group === 0 ? 1 : 0.5;
        mmCtx.beginPath();
        mmCtx.arc(x, y, nd.group === 0 ? 3 : 1.5, 0, Math.PI * 2);
        mmCtx.fill();
      });
      mmCtx.globalAlpha = 1;

      // Draw viewport rect
      const viewPos = network.getViewPosition();
      const viewScale = network.getScale();
      const cw = container.clientWidth;
      const ch = container.clientHeight;
      const vx = (viewPos.x - cw / 2 / viewScale) * sc + cx;
      const vy = (viewPos.y - ch / 2 / viewScale) * sc + cy;
      const vw = (cw / viewScale) * sc;
      const vh = (ch / viewScale) * sc;
      mmCtx.strokeStyle = isDark() ? 'rgba(255,255,255,0.3)' : 'rgba(0,0,0,0.3)';
      mmCtx.lineWidth = 1;
      mmCtx.strokeRect(vx, vy, vw, vh);
    }

    network.on('afterDrawing', drawMinimap);

    /* ============================================================
       CONTROLS
       ============================================================ */
    // Navigation toggle
    document.getElementById('nav-toggle').onclick = () => document.getElementById('left-panel').classList.toggle('collapsed');
    document.getElementById('insp-close').onclick = () => clearSelection();

    // Layout
    document.getElementById('layout-select').onchange = e => {
      const v = e.target.value;
      if (v === 'solar') applySolarLayout();
      else if (v === 'force') applyForceLayout();
      else if (v === 'tree') applyTreeLayout();
    };

    // Group by file
    document.getElementById('btn-group').onclick = e => {
      groupByFile = !groupByFile;
      e.currentTarget.classList.toggle('active', groupByFile);
      visibleGraph();
      currentLayout === 'solar' ? applySolarLayout(false) : currentLayout === 'force' ? applyForceLayout() : applyTreeLayout();
      showToast(groupByFile ? 'Grouped by file' : 'Grouped by depth');
    };

    // Depth slider
    document.getElementById('depth-slider').oninput = e => {
      currentDepth = Number(e.target.value);
      document.getElementById('depth-label').textContent = currentDepth;
      currentLayout === 'solar' ? applySolarLayout(false) : currentLayout === 'force' ? applyForceLayout() : applyTreeLayout();
    };

    // Zoom
    document.getElementById('btn-zoom-in').onclick = () => network.moveTo({ scale: network.getScale() * 1.3, animation: { duration: 200 } });
    document.getElementById('btn-zoom-out').onclick = () => network.moveTo({ scale: network.getScale() * 0.77, animation: { duration: 200 } });
    document.getElementById('btn-fit').onclick = () => network.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
    document.getElementById('btn-reset').onclick = () => {
      searchInput.value = '';
      clearSelection();
      currentLayout === 'solar' ? applySolarLayout() : currentLayout === 'force' ? applyForceLayout() : applyTreeLayout();
    };

    // Export
    function exportPNG() {
      const c = container.querySelector('canvas');
      if (!c) return;
      const a = document.createElement('a');
      a.download = `n3mo-${targetName}-impact.png`;
      a.href = c.toDataURL('image/png');
      a.click();
      showToast('Exported as PNG');
    }
    document.getElementById('btn-export-top').onclick = exportPNG;

    // Theme
    function applyTheme(dark) {
      document.body.classList.toggle('light-mode', !dark);
      document.getElementById('theme-icon-sun').style.display = dark ? '' : 'none';
      document.getElementById('theme-icon-moon').style.display = dark ? 'none' : '';
      localStorage.setItem('n3mo-theme', dark ? 'dark' : 'light');
      // Refresh graph colors
      const allN = nodes.get();
      nodes.update(allN.map(n => {
        const orig = nodesData.find(x => x.id === n.id);
        return buildNode(orig);
      }));
      edges.update(edges.get().map((e, i) => {
        const orig = edgesData.find(x => x.id === e.id);
        return buildEdge(orig, i);
      }));
      if (selectedId) traceToTarget(selectedId);
    }

    document.getElementById('btn-theme').onclick = () => applyTheme(!isDark());

    // Init theme from storage
    const savedTheme = localStorage.getItem('n3mo-theme') || 'dark';
    if (savedTheme === 'light') applyTheme(false);

    // Shortcuts modal
    document.getElementById('btn-shortcuts').onclick = () => document.getElementById('kbd-overlay').classList.toggle('visible');
    document.getElementById('kbd-overlay').onclick = e => { if (e.target === e.currentTarget) e.currentTarget.classList.remove('visible'); };

    /* ============================================================
       KEYBOARD SHORTCUTS
       ============================================================ */
    document.addEventListener('keydown', e => {
      const active = document.activeElement;
      const isInput = active === searchInput || active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.tagName === 'SELECT';

      // Ctrl+K / Cmd+K — focus search
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') { e.preventDefault(); searchInput.focus(); searchInput.select(); return; }

      // Close modals on Escape
      if (e.key === 'Escape') {
        if (document.getElementById('kbd-overlay').classList.contains('visible')) {
          document.getElementById('kbd-overlay').classList.remove('visible'); return;
        }
        if (searchInput === active) { searchInput.value = ''; searchInput.blur(); searchResults.classList.remove('visible'); }
        clearSelection();
        clearTrace();
        return;
      }

      // Skip single-key shortcuts when in input
      if (isInput) return;

      if (e.key === '/') { e.preventDefault(); searchInput.focus(); searchInput.select(); }
      else if (e.key === 'f' || e.key === 'F') network.fit({ animation: { duration: 400 } });
      else if (e.key === '1') { document.getElementById('layout-select').value = 'solar'; applySolarLayout(); }
      else if (e.key === '2') { document.getElementById('layout-select').value = 'force'; applyForceLayout(); }
      else if (e.key === '3') { document.getElementById('layout-select').value = 'tree'; applyTreeLayout(); }
      else if (e.key === 'g' || e.key === 'G') document.getElementById('btn-group').click();
      else if (e.key === 'b' || e.key === 'B') document.getElementById('nav-toggle').click();
      else if (e.key === 't' || e.key === 'T') document.getElementById('btn-theme').click();
      else if (e.key === '?') document.getElementById('btn-shortcuts').click();
    });

    /* ============================================================
       TOAST
       ============================================================ */
    let toastTimer;
    function showToast(msg) {
      const t = document.getElementById('toast');
      t.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg> ${escapeHtml(msg)}`;
      t.classList.add('visible');
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => t.classList.remove('visible'), 2000);
    }

    /* ============================================================
       INIT
       ============================================================ */
    applySolarLayout(false);
  </script>
</body>
</html>
"""

    page = page.replace("__TARGET_JSON__", json.dumps(target_name))
    page = page.replace("__NODES_JSON__", json.dumps(nodes_list))
    page = page.replace("__EDGES_JSON__", json.dumps(edges_list))
    page = page.replace("__MAX_DEPTH__", str(max(1, max_depth)))

    filename = "impact_graph.html"
    with open(filename, "w", encoding="utf-8") as graph_file:
        graph_file.write(page)
    return filename
