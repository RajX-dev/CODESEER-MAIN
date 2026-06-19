# Copyright (C) 2026 Raj shekhar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
  <title>N3MO Orbit View — Repository Knowledge Graph</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,200..800&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
  <style>
    :root {
      /* Default Light Mode tokens */
      --bg-space: #f8fafc;
      --bg-panel: #ffffff;
      --bg-panel-solid: #ffffff;
      --bg-panel-raised: #f1f5f9;
      --border-soft: rgba(0, 0, 0, 0.06);
      --border-medium: rgba(0, 0, 0, 0.12);
      --text-main: #0f172a;
      --text-muted: #64748b;
      --blue: #2563eb;
      --amber: #b45309;
      --red: #dc2626;
      --cyan: #0891b2;
      --green: #16a34a;
      --accent: #4f46e5;
      --accent-hover: #4338ca;
      --accent-bg-active: rgba(79, 70, 229, 0.08);
      --shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
      --font-ui: "Inter", sans-serif;
      --font-mono: "JetBrains Mono", monospace;
    }

    body.dark-mode {
      /* Premium Dark Mode tokens */
      --bg-space: #07080b;
      --bg-panel: #0d0f14;
      --bg-panel-solid: #0d0f14;
      --bg-panel-raised: #151821;
      --border-soft: rgba(255, 255, 255, 0.05);
      --border-medium: rgba(255, 255, 255, 0.1);
      --text-main: #f1f5f9;
      --text-muted: #64748b;
      --blue: #3b82f6;
      --amber: #f59e0b;
      --red: #f43f5e;
      --cyan: #06b6d4;
      --green: #10b981;
      --accent: #6366f1;
      --accent-hover: #4f46e5;
      --accent-bg-active: rgba(99, 102, 241, 0.15);
      --shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }

    * { box-sizing: border-box; }
    html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; }
    body {
      color: var(--text-main);
      background: var(--bg-space);
      font-family: var(--font-ui);
      transition: background-color 0.3s ease, color 0.3s ease;
    }

    #dashboard {
      display: flex;
      width: 100vw;
      height: 100vh;
      overflow: hidden;
    }

    /* Left Sidebar Navigation */
    #nav-sidebar {
      width: 250px;
      background: var(--bg-panel-solid);
      border-right: 1px solid var(--border-soft);
      display: flex;
      flex-direction: column;
      flex-shrink: 0;
      z-index: 10;
      transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .logo-container {
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 12px;
      border-bottom: 1px solid var(--border-soft);
    }

    .logo-icon {
      font-size: 20px;
      color: var(--accent);
      text-shadow: 0 0 10px rgba(99, 102, 241, 0.4);
    }

    .logo-text {
      font-family: "Bricolage Grotesque", sans-serif;
      font-size: 20px;
      font-weight: 800;
      letter-spacing: 0.1em;
      text-transform: uppercase;
      color: var(--text-main);
    }

    .nav-section {
      padding: 16px 12px;
      border-bottom: 1px solid var(--border-soft);
    }

    .nav-section-title {
      font-family: "Bricolage Grotesque", sans-serif;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: 10px;
      padding-left: 8px;
    }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      color: var(--text-muted);
      text-decoration: none;
      font-size: 13px;
      font-weight: 500;
      border-radius: 6px;
      transition: all 0.2s ease;
      margin-bottom: 2px;
    }

    .nav-item:hover {
      color: var(--text-main);
      background: var(--bg-panel-raised);
    }

    .nav-item.active {
      color: var(--text-main);
      background: var(--accent-bg-active);
      border-left: 3px solid var(--accent);
      border-top-left-radius: 2px;
      border-bottom-left-radius: 2px;
    }

    .control-group {
      padding: 0 6px;
    }

    .control-group label {
      display: block;
      font-size: 11px;
      color: var(--text-muted);
      margin-bottom: 6px;
    }

    .control-group select {
      width: 100%;
      height: 34px;
      padding: 0 10px;
      background: var(--bg-panel-raised);
      border: 1px solid var(--border-soft);
      border-radius: 6px;
      color: var(--text-main);
      outline: none;
      font-size: 12px;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .control-group select:hover {
      border-color: var(--accent);
    }

    .slider-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }

    .slider-header label {
      margin-bottom: 0;
    }

    .depth-value {
      font-family: var(--font-mono);
      font-size: 12px;
      font-weight: 600;
      color: var(--accent);
    }

    #depth-slider {
      width: 100%;
      accent-color: var(--accent);
      cursor: pointer;
    }

    .action-btn {
      width: 100%;
      height: 34px;
      background: var(--bg-panel-raised);
      border: 1px solid var(--border-soft);
      border-radius: 6px;
      color: var(--text-main);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.2s ease;
    }

    .action-btn:hover, .action-btn.active {
      background: var(--accent-bg-active);
      border-color: var(--accent);
      color: var(--text-main);
    }

    .nav-footer {
      margin-top: auto;
      padding: 16px 12px;
      border-top: 1px solid var(--border-soft);
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .nav-footer-btn {
      width: 100%;
      height: 34px;
      background: transparent;
      border: 1px solid var(--border-soft);
      border-radius: 6px;
      color: var(--text-muted);
      font-size: 12px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: all 0.2s ease;
    }

    .nav-footer-btn:hover {
      color: var(--text-main);
      border-color: var(--accent);
      background: var(--bg-panel-raised);
    }

    .version {
      font-size: 9px;
      color: var(--text-muted);
      text-align: center;
      opacity: 0.6;
    }

    /* Main Content */
    #main-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-width: 0;
      height: 100%;
    }

    /* Top bar Header */
    #top-bar {
      height: 72px;
      background: var(--bg-panel-solid);
      border-bottom: 1px solid var(--border-soft);
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0 24px;
      flex-shrink: 0;
      z-index: 9;
    }

    .header-left {
      display: flex;
      align-items: center;
      gap: 16px;
      min-width: 0;
    }

    .target-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      min-width: 0;
    }

    .target-label {
      color: var(--text-muted);
      font-weight: 500;
    }

    .target-value {
      font-family: var(--font-mono);
      font-weight: 600;
      color: var(--text-main);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .badge-row {
      display: flex;
      gap: 8px;
    }

    .risk-pill {
      padding: 4px 10px;
      background: rgba(244, 63, 94, 0.1);
      border: 1px solid var(--red);
      border-radius: 20px;
      color: var(--red);
      font-family: "Bricolage Grotesque", sans-serif;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .tag-pill {
      padding: 4px 10px;
      background: var(--line-soft);
      border: 1px solid var(--border-soft);
      border-radius: 20px;
      color: var(--text-muted);
      font-size: 10px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    /* Metrics Panel Dashboard */
    .metrics-panel {
      display: flex;
      gap: 8px;
      flex-shrink: 0;
    }

    .metric-card {
      min-width: 90px;
      padding: 6px 12px;
      background: var(--bg-panel);
      border: 1px solid var(--border-soft);
      border-radius: 6px;
      display: flex;
      flex-direction: column;
      align-items: center;
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
      cursor: help;
    }

    .metric-card:hover {
      transform: translateY(-2px);
      border-color: var(--accent);
      box-shadow: 0 4px 12px rgba(99, 102, 241, 0.15);
    }

    .metric-value {
      font-family: var(--font-mono);
      font-size: 18px;
      font-weight: 700;
      color: var(--text-main);
    }

    .metric-label {
      font-family: "Bricolage Grotesque", sans-serif;
      font-size: 8px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-top: 2px;
    }

    /* Work Area split panels layout */
    #work-area {
      flex: 1;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 380px;
      min-height: 0;
    }

    /* Knowledge Graph Canvas Panel */
    #graph-panel {
      position: relative;
      min-width: 0;
      overflow: hidden;
      background: var(--bg-space);
    }

    #mynetwork {
      position: absolute;
      inset: 0;
      z-index: 2;
    }

    #orbit-layer {
      position: absolute;
      inset: 0;
      z-index: 1;
      pointer-events: none;
    }

    /* Floating Canvas Toolbar */
    .canvas-toolbar {
      position: absolute;
      top: 16px;
      right: 16px;
      background: var(--bg-panel);
      border: 1px solid var(--border-soft);
      border-radius: 8px;
      padding: 4px;
      display: flex;
      gap: 4px;
      box-shadow: var(--shadow);
      z-index: 10;
    }

    .tb-btn {
      width: 32px;
      height: 32px;
      background: transparent;
      border: none;
      border-radius: 6px;
      color: var(--text-muted);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      transition: all 0.2s ease;
    }

    .tb-btn:hover {
      background: var(--bg-panel-raised);
      color: var(--text-main);
    }

    /* Floating Canvas Legend */
    .canvas-legend {
      position: absolute;
      bottom: 16px;
      left: 16px;
      background: var(--bg-panel);
      border: 1px solid var(--border-soft);
      border-radius: 8px;
      padding: 12px;
      box-shadow: var(--shadow);
      z-index: 10;
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-width: 200px;
    }

    .legend-title {
      font-family: "Bricolage Grotesque", sans-serif;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-muted);
      border-bottom: 1px solid var(--border-soft);
      padding-bottom: 6px;
      margin-bottom: 2px;
    }

    .legend-row {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .legend-color-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    .legend-text {
      font-size: 11px;
      color: var(--text-muted);
    }

    /* Right details panel */
    #info-panels {
      background: var(--bg-panel-solid);
      border-left: 1px solid var(--border-soft);
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      gap: 16px;
      padding: 16px;
    }

    .panel-section {
      background: var(--bg-panel);
      border: 1px solid var(--border-soft);
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }

    .panel-header {
      background: var(--bg-panel-raised);
      padding: 12px 16px;
      border-bottom: 1px solid var(--border-soft);
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .panel-header .icon {
      font-size: 14px;
      color: var(--accent);
    }

    .panel-header h3 {
      font-family: "Bricolage Grotesque", sans-serif;
      font-size: 13px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin: 0;
      color: var(--text-main);
    }

    .panel-body {
      padding: 16px;
      overflow-y: auto;
    }

    /* Card Panels Styling */
    .card {
      background: var(--bg-panel-raised);
      border: 1px solid var(--border-soft);
      border-radius: 6px;
      padding: 12px;
      margin-bottom: 12px;
      transition: all 0.2s ease;
    }

    .card:hover {
      border-color: var(--accent);
    }

    .card-label {
      font-family: "Bricolage Grotesque", sans-serif;
      font-size: 8px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: 6px;
    }

    .symbol-name {
      font-family: var(--font-mono);
      font-size: 13px;
      font-weight: 600;
      word-break: break-all;
      color: var(--text-main);
    }

    .badge {
      display: inline-flex;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .badge.target { color: var(--red); background: rgba(244, 63, 94, 0.1); border: 1px solid var(--red); }
    .badge.inner { color: var(--cyan); background: rgba(6, 182, 212, 0.1); border: 1px solid var(--cyan); }
    .badge.mid { color: var(--amber); background: rgba(245, 158, 11, 0.1); border: 1px solid var(--amber); }
    .badge.outer { color: var(--blue); background: rgba(59, 130, 246, 0.1); border: 1px solid var(--blue); }

    .location {
      font-family: var(--font-mono);
      font-size: 11px;
      color: var(--text-muted);
      word-break: break-all;
      line-height: 1.5;
    }

    .action-row {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-top: 16px;
    }

    .action {
      height: 34px;
      border: 1px solid var(--border-soft);
      border-radius: 6px;
      background: var(--bg-panel-raised);
      color: var(--text-main);
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      text-decoration: none;
      transition: all 0.2s ease;
    }

    a.action {
      display: flex;
    }

    .action.primary {
      background: var(--accent);
      border-color: var(--accent);
      color: #ffffff;
    }

    .action.primary:hover {
      background: var(--accent-hover);
      border-color: var(--accent-hover);
    }

    .action:not(.primary):hover {
      border-color: var(--accent);
      background: var(--accent-bg-active);
    }

    /* Empty State */
    .empty-state {
      padding: 40px 16px;
      text-align: center;
      color: var(--text-muted);
    }

    .empty-icon {
      font-size: 28px;
      color: var(--border-soft);
      margin-bottom: 12px;
    }

    .empty-state p {
      font-size: 12px;
      line-height: 1.6;
      margin: 0;
    }

    /* System Architecture List Rows */
    .arch-card {
      background: var(--bg-panel-raised);
      border: 1px solid var(--border-soft);
      border-radius: 6px;
      padding: 12px;
    }

    .arch-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 12px;
      padding: 6px 0;
      border-bottom: 1px solid var(--border-soft);
    }

    .arch-row:last-child {
      border-bottom: none;
    }

    .arch-label {
      color: var(--text-muted);
    }

    .arch-val {
      font-weight: 600;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .text-purple { color: #8b5cf6; }
    .text-cyan { color: var(--cyan); }
    .text-green { color: var(--green); }

    .arch-header-sub {
      font-family: "Bricolage Grotesque", sans-serif;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: 8px;
    }

    .diagnostic-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .diag-item {
      background: var(--bg-panel);
      border: 1px solid var(--border-soft);
      border-radius: 4px;
      padding: 8px;
      text-align: center;
    }

    .diag-label {
      font-size: 9px;
      color: var(--text-muted);
      margin-bottom: 4px;
    }

    .diag-val {
      font-family: var(--font-mono);
      font-size: 11px;
      font-weight: 700;
      color: var(--text-main);
    }

    /* Toast Notification */
    #toast {
      z-index: 30;
      position: absolute;
      left: 50%;
      bottom: 24px;
      padding: 8px 16px;
      border: 1px solid var(--border-soft);
      border-radius: 6px;
      opacity: 0;
      color: var(--text-main);
      background: var(--bg-panel);
      box-shadow: var(--shadow);
      font-size: 12px;
      font-weight: 500;
      pointer-events: none;
      transform: translate(-50%, 10px);
      transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }

    #toast.visible {
      opacity: 1;
      transform: translate(-50%, 0);
    }

    /* Code Preview Panels */
    .code-preview {
      background: var(--bg-space);
      border: 1px solid var(--border-soft);
      border-radius: 6px;
      overflow: hidden;
      margin-top: 8px;
    }
    .code-header {
      background: var(--bg-panel-raised);
      padding: 8px 12px;
      border-bottom: 1px solid var(--border-soft);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .code-file {
      font-family: var(--font-mono);
      font-size: 10px;
      color: var(--text-muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 70%;
    }
    .code-line-badge {
      font-family: var(--font-mono);
      font-size: 9px;
      color: var(--text-main);
      background: var(--border-soft);
      padding: 2px 6px;
      border-radius: 4px;
    }
    .code-content {
      padding: 12px;
      overflow-x: auto;
      background: var(--bg-space);
    }
    .code-line {
      display: flex;
      gap: 12px;
      padding: 2px 0;
    }
    .code-line.highlight {
      background: rgba(99, 102, 241, 0.08);
      margin: 0 -12px;
      padding: 2px 12px;
      border-left: 2px solid var(--accent);
    }
    .line-num {
      color: var(--text-muted);
      text-align: right;
      min-width: 32px;
      user-select: none;
      opacity: 0.5;
      font-family: var(--font-mono);
      font-size: 11px;
    }
    .line-code {
      color: var(--text-main);
      white-space: pre;
      font-family: var(--font-mono);
      font-size: 11px;
    }

    @media (max-width: 1100px) {
      #work-area { grid-template-columns: minmax(0, 1fr) 300px; }
      .metrics-panel .metric-card:nth-child(3) { display: none; }
    }
    @media (max-width: 768px) {
      #dashboard { flex-direction: column; }
      #nav-sidebar { width: 100%; height: auto; border-right: none; border-bottom: 1px solid var(--border-soft); }
      #work-area { grid-template-columns: 1fr; }
      #info-panels { border-left: none; border-top: 1px solid var(--border-soft); }
    }
  </style>
</head>
<body class="dark-mode">
  <div id="dashboard">
    <!-- Left Navigation Sidebar -->
    <aside id="nav-sidebar">
      <div class="logo-container">
        <div class="logo-icon"><i class="fa-solid fa-circle-nodes"></i></div>
        <div class="logo-text">N3MO</div>
      </div>
      
      <div class="nav-section">
        <div class="nav-section-title">Navigation</div>
        <a href="#" class="nav-item active"><i class="fa-solid fa-network-wired"></i> Impact Graph</a>
        <a href="https://github.com/RajX-dev/N3MO" target="_blank" class="nav-item"><i class="fa-brands fa-github"></i> Repository</a>
        <a href="https://github.com/RajX-dev/N3MO/blob/main/README.md" target="_blank" class="nav-item"><i class="fa-solid fa-book"></i> Documentation</a>
      </div>

      <div class="nav-section">
        <div class="nav-section-title">Layout Engine</div>
        <div class="control-group">
          <label for="layout-select">Graph Representation</label>
          <select id="layout-select">
            <option value="solar">Radial Orbital</option>
            <option value="force">Force Directed</option>
            <option value="tree">Impact Tree</option>
          </select>
        </div>
        <div class="control-group" style="margin-top: 12px;">
          <button class="action-btn" id="btn-group" type="button">
            <i class="fa-solid fa-folder-tree"></i> Group by File
          </button>
        </div>
      </div>

      <div class="nav-section">
        <div class="nav-section-title">Configuration</div>
        <div class="control-group">
          <div class="slider-header">
            <label for="depth-slider">Visible Depth</label>
            <span class="depth-value" id="depth-label">__MAX_DEPTH__</span>
          </div>
          <input id="depth-slider" type="range" min="1" max="__MAX_DEPTH__" value="__MAX_DEPTH__">
        </div>
      </div>
      
      <div class="nav-footer">
        <button class="nav-footer-btn" id="btn-theme"><i class="fa-solid fa-sun"></i> Light Mode</button>
        <div class="version">v1.2.4</div>
      </div>
    </aside>

    <!-- Main Content Panel -->
    <main id="main-content">
      <header id="top-bar">
        <div class="header-left">
          <div class="target-title">
            <span class="target-label">Target Symbol:</span>
            <span class="target-value" id="target-name"></span>
          </div>
          <div class="badge-row">
            <span class="risk-pill" id="risk-pill">High Impact</span>
            <span class="tag-pill"><i class="fa-solid fa-shield-halved"></i> Verified</span>
          </div>
        </div>
        
        <div class="metrics-panel">
          <div class="metric-card" title="Direct caller dependencies (Depth 1)">
            <div class="metric-value" id="stat-direct">0</div>
            <div class="metric-label">Direct Callers</div>
          </div>
          <div class="metric-card" title="Total transitive callers impacted">
            <div class="metric-value" id="stat-total">0</div>
            <div class="metric-label">Total Impacted</div>
          </div>
          <div class="metric-card" title="Unique files containing call paths">
            <div class="metric-value" id="stat-files">0</div>
            <div class="metric-label">Affected Files</div>
          </div>
        </div>
      </header>

      <div id="work-area">
        <section id="graph-panel">
          <div id="stars"></div>
          <div id="orbit-layer"></div>
          <div id="mynetwork"></div>

          <!-- Canvas Floating Search Bar -->
          <div class="search" style="position: absolute; top: 16px; left: 16px; z-index: 10; width: 300px;">
            <input id="symbol-search" type="search" placeholder="Search symbol... (Press '/' to focus)" autocomplete="off">
          </div>

          <div class="canvas-toolbar">
            <button class="tb-btn" id="btn-fit" title="Fit Graph"><i class="fa-solid fa-expand"></i></button>
            <button class="tb-btn" id="btn-zoom-in" title="Zoom In"><i class="fa-solid fa-plus"></i></button>
            <button class="tb-btn" id="btn-zoom-out" title="Zoom Out"><i class="fa-solid fa-minus"></i></button>
            <button class="tb-btn" id="btn-export" title="Export PNG Image"><i class="fa-solid fa-image"></i></button>
            <button class="tb-btn" id="btn-reset" title="Reset View"><i class="fa-solid fa-rotate-left"></i></button>
          </div>

          <div class="canvas-legend">
            <div class="legend-title">Blast Radius Legend</div>
            <div class="legend-row">
              <span class="legend-color-dot" style="background: var(--red);"></span>
              <span class="legend-text">Target Focus Node</span>
            </div>
            <div class="legend-row">
              <span class="legend-color-dot" style="background: var(--cyan);"></span>
              <span class="legend-text">Direct Caller (Depth 1)</span>
            </div>
            <div class="legend-row">
              <span class="legend-color-dot" style="background: var(--amber);"></span>
              <span class="legend-text">Indirect Caller (Depth 2)</span>
            </div>
            <div class="legend-row">
              <span class="legend-color-dot" style="background: var(--blue);"></span>
              <span class="legend-text">Deep Caller (Depth &ge; 3)</span>
            </div>
          </div>
        </section>

        <!-- Right Side Multi-Panels -->
        <aside id="info-panels">
          <!-- Panel 1: Real-time Analysis -->
          <div class="panel-section" id="analysis-panel" style="flex: 1; display: flex; flex-direction: column;">
            <div class="panel-header" style="flex-shrink: 0;">
              <i class="fa-solid fa-magnifying-glass-chart icon"></i>
              <h3>Real-Time Analysis</h3>
            </div>
            <div class="panel-body" id="inspector-content" style="flex: 1; overflow-y: auto;">
              <div class="empty-state">
                <div class="empty-icon"><i class="fa-solid fa-circle-info"></i></div>
                <p>Select any node in the knowledge graph canvas to view call telemetry, source path, and code context.</p>
              </div>
            </div>
          </div>

          <!-- Panel 2: System Architecture Details -->
          <div class="panel-section" id="architecture-panel" style="flex-shrink: 0;">
            <div class="panel-header">
              <i class="fa-solid fa-server icon"></i>
              <h3>System Architecture</h3>
            </div>
            <div class="panel-body">
              <div class="arch-card">
                <div class="arch-row">
                  <span class="arch-label">Relational Engine</span>
                  <span class="arch-val"><i class="fa-solid fa-database text-purple"></i> PostgreSQL</span>
                </div>
                <div class="arch-row">
                  <span class="arch-label">Parser Engine</span>
                  <span class="arch-val"><i class="fa-solid fa-code-branch text-cyan"></i> Tree-sitter</span>
                </div>
                <div class="arch-row">
                  <span class="arch-label">License Mode</span>
                  <span class="arch-val"><i class="fa-solid fa-balance-scale text-green"></i> Local (AGPL-3.0)</span>
                </div>
              </div>
              
              <div class="arch-card" style="margin-top: 12px;">
                <div class="arch-header-sub">Diagnostics</div>
                <div class="diagnostic-grid">
                  <div class="diag-item">
                    <div class="diag-label">Search Speed</div>
                    <div class="diag-val">&lt; 50ms</div>
                  </div>
                  <div class="diag-item">
                    <div class="diag-label">Link Strategy</div>
                    <div class="diag-val">Scope-Aware</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </aside>
      </div>
    </main>
  </div>

  <script>
    const targetName = __TARGET_JSON__;
    const nodesData = __NODES_JSON__;
    const edgesData = __EDGES_JSON__;
    const configuredMaxDepth = __MAX_DEPTH__;
    const actualMaxDepth = Math.max(1, ...nodesData.map(node => node.group));
    const themes = {
      light: {
        text: '#0f172a',
        stroke: '#ffffff',
        edge: '#cbd5e1',
        edgeHover: '#64748b',
        orbitStroke: 'rgba(0, 0, 0, 0.05)',
        orbitDash: 'rgba(99, 102, 241, 0.15)',
        palette: ['#6366f1', '#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6'],
        nodes: {
          target: { bg: '#e0e7ff', border: '#4f46e5', highlightBg: '#4f46e5', hoverBg: '#e0e7ff' },
          inner: { bg: '#d1fae5', border: '#059669', highlightBg: '#d1fae5', hoverBg: '#d1fae5' },
          mid: { bg: '#fef3c7', border: '#d97706', highlightBg: '#fef3c7', hoverBg: '#fef3c7' },
          outer: { bg: '#f1f5f9', border: '#64748b', highlightBg: '#f1f5f9', hoverBg: '#f1f5f9' }
        }
      },
      dark: {
        text: '#f1f5f9',
        stroke: '#07080b',
        edge: '#1e293b',
        edgeHover: '#64748b',
        orbitStroke: 'rgba(255, 255, 255, 0.05)',
        orbitDash: 'rgba(99, 102, 241, 0.18)',
        palette: ['#818cf8', '#60a5fa', '#34d399', '#fbbf24', '#f472b6', '#a78bfa'],
        nodes: {
          target: { bg: '#1e1b4b', border: '#818cf8', highlightBg: '#818cf8', hoverBg: '#2e2a75' },
          inner: { bg: '#064e3b', border: '#34d399', highlightBg: '#2a2a2a', hoverBg: '#0b6c53' },
          mid: { bg: '#451a03', border: '#fbbf24', highlightBg: '#2a2a2a', hoverBg: '#622705' },
          outer: { bg: '#0d0f16', border: '#64748b', highlightBg: '#2a2a2a', hoverBg: '#141722' }
        }
      }
    };
    let currentDepth = Math.min(configuredMaxDepth, actualMaxDepth);
    let currentLayout = 'solar';
    let groupByFile = false;
    let selectedId = null;

    document.getElementById('target-name').textContent = targetName;
    document.getElementById('stat-direct').textContent = nodesData.filter(node => node.group === 1).length;
    document.getElementById('stat-total').textContent = nodesData.filter(node => node.group > 0).length;
    document.getElementById('stat-files').textContent = new Set(nodesData.filter(node => node.path).map(node => node.path)).size;
    document.getElementById('risk-pill').textContent =
      nodesData.filter(node => node.group > 0).length > 10 ? 'High impact' : 'Moderate impact';

    const fileColor = (path, currentTheme) => {
      let hash = 0;
      for (const char of path || 'target') hash = ((hash << 5) - hash) + char.charCodeAt(0);
      const palette = themes[currentTheme].palette;
      return palette[Math.abs(hash) % palette.length];
    };

    const baseNode = node => {
      const isTarget = node.group === 0;
      const isInner = node.group === 1;
      const isMid = node.group === 2;
      const isOuter = node.group >= 3;

      const currentTheme = document.body.classList.contains('dark-mode') ? 'dark' : 'light';
      const t = themes[currentTheme];
      const nodeTheme = isTarget ? t.nodes.target : isInner ? t.nodes.inner : isMid ? t.nodes.mid : t.nodes.outer;

      const border = groupByFile && !isTarget
        ? fileColor(node.path, currentTheme)
        : nodeTheme.border;

      const background = nodeTheme.bg;

      // Create a copy and remove "group" to prevent Vis.js group styling override
      const cleanNode = { ...node };
      delete cleanNode.group;

      return {
        ...cleanNode,
        depth: node.group,
        level: node.group,
        shape: 'dot',
        size: isTarget ? 28 : isInner ? 14 : isMid ? 11 : Math.max(8, 12 - node.group),
        borderWidth: isTarget ? 3 : 2,
        borderWidthSelected: 3,
        font: {
          face: 'JetBrains Mono',
          color: t.text,
          size: isTarget ? 13 : 10,
          strokeWidth: 4,
          strokeColor: t.stroke
        },
        color: {
          background,
          border,
          highlight: { background: nodeTheme.highlightBg, border: t.text },
          hover: { background: nodeTheme.hoverBg, border: t.text }
        }
      };
    };

    const baseEdge = (edge, index) => {
      const currentTheme = document.body.classList.contains('dark-mode') ? 'dark' : 'light';
      const t = themes[currentTheme];
      return {
        ...edge,
        id: edge.id || `edge-${index}`,
        arrows: { to: { enabled: true, scaleFactor: .45 } },
        color: { color: t.edge, highlight: t.nodes.target.border, hover: t.edgeHover, opacity: .8 },
        width: 1,
        selectionWidth: 1.5,
        hoverWidth: 1.2,
        smooth: currentLayout === 'tree'
          ? { enabled: true, type: 'cubicBezier', forceDirection: 'horizontal', roundness: 0.5 }
          : { enabled: true, type: 'curvedCW', roundness: .08 }
      };
    };

    const nodes = new vis.DataSet(nodesData.map(baseNode));
    const edges = new vis.DataSet(edgesData.map(baseEdge));
    const container = document.getElementById('mynetwork');
    const network = new vis.Network(container, { nodes, edges }, {
      autoResize: true,
      physics: false,
      interaction: { hover: true, multiselect: false, navigationButtons: false, keyboard: true },
      layout: { improvedLayout: false }
    });

    function solarPositions() {
      const positions = {};
      const visible = nodesData.filter(node => node.group <= currentDepth);
      positions[targetName] = { x: 0, y: 0 };
      
      for (let depth = 1; depth <= currentDepth; depth += 1) {
        const ringNodes = visible.filter(node => node.group === depth);
        ringNodes.sort((a, b) => a.label.localeCompare(b.label));
        
        const maxPerRing = 10;
        const numSubRings = Math.ceil(ringNodes.length / maxPerRing);
        const baseRadius = 160 + ((depth - 1) * 160);
        
        ringNodes.forEach((node, index) => {
          const subRingIdx = index % numSubRings;
          const ringSpacing = 45;
          const offsetRadius = (subRingIdx - (numSubRings - 1) / 2) * ringSpacing;
          const radius = baseRadius + offsetRadius;
          
          const nodesInThisSubRing = Math.ceil(ringNodes.length / numSubRings);
          const nodeIdxInSubRing = Math.floor(index / numSubRings);
          
          const angleOffset = (depth % 2 === 0 ? Math.PI / 5 : -Math.PI / 2) + (subRingIdx * (Math.PI / 10));
          const angle = angleOffset + ((Math.PI * 2 * nodeIdxInSubRing) / Math.max(nodesInThisSubRing, 1));
          
          positions[node.id] = {
            x: Math.cos(angle) * radius,
            y: Math.sin(angle) * radius
          };
        });
      }
      return positions;
    }

    function drawOrbits() {
      const layer = document.getElementById('orbit-layer');
      layer.innerHTML = '';
      network.redraw();
    }

    function visibleGraph() {
      const visibleNodes = nodesData.filter(node => node.group <= currentDepth).map(baseNode);
      const ids = new Set(visibleNodes.map(node => node.id));
      const visibleEdges = edgesData
        .filter(edge => ids.has(edge.from) && ids.has(edge.to))
        .map((edge, idx) => baseEdge(edge, idx));
      nodes.clear();
      edges.clear();
      nodes.add(visibleNodes);
      edges.add(visibleEdges);

      const scale = network.getScale();
      updateLabelVisibility(scale > 0.45, true);
    }

    function disableHierarchical() {
      network.setOptions({
        layout: {
          hierarchical: {
            enabled: false
          }
        }
      });
    }

    function applySolarLayout(animate = true) {
      currentLayout = 'solar';
      disableHierarchical();
      network.setOptions({ physics: false });
      visibleGraph();
      const positions = solarPositions();
      nodes.update(nodes.get().map(node => ({
        id: node.id,
        x: positions[node.id]?.x || 0,
        y: positions[node.id]?.y || 0,
        fixed: { x: true, y: true }
      })));
      drawOrbits();
      setTimeout(() => network.fit({ animation: animate ? { duration: 600, easingFunction: 'easeInOutQuad' } : false }), 30);
    }

    function applyForceLayout() {
      currentLayout = 'force';
      disableHierarchical();
      visibleGraph();
      nodes.update(nodes.get().map(node => ({ id: node.id, fixed: false })));
      drawOrbits();
      network.setOptions({
        physics: {
          enabled: true,
          solver: 'forceAtlas2Based',
          forceAtlas2Based: {
            gravitationalConstant: -55,
            centralGravity: .012,
            springLength: 125,
            springConstant: .055,
            damping: .5
          },
          stabilization: { enabled: true, iterations: 150, fit: true }
        }
      });
    }

    function applyTreeLayout() {
      currentLayout = 'tree';
      disableHierarchical();
      visibleGraph();
      nodes.update(nodes.get().map(node => ({ id: node.id, fixed: false })));
      drawOrbits();
      network.setOptions({
        physics: { enabled: false },
        layout: {
          hierarchical: {
            enabled: true,
            direction: 'LR',
            sortMethod: 'directed',
            levelSeparation: 180,
            nodeSpacing: 80,
            parentCentralization: true,
            blockShifting: true,
            edgeMinimization: true
          }
        }
      });
      setTimeout(() => network.fit({ animation: { duration: 500 } }), 50);
    }

    network.on('stabilizationIterationsDone', () => {
      if (currentLayout === 'force') {
        network.setOptions({ physics: false });
        showToast('Physics stabilized and frozen');
      }
    });

    let lastShowLabels = true;
    function updateLabelVisibility(showLabels, force = false) {
      if (showLabels === lastShowLabels && !force) return;
      lastShowLabels = showLabels;
      
      nodes.update(nodes.get().map(node => {
        const isTarget = node.depth === 0;
        const isSelected = node.id === selectedId;
        return {
          id: node.id,
          font: {
            size: (showLabels || isTarget || isSelected) ? (isTarget ? 15 : 11) : 0
          }
        };
      }));
    }

    network.on('zoom', () => {
      const scale = network.getScale();
      updateLabelVisibility(scale > 0.45);
    });

    function traceToTarget(startId) {
      const tracedNodes = new Set();
      const tracedEdges = new Set();
      const pathNodes = [];

      function findPaths(currentId) {
        pathNodes.push(currentId);
        if (currentId === targetName) {
          pathNodes.forEach(n => tracedNodes.add(n));
          for (let i = 0; i < pathNodes.length - 1; i++) {
            const fromNode = pathNodes[i];
            const toNode = pathNodes[i + 1];
            const edge = edgesData.find(e => e.from === fromNode && e.to === toNode);
            if (edge) {
              const edgeId = edge.id || `edge-${edgesData.indexOf(edge)}`;
              tracedEdges.add(edgeId);
            }
          }
          pathNodes.pop();
          return;
        }

        const outgoing = edgesData.filter(e => e.from === currentId);
        for (const edge of outgoing) {
          const nextId = edge.to;
          if (!pathNodes.includes(nextId)) {
            findPaths(nextId);
          }
        }
        pathNodes.pop();
      }

      findPaths(startId);

      if (tracedNodes.size === 0) {
        tracedNodes.add(startId);
        tracedNodes.add(targetName);
      }

      nodes.update(nodes.get().map(node => {
        const isTarget = node.depth === 0;
        const isSelected = node.id === selectedId;
        const scale = network.getScale();
        const showLabels = scale > 0.45;
        const showLabel = showLabels || isTarget || isSelected || node.id === startId;
        return {
          id: node.id,
          opacity: tracedNodes.has(node.id) ? 1 : 0.15,
          font: { size: showLabel ? (isTarget ? 13 : 10) : 0 }
        };
      }));

      edges.update(edges.get().map((edge, idx) => {
        const edgeId = edge.id || `edge-${idx}`;
        const isTraced = tracedEdges.has(edgeId);
        const currentTheme = document.body.classList.contains('dark-mode') ? 'dark' : 'light';
        const t = themes[currentTheme];
        return {
          id: edgeId,
          color: isTraced
            ? { color: t.nodes.target.border, opacity: 1 }
            : { color: t.edge, opacity: 0.1 },
          width: isTraced ? 2 : 1
        };
      }));
    }

    function clearTrace() {
      const scale = network.getScale();
      const showLabels = scale > 0.45;
      nodes.update(nodes.get().map(node => {
        const isTarget = node.depth === 0;
        const isSelected = node.id === selectedId;
        return {
          id: node.id,
          opacity: 1,
          font: {
            size: (showLabels || isTarget || isSelected) ? (isTarget ? 13 : 10) : 0
          }
        };
      }));
      const currentTheme = document.body.classList.contains('dark-mode') ? 'dark' : 'light';
      const t = themes[currentTheme];
      edges.update(edges.get().map((edge, idx) => ({
        id: edge.id || `edge-${idx}`,
        color: { color: t.edge, highlight: t.nodes.target.border, hover: t.edgeHover, opacity: .8 },
        width: 1
      })));
    }

    function osBasename(path) {
      if (!path) return '';
      const parts = path.split('/');
      return parts[parts.length - 1];
    }

    function renderCodePreview(node) {
      if (!node.code_context || node.code_context.length === 0) {
        return '';
      }
      const linesHtml = node.code_context.map(([lineNum, lineContent]) => {
        const isCallSite = lineNum === node.line;
        return `
          <div class="code-line ${isCallSite ? 'highlight' : ''}">
            <span class="line-num">${lineNum}</span>
            <span class="line-code">${escapeHtml(lineContent)}</span>
          </div>
        `;
      }).join('');

      return `
        <div class="card">
          <div class="card-label">Call Site Code Preview</div>
          <div class="code-preview">
            <div class="code-header">
              <span class="code-file" title="${escapeHtml(node.path)}">${escapeHtml(osBasename(node.path))}</span>
              <span class="code-line-badge">Line ${node.line}</span>
            </div>
            <div class="code-content">
              ${linesHtml}
            </div>
          </div>
        </div>
      `;
    }

    const defaultEmptyState = `
      <div class="empty-state">
        <div class="empty-icon"><i class="fa-solid fa-circle-info"></i></div>
        <p>Select any node in the knowledge graph canvas to view call telemetry, source path, and code context.</p>
      </div>`;

    function inspectNode(nodeId) {
      const node = nodesData.find(item => item.id === nodeId);
      if (!node) return;
      selectedId = nodeId;
      traceToTarget(nodeId);
      const classification = node.group === 0 ? 'target' : node.group === 1 ? 'inner' : node.group === 2 ? 'mid' : 'outer';
      const classText = node.group === 0 ? 'Target node' : node.group === 1 ? 'Direct caller / Depth 1' : node.group === 2 ? 'Indirect caller / Depth 2' : `Deep caller / Depth ${node.group}`;
      const location = node.path ? `${node.path}:${node.line || 1}` : 'Target definition';
      const editorLink = node.path ? `vscode://file/${encodeURI(node.path)}:${node.line || 1}` : '#';
      const codeHtml = renderCodePreview(node);
      
      document.getElementById('inspector-content').innerHTML = `
        <div class="card">
          <div class="card-label">Selected symbol</div>
          <div class="symbol-name">${escapeHtml(node.label)}</div>
        </div>
        <div class="card">
          <div class="card-label">Dependency depth</div>
          <span class="badge ${classification}">${classText}</span>
        </div>
        <div class="card">
          <div class="card-label">Source location</div>
          <div class="location">${escapeHtml(location)}</div>
        </div>
        ${codeHtml}
        <div class="action-row">
          <a class="action primary" href="${editorLink}">Open in editor</a>
          <button class="action" id="focus-selected" type="button"><i class="fa-solid fa-crosshairs"></i> Focus path</button>
          <button class="action" id="copy-location" type="button"><i class="fa-solid fa-copy"></i> Copy path</button>
          <button class="action" id="clear-path" type="button"><i class="fa-solid fa-xmark"></i> Clear path</button>
        </div>`;

      document.getElementById('focus-selected').onclick = () =>
        network.focus(nodeId, { scale: 1.35, animation: { duration: 500 } });
      document.getElementById('copy-location').onclick = async () => {
        await navigator.clipboard.writeText(location);
        showToast('Location copied');
      };
      document.getElementById('clear-path').onclick = () => {
        selectedId = null;
        network.unselectAll();
        clearTrace();
        document.getElementById('inspector-content').innerHTML = defaultEmptyState;
      };
    }

    function escapeHtml(value) {
      return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
    }

    let toastTimer;
    function showToast(message) {
      const toast = document.getElementById('toast');
      toast.textContent = message;
      toast.classList.add('visible');
      clearTimeout(toastTimer);
      toastTimer = setTimeout(() => toast.classList.remove('visible'), 1500);
    }

    network.on('click', params => {
      if (params.nodes.length) {
        inspectNode(params.nodes[0]);
      } else {
        selectedId = null;
        clearTrace();
        document.getElementById('inspector-content').innerHTML = defaultEmptyState;
      }
    });

    network.on('hoverNode', params => {
      nodes.update({
        id: params.node,
        font: { size: params.node === targetName ? 15 : 11 }
      });
      if (!selectedId) {
        traceToTarget(params.node);
      }
    });

    network.on('blurNode', params => {
      const scale = network.getScale();
      const showLabels = scale > 0.45;
      if (!showLabels && params.node !== targetName && params.node !== selectedId) {
        nodes.update({
          id: params.node,
          font: { size: 0 }
        });
      }
      if (!selectedId) {
        clearTrace();
      }
    });

    network.on('beforeDrawing', context => {
      if (currentLayout !== 'solar') return;
      context.save();
      context.setLineDash([5, 8]);
      context.lineWidth = 1 / network.getScale();
      context.strokeStyle = document.body.classList.contains('dark-mode') 
        ? 'rgba(255, 255, 255, 0.05)' 
        : 'rgba(0, 0, 0, 0.05)';
      
      const visible = nodesData.filter(node => node.group <= currentDepth);
      
      for (let depth = 1; depth <= currentDepth; depth += 1) {
        const ringNodes = visible.filter(node => node.group === depth);
        if (ringNodes.length === 0) continue;
        
        const maxPerRing = 10;
        const numSubRings = Math.ceil(ringNodes.length / maxPerRing);
        const baseRadius = 160 + ((depth - 1) * 160);
        
        for (let subRingIdx = 0; subRingIdx < numSubRings; subRingIdx++) {
          const ringSpacing = 45;
          const offsetRadius = (subRingIdx - (numSubRings - 1) / 2) * ringSpacing;
          const radius = baseRadius + offsetRadius;
          
          context.beginPath();
          context.arc(0, 0, radius, 0, Math.PI * 2);
          context.stroke();
        }
      }
      context.restore();
    });

    const search = document.getElementById('symbol-search');
    search.addEventListener('input', () => {
      const query = search.value.trim().toLowerCase();
      clearTrace();
      if (!query) return;
      const matches = nodes.get().filter(node => node.label.toLowerCase().includes(query));
      nodes.update(nodes.get().map(node => {
        const isTarget = node.depth === 0;
        const isMatched = matches.some(match => match.id === node.id);
        return {
          id: node.id,
          opacity: isMatched ? 1 : .12,
          font: { size: (isMatched || isTarget) ? (isTarget ? 15 : 11) : 0 }
        };
      }));
      if (matches.length === 1) {
        network.selectNodes([matches[0].id]);
        inspectNode(matches[0].id);
        network.focus(matches[0].id, { scale: 1.25, animation: true });
      }
    });

    document.addEventListener('keydown', event => {
      if (event.key === '/' && document.activeElement !== search) {
        event.preventDefault();
        search.focus();
      }
      if (event.key === 'Escape') {
        search.value = '';
        selectedId = null;
        network.unselectAll();
        clearTrace();
        document.getElementById('inspector-content').innerHTML = defaultEmptyState;
      }
    });

    document.getElementById('layout-select').onchange = event => {
      const val = event.target.value;
      if (val === 'solar') applySolarLayout();
      else if (val === 'force') applyForceLayout();
      else if (val === 'tree') applyTreeLayout();
    };
    document.getElementById('btn-group').onclick = event => {
      groupByFile = !groupByFile;
      event.currentTarget.classList.toggle('active', groupByFile);
      visibleGraph();
      currentLayout === 'solar' ? applySolarLayout(false) : currentLayout === 'force' ? applyForceLayout() : applyTreeLayout();
      showToast(groupByFile ? 'File colors enabled' : 'Depth colors restored');
    };
    document.getElementById('btn-fit').onclick = () => network.fit({ animation: true });
    document.getElementById('btn-zoom-in').onclick = () => network.moveTo({ scale: network.getScale() * 1.2 });
    document.getElementById('btn-zoom-out').onclick = () => network.moveTo({ scale: network.getScale() * .82 });
    document.getElementById('btn-reset').onclick = () => {
      search.value = '';
      selectedId = null;
      clearTrace();
      currentLayout === 'solar' ? applySolarLayout() : currentLayout === 'force' ? applyForceLayout() : applyTreeLayout();
      document.getElementById('inspector-content').innerHTML = defaultEmptyState;
    };
    document.getElementById('btn-export').onclick = () => {
      const canvas = container.querySelector('canvas');
      if (!canvas) return;
      const link = document.createElement('a');
      link.download = `n3mo-${targetName}-impact.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    };
    document.getElementById('depth-slider').oninput = event => {
      currentDepth = Number(event.target.value);
      document.getElementById('depth-label').textContent = currentDepth;
      currentLayout === 'solar' ? applySolarLayout(false) : currentLayout === 'force' ? applyForceLayout() : applyTreeLayout();
    };

    function updateThemeColors() {
      const allNodes = nodes.get();
      nodes.update(allNodes.map(node => {
        const origNode = nodesData.find(item => item.id === node.id);
        return baseNode(origNode);
      }));
      
      const allEdges = edges.get();
      edges.update(allEdges.map((edge, idx) => {
        const origEdge = edgesData.find(e => e.id === edge.id);
        return baseEdge(origEdge, idx);
      }));
      
      drawOrbits();
      if (selectedId) {
        traceToTarget(selectedId);
      }
    }

    const savedTheme = localStorage.getItem('n3mo-theme') || 'dark';
    if (savedTheme === 'dark') {
      document.body.classList.add('dark-mode');
      document.getElementById('btn-theme').innerHTML = '<i class="fa-solid fa-sun"></i> Light Mode';
    } else {
      document.body.classList.remove('dark-mode');
      document.getElementById('btn-theme').innerHTML = '<i class="fa-solid fa-moon"></i> Dark Mode';
    }

    document.getElementById('btn-theme').onclick = () => {
      const isDark = document.body.classList.toggle('dark-mode');
      localStorage.setItem('n3mo-theme', isDark ? 'dark' : 'light');
      document.getElementById('btn-theme').innerHTML = isDark 
        ? '<i class="fa-solid fa-sun"></i> Light Mode' 
        : '<i class="fa-solid fa-moon"></i> Dark Mode';
      updateThemeColors();
    };

    drawOrbits();
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
