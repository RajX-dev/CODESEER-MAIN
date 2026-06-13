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
  <title>N3MO Orbit View</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --space: #f7f4ef;
      --panel: #f9f6f0;
      --panel-solid: #f9f6f0;
      --panel-raised: #f1ebd9;
      --line: #e5dfd5;
      --line-soft: rgba(27, 24, 22, 0.05);
      --text: #191816;
      --muted: #6e6a64;
      --blue: #35608a;
      --amber: #a36a18;
      --red: #c85a49;
      --cyan: #2b664c;
    }

    body.dark-mode {
      --space: #191919;
      --panel: #222222;
      --panel-solid: #222222;
      --panel-raised: #2a2a2a;
      --line: #333333;
      --line-soft: rgba(255, 255, 255, 0.05);
      --text: #f7f4ef;
      --muted: #a39f99;
      --blue: #5294e2;
      --amber: #cca043;
      --red: #e07a6b;
      --cyan: #59b387;
    }

    body.dark-mode .card,
    body.dark-mode .summary-stat,
    body.dark-mode .search input,
    body.dark-mode .toolbar-group,
    body.dark-mode .depth-control,
    body.dark-mode .legend,
    body.dark-mode #toast,
    body.dark-mode .action {
      background: #222222;
    }

    body.dark-mode .code-preview {
      background: #1e1e1e;
    }
    body.dark-mode .code-header {
      background: #2a2a2a;
    }
    body.dark-mode .code-content {
      background: #1e1e1e;
    }

    * { box-sizing: border-box; }
    html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; }
    body {
      color: var(--text);
      background: var(--space);
      font-family: Inter, sans-serif;
    }

    button, input, select { font: inherit; }
    button { color: inherit; }

    #app {
      display: grid;
      grid-template-rows: 72px minmax(0, 1fr);
      width: 100vw;
      height: 100vh;
    }

    .topbar {
      z-index: 20;
      display: grid;
      grid-template-columns: minmax(260px, 1fr) auto;
      align-items: center;
      gap: 20px;
      padding: 12px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel-solid);
    }

    .brand-row { display: flex; align-items: center; gap: 14px; min-width: 0; }
    .brand {
      display: flex;
      align-items: center;
      gap: 9px;
      color: var(--text);
      font-family: "Lora", serif;
      font-size: 16px;
      font-weight: 700;
      letter-spacing: 0.05em;
      white-space: nowrap;
    }
    .brand-mark {
      position: relative;
      width: 18px;
      height: 18px;
      border: 1px solid var(--red);
      border-radius: 50%;
    }
    .brand-mark::after {
      content: "";
      position: absolute;
      inset: 4px;
      border-radius: 50%;
      background: var(--red);
    }
    .target-summary { min-width: 0; }
    .target-name {
      overflow: hidden;
      font-family: "JetBrains Mono", monospace;
      font-size: 15px;
      font-weight: 600;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .target-meta { margin-top: 3px; color: var(--muted); font-size: 11px; }
    .risk-pill {
      padding: 4px 8px;
      border: 1px solid var(--red);
      border-radius: 4px;
      color: var(--red);
      background: rgba(204, 90, 63, 0.05);
      font-family: "Lora", serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.02em;
      text-transform: uppercase;
      white-space: nowrap;
    }

    .summary-stats { display: flex; align-items: center; gap: 8px; }
    .summary-stat {
      min-width: 82px;
      padding: 6px 10px;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: #ffffff;
    }
    .summary-stat span {
      display: block;
      color: var(--muted);
      font-family: "Lora", serif;
      font-size: 8px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .summary-stat strong {
      display: block;
      margin-top: 2px;
      font-family: "JetBrains Mono", monospace;
      font-size: 16px;
    }

    .workspace {
      position: relative;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      min-height: 0;
    }

    #graph-shell { position: relative; min-width: 0; overflow: hidden; background: var(--space); }
    #mynetwork { position: absolute; inset: 0; z-index: 2; }
    #stars, #orbit-layer { position: absolute; inset: 0; pointer-events: none; }
    #stars { display: none; }
    #orbit-layer { z-index: 1; }
    .orbit {
      position: absolute;
      left: 50%;
      top: 50%;
      border: 1px solid rgba(27, 24, 22, 0.08);
      border-radius: 50%;
      transform: translate(-50%, -50%);
    }
    .orbit-label {
      position: absolute;
      left: 50%;
      top: 0;
      padding: 3px 7px;
      border: 1px solid var(--line);
      border-radius: 4px;
      color: var(--muted);
      background: var(--panel-solid);
      font-family: "JetBrains Mono", monospace;
      font-size: 9px;
      letter-spacing: 0.08em;
      transform: translate(-50%, -50%);
      text-transform: uppercase;
    }

    .toolbar {
      z-index: 10;
      position: absolute;
      top: 16px;
      left: 16px;
      right: 16px;
      display: flex;
      align-items: center;
      gap: 8px;
      pointer-events: none;
    }
    .toolbar > * { pointer-events: auto; }
    .search {
      position: relative;
      width: min(330px, 38vw);
    }
    .search input {
      width: 100%;
      height: 40px;
      padding: 0 36px 0 13px;
      border: 1px solid var(--line);
      border-radius: 4px;
      outline: none;
      color: var(--text);
      background: #ffffff;
      box-shadow: 0 4px 12px rgba(0,0,0,.03);
      font-family: "JetBrains Mono", monospace;
      font-size: 12px;
    }
    .search input:focus { border-color: var(--red); box-shadow: 0 0 0 3px rgba(204,90,63,.12); }
    .search kbd {
      position: absolute;
      top: 10px;
      right: 10px;
      padding: 2px 5px;
      border: 1px solid var(--line);
      border-radius: 4px;
      color: var(--muted);
      background: var(--space);
      font-size: 9px;
    }
    .toolbar-group {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 4px;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: #ffffff;
      box-shadow: 0 4px 12px rgba(0,0,0,.03);
    }
    .toolbar-spacer { flex: 1; }
    .tool-button, .tool-select {
      height: 32px;
      border: 1px solid transparent;
      border-radius: 3px;
      color: var(--muted);
      background: transparent;
      cursor: pointer;
      font-size: 11px;
    }
    .tool-button { padding: 0 10px; }
    .tool-button.square { width: 32px; padding: 0; font-size: 16px; }
    .tool-button:hover, .tool-button.active, .tool-select:hover {
      border-color: var(--line);
      color: var(--text);
      background: var(--panel-raised);
    }
    .tool-select { padding: 0 28px 0 9px; outline: none; }

    .depth-control {
      z-index: 10;
      position: absolute;
      right: 18px;
      bottom: 18px;
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 230px;
      padding: 10px 12px;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: #ffffff;
      box-shadow: 0 4px 16px rgba(0,0,0,.05);
    }
    .depth-control label { color: var(--muted); font-size: 11px; }
    .depth-control input { flex: 1; accent-color: var(--red); }
    .depth-value {
      min-width: 22px;
      color: var(--text);
      font-family: "JetBrains Mono", monospace;
      font-size: 12px;
      text-align: right;
    }

    .legend {
      z-index: 10;
      position: absolute;
      left: 18px;
      bottom: 18px;
      display: flex;
      gap: 14px;
      padding: 9px 12px;
      border: 1px solid var(--line);
      border-radius: 4px;
      color: var(--muted);
      background: #ffffff;
      box-shadow: 0 4px 16px rgba(0,0,0,.05);
      font-size: 10px;
    }
    .legend-item { display: flex; align-items: center; gap: 6px; }
    .legend-dot { width: 7px; height: 7px; border-radius: 50%; }

    #sidebar {
      z-index: 12;
      min-width: 0;
      overflow-y: auto;
      border-left: 1px solid var(--line);
      background: var(--panel-solid);
      box-shadow: none;
    }
    .sidebar-header { padding: 18px; border-bottom: 1px solid var(--line); }
    .eyebrow {
      color: var(--red);
      font-family: "Lora", serif;
      font-size: 10px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .sidebar-title { margin-top: 7px; font-family: "Lora", serif; font-size: 18px; font-weight: 600; }
    .inspector { padding: 16px; }
    .empty-state { padding: 80px 20px; color: var(--muted); text-align: center; }
    .empty-orbit {
      width: 50px;
      height: 50px;
      margin: 0 auto 18px;
      border: 1px solid var(--line);
      border-radius: 50%;
    }
    .empty-state p { margin: 0; font-size: 12px; line-height: 1.6; }
    .card {
      margin-bottom: 12px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 4px;
      background: #ffffff;
    }
    .card-label {
      margin-bottom: 8px;
      color: var(--muted);
      font-family: "Lora", serif;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .symbol-name { font-family: "JetBrains Mono", monospace; font-size: 13px; font-weight: 600; word-break: break-all; }
    .badge {
      display: inline-flex;
      padding: 4px 8px;
      border: 1px solid currentColor;
      border-radius: 4px;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: .04em;
      text-transform: uppercase;
    }
    .badge.target { color: var(--red); background: rgba(200, 90, 73, 0.08); }
    .badge.inner { color: var(--cyan); background: rgba(43, 102, 76, 0.08); }
    .badge.mid { color: var(--amber); background: rgba(163, 106, 24, 0.08); }
    .badge.outer { color: var(--blue); background: rgba(53, 96, 138, 0.08); }
    body.dark-mode .badge.target { background: rgba(224, 122, 107, 0.15); }
    body.dark-mode .badge.inner { background: rgba(89, 179, 135, 0.15); }
    body.dark-mode .badge.mid { background: rgba(204, 160, 67, 0.15); }
    body.dark-mode .badge.outer { background: rgba(82, 148, 226, 0.15); }
    .location {
      color: var(--muted);
      font-family: "JetBrains Mono", monospace;
      font-size: 11px;
      line-height: 1.6;
      word-break: break-all;
    }
    .action-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .action {
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 4px;
      color: var(--text);
      background: #ffffff;
      cursor: pointer;
      font-size: 11px;
      font-weight: 600;
      text-decoration: none;
    }
    a.action { display: flex; align-items: center; justify-content: center; }
    .action.primary { border-color: var(--red); background: var(--red); color: #ffffff; }
    .action:hover { filter: brightness(0.96); }

    #toast {
      z-index: 30;
      position: absolute;
      left: 50%;
      bottom: 24px;
      padding: 9px 12px;
      border: 1px solid var(--line);
      border-radius: 4px;
      opacity: 0;
      color: var(--text);
      background: #ffffff;
      box-shadow: 0 4px 16px rgba(0,0,0,.08);
      font-size: 11px;
      pointer-events: none;
      transform: translate(-50%, 10px);
      transition: .2s ease;
    }
    #toast.visible { opacity: 1; transform: translate(-50%, 0); }

    /* Code Preview UI */
    .code-preview {
      background: #faf8f5;
      border: 1px solid var(--line);
      border-radius: 4px;
      overflow: hidden;
      margin-top: 8px;
    }
    .code-header {
      background: #f3ede2;
      padding: 8px 12px;
      border-bottom: 1px solid var(--line);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .code-file {
      font-family: "JetBrains Mono", monospace;
      font-size: 10px;
      color: var(--muted);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      max-width: 70%;
    }
    .code-line-badge {
      font-family: "JetBrains Mono", monospace;
      font-size: 9px;
      color: var(--text);
      background: var(--line);
      padding: 2px 6px;
      border-radius: 4px;
    }
    .code-content {
      padding: 12px;
      overflow-x: auto;
      background: #faf8f5;
    }
    .code-line {
      display: flex;
      gap: 12px;
      padding: 2px 0;
    }
    .code-line.highlight {
      background: rgba(204, 90, 63, 0.06);
      margin: 0 -12px;
      padding: 2px 12px;
      border-left: 2px solid var(--red);
    }
    .line-num {
      color: var(--muted);
      text-align: right;
      min-width: 32px;
      user-select: none;
      opacity: 0.5;
      font-family: "JetBrains Mono", monospace;
      font-size: 11px;
    }
    .line-code {
      color: var(--text);
      white-space: pre;
      font-family: "JetBrains Mono", monospace;
      font-size: 11px;
    }

    @media (max-width: 980px) {
      .workspace { grid-template-columns: minmax(0, 1fr) 300px; }
      .summary-stat:nth-child(3) { display: none; }
      .toolbar .tool-button span { display: none; }
    }
  </style>
</head>
<body>
  <div id="app">
    <header class="topbar">
      <div class="brand-row">
        <div class="brand"><span class="brand-mark"></span>N3MO</div>
        <div class="target-summary">
          <div class="target-name" id="target-name"></div>
          <div class="target-meta">Impact orbit / dependency depth</div>
        </div>
        <div class="risk-pill" id="risk-pill">High impact</div>
      </div>
      <div class="summary-stats">
        <div class="summary-stat"><span>Direct</span><strong id="stat-direct">0</strong></div>
        <div class="summary-stat"><span>Total</span><strong id="stat-total">0</strong></div>
        <div class="summary-stat"><span>Files</span><strong id="stat-files">0</strong></div>
      </div>
    </header>

    <main class="workspace">
      <section id="graph-shell">
        <div id="stars"></div>
        <div id="orbit-layer"></div>
        <div id="mynetwork"></div>

        <div class="toolbar">
          <div class="search">
            <input id="symbol-search" type="search" placeholder="Find a symbol..." autocomplete="off">
            <kbd>/</kbd>
          </div>
          <div class="toolbar-group">
            <select class="tool-select" id="layout-select" aria-label="Graph layout">
              <option value="solar">Solar system</option>
              <option value="force">Force graph</option>
              <option value="tree">Impact tree</option>
            </select>
            <button class="tool-button" id="btn-group" type="button">Group by file</button>
          </div>
          <div class="toolbar-spacer"></div>
          <div class="toolbar-group">
            <button class="tool-button square" id="btn-fit" type="button" title="Fit graph">◎</button>
            <button class="tool-button square" id="btn-zoom-in" type="button" title="Zoom in">+</button>
            <button class="tool-button square" id="btn-zoom-out" type="button" title="Zoom out">-</button>
            <button class="tool-button" id="btn-export" type="button">Export PNG</button>
            <button class="tool-button" id="btn-theme" type="button">◑ Theme</button>
            <button class="tool-button" id="btn-reset" type="button">Reset</button>
          </div>
        </div>

        <div class="legend">
          <div class="legend-item"><span class="legend-dot" style="background:var(--red)"></span>Target sun</div>
          <div class="legend-item"><span class="legend-dot" style="background:var(--red)"></span>Inner layer</div>
          <div class="legend-item"><span class="legend-dot" style="background:var(--amber)"></span>Mid layer</div>
          <div class="legend-item"><span class="legend-dot" style="background:var(--blue)"></span>Outer layer</div>
        </div>

        <div class="depth-control">
          <label for="depth-slider">Visible depth</label>
          <input id="depth-slider" type="range" min="1" max="__MAX_DEPTH__" value="__MAX_DEPTH__">
          <span class="depth-value" id="depth-label">__MAX_DEPTH__</span>
        </div>
        <div id="toast"></div>
      </section>

      <aside id="sidebar" style="display: flex; flex-direction: column;">
        <div class="sidebar-header" style="flex-shrink: 0;">
          <div class="eyebrow">Node inspector</div>
          <div class="sidebar-title" id="sidebar-title-text">Trace a dependency</div>
        </div>
        <div id="inspector-tab-content" style="flex: 1; overflow-y: auto; padding: 16px;">
          <div class="inspector" id="inspector-content" style="padding: 0;">
            <div class="empty-state">
              <div class="empty-orbit"></div>
              <p>Select a planet to inspect its depth, source location, and path to the target.</p>
            </div>
          </div>
        </div>
      </aside>
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
        text: '#191816',
        stroke: '#fbf9f6',
        edge: '#d3c9b9',
        edgeHover: '#a19685',
        orbitStroke: 'rgba(27, 24, 22, 0.08)',
        orbitDash: 'rgba(96, 127, 165, 0.22)',
        palette: ['#317589', '#c85a49', '#2e7d5c', '#d9822b', '#4a55a4', '#8a5a8f'],
        nodes: {
          target: { bg: '#fdf6f5', border: '#c85a49', highlightBg: '#c85a49', hoverBg: '#fdf6f5' },
          inner: { bg: '#f2f7f5', border: '#2b664c', highlightBg: '#e2ece8', hoverBg: '#e2ece8' },
          mid: { bg: '#fbf6ed', border: '#a36a18', highlightBg: '#f5ead2', hoverBg: '#f5ead2' },
          outer: { bg: '#f3f7fa', border: '#35608a', highlightBg: '#e4ecf3', hoverBg: '#e4ecf3' }
        }
      },
      dark: {
        text: '#f7f4ef',
        stroke: '#191919',
        edge: '#444444',
        edgeHover: '#666666',
        orbitStroke: 'rgba(255, 255, 255, 0.08)',
        orbitDash: 'rgba(143, 174, 196, 0.25)',
        palette: ['#7bc0d3', '#e07a6b', '#69b592', '#e3aa6d', '#939cd8', '#c99ece'],
        nodes: {
          target: { bg: '#3d1d1a', border: '#e07a6b', highlightBg: '#e07a6b', hoverBg: '#542622' },
          inner: { bg: '#162c22', border: '#59b387', highlightBg: '#2a2a2a', hoverBg: '#234434' },
          mid: { bg: '#332813', border: '#cca043', highlightBg: '#2a2a2a', hoverBg: '#4a3b1d' },
          outer: { bg: '#162638', border: '#5294e2', highlightBg: '#2a2a2a', hoverBg: '#223c57' }
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
        color: { color: t.edge, highlight: currentTheme === 'dark' ? '#e0755a' : '#cc5a3f', hover: t.edgeHover, opacity: .8 },
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
            ? { color: currentTheme === 'dark' ? '#e0755a' : '#cc5a3f', opacity: 1 }
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
        color: { color: t.edge, highlight: currentTheme === 'dark' ? '#e0755a' : '#cc5a3f', hover: t.edgeHover, opacity: .8 },
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



    function inspectNode(nodeId) {
      const node = nodesData.find(item => item.id === nodeId);
      if (!node) return;
      selectedId = nodeId;
      traceToTarget(nodeId);
      const classification = node.group === 0 ? 'target' : node.group === 1 ? 'inner' : node.group === 2 ? 'mid' : 'outer';
      const classText = node.group === 0 ? 'Target sun' : node.group === 1 ? 'Inner layer / Depth 1' : node.group === 2 ? 'Mid layer / Depth 2' : `Outer layer / Depth ${node.group}`;
      const location = node.path ? `${node.path}:${node.line || 1}` : 'Target definition';
      const editorLink = node.path ? `vscode://file/${encodeURI(node.path)}:${node.line || 1}` : '#';
      const codeHtml = renderCodePreview(node);
      
      document.getElementById('inspector-content').innerHTML = `
        <div class="card">
          <div class="card-label">Selected symbol</div>
          <div class="symbol-name">${escapeHtml(node.label)}</div>
        </div>
        <div class="card">
          <div class="card-label">Orbit classification</div>
          <span class="badge ${classification}">${classText}</span>
        </div>
        <div class="card">
          <div class="card-label">Source location</div>
          <div class="location">${escapeHtml(location)}</div>
        </div>
        ${codeHtml}
        <div class="action-row">
          <a class="action primary" href="${editorLink}">Open in editor</a>
          <button class="action" id="focus-selected" type="button">Focus path</button>
          <button class="action" id="copy-location" type="button">Copy location</button>
          <button class="action" id="clear-path" type="button">Clear path</button>
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
        document.getElementById('inspector-content').innerHTML = `
          <div class="empty-state">
            <div class="empty-orbit"></div>
            <p>Select a planet to inspect its depth, source location, and path to the target.</p>
          </div>`;
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
        document.getElementById('inspector-content').innerHTML = `
          <div class="empty-state">
            <div class="empty-orbit"></div>
            <p>Select a planet to inspect its depth, source location, and path to the target.</p>
          </div>`;
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
      context.strokeStyle = 'rgba(96, 127, 165, 0.22)';
      
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
        document.getElementById('inspector-content').innerHTML = `
          <div class="empty-state">
            <div class="empty-orbit"></div>
            <p>Select a planet to inspect its depth, source location, and path to the target.</p>
          </div>`;
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
      document.getElementById('inspector-content').innerHTML = `
        <div class="empty-state">
          <div class="empty-orbit"></div>
          <p>Select a planet to inspect its depth, source location, and path to the target.</p>
        </div>`;
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

    const savedTheme = localStorage.getItem('n3mo-theme') || 'light';
    if (savedTheme === 'dark') {
      document.body.classList.add('dark-mode');
      document.getElementById('btn-theme').textContent = '☼ Light Mode';
    } else {
      document.getElementById('btn-theme').textContent = '◑ Dark Mode';
    }

    document.getElementById('btn-theme').onclick = () => {
      const isDark = document.body.classList.toggle('dark-mode');
      localStorage.setItem('n3mo-theme', isDark ? 'dark' : 'light');
      document.getElementById('btn-theme').textContent = isDark ? '☼ Light Mode' : '◑ Dark Mode';
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
