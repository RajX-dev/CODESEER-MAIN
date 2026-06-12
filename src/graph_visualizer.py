import json


def generate_solar_graph_html(nodes, edges, target_name, max_depth=3):
    nodes_list = [
        {
            "id": name,
            "label": name,
            "group": data["group"],
            "path": data.get("path", ""),
            "line": data.get("line", 0),
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
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {
      --space: #05070b;
      --panel: rgba(12, 17, 24, 0.92);
      --panel-solid: #0c1118;
      --panel-raised: #111924;
      --line: #263244;
      --line-soft: rgba(92, 116, 145, 0.18);
      --text: #edf5ff;
      --muted: #8090a5;
      --blue: #4c8dff;
      --amber: #f5a524;
      --red: #ff5a5f;
      --cyan: #55d6e8;
    }

    * { box-sizing: border-box; }
    html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; }
    body {
      color: var(--text);
      background:
        radial-gradient(circle at 35% 42%, rgba(34, 64, 112, 0.16), transparent 34%),
        radial-gradient(circle at 70% 15%, rgba(76, 141, 255, 0.08), transparent 24%),
        var(--space);
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
      background: rgba(5, 7, 11, 0.86);
      backdrop-filter: blur(18px);
    }

    .brand-row { display: flex; align-items: center; gap: 14px; min-width: 0; }
    .brand {
      display: flex;
      align-items: center;
      gap: 9px;
      color: var(--blue);
      font-family: "JetBrains Mono", monospace;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.16em;
      white-space: nowrap;
    }
    .brand-mark {
      position: relative;
      width: 24px;
      height: 24px;
      border: 1px solid rgba(76, 141, 255, 0.7);
      border-radius: 50%;
      box-shadow: inset 0 0 12px rgba(76, 141, 255, 0.3);
    }
    .brand-mark::after {
      content: "";
      position: absolute;
      inset: 7px;
      border-radius: 50%;
      background: var(--blue);
      box-shadow: 0 0 12px var(--blue);
    }
    .target-summary { min-width: 0; }
    .target-name {
      overflow: hidden;
      font-family: "JetBrains Mono", monospace;
      font-size: 16px;
      font-weight: 600;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .target-meta { margin-top: 3px; color: var(--muted); font-size: 11px; }
    .risk-pill {
      padding: 5px 8px;
      border: 1px solid rgba(255, 90, 95, 0.4);
      border-radius: 999px;
      color: #ff9699;
      background: rgba(255, 90, 95, 0.1);
      font-size: 10px;
      font-weight: 700;
      letter-spacing: 0.08em;
      white-space: nowrap;
    }

    .summary-stats { display: flex; align-items: center; gap: 8px; }
    .summary-stat {
      min-width: 82px;
      padding: 8px 11px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: rgba(17, 25, 36, 0.72);
    }
    .summary-stat span {
      display: block;
      color: var(--muted);
      font-size: 9px;
      font-weight: 700;
      letter-spacing: 0.1em;
      text-transform: uppercase;
    }
    .summary-stat strong {
      display: block;
      margin-top: 2px;
      font-family: "JetBrains Mono", monospace;
      font-size: 18px;
    }

    .workspace {
      position: relative;
      display: grid;
      grid-template-columns: minmax(0, 1fr) 360px;
      min-height: 0;
    }

    #graph-shell { position: relative; min-width: 0; overflow: hidden; }
    #mynetwork { position: absolute; inset: 0; z-index: 2; }
    #stars, #orbit-layer { position: absolute; inset: 0; pointer-events: none; }
    #stars {
      z-index: 0;
      opacity: 0.48;
      background-image:
        radial-gradient(circle, rgba(255,255,255,.7) 0 1px, transparent 1.2px),
        radial-gradient(circle, rgba(90,150,255,.6) 0 1px, transparent 1.3px);
      background-position: 0 0, 37px 51px;
      background-size: 83px 83px, 127px 127px;
    }
    #orbit-layer { z-index: 1; }
    .orbit {
      position: absolute;
      left: 50%;
      top: 50%;
      border: 1px solid rgba(96, 127, 165, 0.22);
      border-radius: 50%;
      transform: translate(-50%, -50%);
      box-shadow: inset 0 0 40px rgba(76, 141, 255, 0.018);
    }
    .orbit-label {
      position: absolute;
      left: 50%;
      top: 0;
      padding: 3px 7px;
      border: 1px solid rgba(96, 127, 165, 0.2);
      border-radius: 999px;
      color: #65778f;
      background: rgba(5, 7, 11, 0.84);
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
      border-radius: 10px;
      outline: none;
      color: var(--text);
      background: var(--panel);
      box-shadow: 0 12px 28px rgba(0,0,0,.22);
      font-family: "JetBrains Mono", monospace;
      font-size: 12px;
    }
    .search input:focus { border-color: var(--blue); box-shadow: 0 0 0 3px rgba(76,141,255,.12); }
    .search kbd {
      position: absolute;
      top: 10px;
      right: 10px;
      padding: 2px 5px;
      border: 1px solid var(--line);
      border-radius: 4px;
      color: var(--muted);
      background: #0a0e14;
      font-size: 9px;
    }
    .toolbar-group {
      display: flex;
      align-items: center;
      gap: 5px;
      padding: 4px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: var(--panel);
      box-shadow: 0 12px 28px rgba(0,0,0,.22);
    }
    .toolbar-spacer { flex: 1; }
    .tool-button, .tool-select {
      height: 32px;
      border: 1px solid transparent;
      border-radius: 7px;
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
      border-radius: 11px;
      background: var(--panel);
      box-shadow: 0 14px 36px rgba(0,0,0,.32);
    }
    .depth-control label { color: var(--muted); font-size: 11px; }
    .depth-control input { flex: 1; accent-color: var(--blue); }
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
      border-radius: 10px;
      color: var(--muted);
      background: var(--panel);
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
      box-shadow: -18px 0 45px rgba(0,0,0,.2);
    }
    .sidebar-header { padding: 18px; border-bottom: 1px solid var(--line); }
    .eyebrow {
      color: var(--blue);
      font-size: 9px;
      font-weight: 700;
      letter-spacing: .14em;
      text-transform: uppercase;
    }
    .sidebar-title { margin-top: 7px; font-size: 15px; font-weight: 600; }
    .inspector { padding: 16px; }
    .empty-state { padding: 80px 20px; color: var(--muted); text-align: center; }
    .empty-orbit {
      width: 60px;
      height: 60px;
      margin: 0 auto 18px;
      border: 1px solid var(--line);
      border-radius: 50%;
      box-shadow: inset 0 0 20px rgba(76,141,255,.09);
    }
    .empty-state p { margin: 0; font-size: 12px; line-height: 1.6; }
    .card {
      margin-bottom: 12px;
      padding: 14px;
      border: 1px solid var(--line);
      border-radius: 10px;
      background: #0a0f16;
    }
    .card-label {
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 9px;
      font-weight: 700;
      letter-spacing: .1em;
      text-transform: uppercase;
    }
    .symbol-name { font-family: "JetBrains Mono", monospace; font-size: 14px; font-weight: 600; word-break: break-all; }
    .badge {
      display: inline-flex;
      padding: 5px 8px;
      border: 1px solid currentColor;
      border-radius: 999px;
      font-size: 9px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }
    .badge.target { color: #ff8589; background: rgba(255,90,95,.08); }
    .badge.direct { color: #ffc35c; background: rgba(245,165,36,.08); }
    .badge.ripple { color: #77a6ff; background: rgba(76,141,255,.08); }
    .location {
      color: #b7c4d4;
      font-family: "JetBrains Mono", monospace;
      font-size: 11px;
      line-height: 1.6;
      word-break: break-all;
    }
    .action-row { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
    .action {
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--text);
      background: var(--panel-raised);
      cursor: pointer;
      font-size: 11px;
      font-weight: 600;
      text-decoration: none;
    }
    a.action { display: flex; align-items: center; justify-content: center; }
    .action.primary { border-color: #346ccf; background: #2459b8; }
    .action:hover { filter: brightness(1.13); }

    #toast {
      z-index: 30;
      position: absolute;
      left: 50%;
      bottom: 24px;
      padding: 9px 12px;
      border: 1px solid var(--line);
      border-radius: 8px;
      opacity: 0;
      color: var(--text);
      background: var(--panel-solid);
      box-shadow: 0 14px 35px rgba(0,0,0,.35);
      font-size: 11px;
      pointer-events: none;
      transform: translate(-50%, 10px);
      transition: .2s ease;
    }
    #toast.visible { opacity: 1; transform: translate(-50%, 0); }

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
            </select>
            <button class="tool-button" id="btn-group" type="button">Group by file</button>
          </div>
          <div class="toolbar-spacer"></div>
          <div class="toolbar-group">
            <button class="tool-button square" id="btn-fit" type="button" title="Fit graph">◎</button>
            <button class="tool-button square" id="btn-zoom-in" type="button" title="Zoom in">+</button>
            <button class="tool-button square" id="btn-zoom-out" type="button" title="Zoom out">-</button>
            <button class="tool-button" id="btn-export" type="button">Export PNG</button>
            <button class="tool-button" id="btn-reset" type="button">Reset</button>
          </div>
        </div>

        <div class="legend">
          <div class="legend-item"><span class="legend-dot" style="background:var(--red)"></span>Target sun</div>
          <div class="legend-item"><span class="legend-dot" style="background:var(--amber)"></span>Direct orbit</div>
          <div class="legend-item"><span class="legend-dot" style="background:var(--blue)"></span>Ripple orbit</div>
        </div>

        <div class="depth-control">
          <label for="depth-slider">Visible depth</label>
          <input id="depth-slider" type="range" min="1" max="__MAX_DEPTH__" value="__MAX_DEPTH__">
          <span class="depth-value" id="depth-label">__MAX_DEPTH__</span>
        </div>
        <div id="toast"></div>
      </section>

      <aside id="sidebar">
        <div class="sidebar-header">
          <div class="eyebrow">Node inspector</div>
          <div class="sidebar-title">Trace a dependency</div>
        </div>
        <div class="inspector" id="inspector-content">
          <div class="empty-state">
            <div class="empty-orbit"></div>
            <p>Select a planet to inspect its depth, source location, and path to the target.</p>
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
    const palette = ['#55d6e8', '#a78bfa', '#39d98a', '#ff7a90', '#f3cf5b', '#5aa9ff'];
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

    const fileColor = path => {
      let hash = 0;
      for (const char of path || 'target') hash = ((hash << 5) - hash) + char.charCodeAt(0);
      return palette[Math.abs(hash) % palette.length];
    };

    const baseNode = node => {
      const isTarget = node.group === 0;
      const isDirect = node.group === 1;
      const border = groupByFile && !isTarget
        ? fileColor(node.path)
        : isTarget ? '#ff7478' : isDirect ? '#f5a524' : '#4c8dff';
      return {
        ...node,
        shape: 'dot',
        size: isTarget ? 36 : isDirect ? 17 : Math.max(10, 15 - node.group),
        borderWidth: isTarget ? 3 : 2,
        borderWidthSelected: 4,
        font: {
          face: 'JetBrains Mono',
          color: '#dce8f6',
          size: isTarget ? 15 : 11,
          strokeWidth: 5,
          strokeColor: '#05070b'
        },
        color: {
          background: isTarget ? '#ff4f55' : isDirect ? '#151510' : '#0a111d',
          border,
          highlight: { background: isTarget ? '#ff4f55' : '#142848', border: '#ffffff' },
          hover: { background: isTarget ? '#ff6267' : '#12233d', border: '#ffffff' }
        },
        shadow: {
          enabled: true,
          color: isTarget ? 'rgba(255,79,85,.72)' : `${border}66`,
          size: isTarget ? 32 : 15,
          x: 0,
          y: 0
        }
      };
    };

    const baseEdge = edge => ({
      ...edge,
      arrows: { to: { enabled: true, scaleFactor: .45 } },
      color: { color: '#2a3748', highlight: '#83aefc', hover: '#526c8d', opacity: .78 },
      width: 1,
      selectionWidth: 2,
      hoverWidth: 1.5,
      smooth: { enabled: true, type: 'curvedCW', roundness: .08 }
    });

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
        const radius = 145 + ((depth - 1) * 125);
        ringNodes.sort((a, b) => a.label.localeCompare(b.label));
        ringNodes.forEach((node, index) => {
          const offset = depth % 2 === 0 ? Math.PI / 5 : -Math.PI / 2;
          const angle = offset + ((Math.PI * 2 * index) / Math.max(ringNodes.length, 1));
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
        .map(edge => baseEdge(edge));
      nodes.clear();
      edges.clear();
      nodes.add(visibleNodes);
      edges.add(visibleEdges);
    }

    function applySolarLayout(animate = true) {
      currentLayout = 'solar';
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
          stabilization: { iterations: 180, fit: true }
        }
      });
    }

    function traceToTarget(startId) {
      const tracedNodes = new Set([startId, targetName]);
      const tracedEdges = new Set();
      let cursor = startId;
      let guard = 0;
      while (cursor !== targetName && guard < nodesData.length) {
        const edge = edgesData.find(item => item.from === cursor);
        if (!edge) break;
        tracedEdges.add(edge.id);
        tracedNodes.add(edge.to);
        cursor = edge.to;
        guard += 1;
      }
      nodes.update(nodes.get().map(node => ({
        id: node.id,
        opacity: tracedNodes.has(node.id) ? 1 : .16
      })));
      edges.update(edges.get().map(edge => ({
        id: edge.id,
        color: tracedEdges.has(edge.id)
          ? { color: '#7da9ff', opacity: 1 }
          : { color: '#243041', opacity: .12 },
        width: tracedEdges.has(edge.id) ? 2.4 : 1
      })));
    }

    function clearTrace() {
      nodes.update(nodes.get().map(node => ({ id: node.id, opacity: 1 })));
      edges.update(edges.get().map((edge, index) => ({
        id: edge.id,
        color: { color: '#2a3748', highlight: '#83aefc', hover: '#526c8d', opacity: .78 },
        width: 1
      })));
    }

    function inspectNode(nodeId) {
      const node = nodesData.find(item => item.id === nodeId);
      if (!node) return;
      selectedId = nodeId;
      traceToTarget(nodeId);
      const classification = node.group === 0 ? 'target' : node.group === 1 ? 'direct' : 'ripple';
      const classText = node.group === 0 ? 'Target sun' : node.group === 1 ? 'Direct caller / Depth 1' : `Ripple effect / Depth ${node.group}`;
      const location = node.path ? `${node.path}:${node.line || 1}` : 'Target definition';
      const editorLink = node.path ? `vscode://file/${encodeURI(node.path)}:${node.line || 1}` : '#';
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
      if (params.nodes.length) inspectNode(params.nodes[0]);
      else {
        selectedId = null;
        clearTrace();
      }
    });
    network.on('hoverNode', params => {
      if (!selectedId) traceToTarget(params.node);
    });
    network.on('blurNode', () => {
      if (!selectedId) clearTrace();
    });
    network.on('beforeDrawing', context => {
      if (currentLayout !== 'solar') return;
      context.save();
      context.setLineDash([5, 8]);
      context.lineWidth = 1 / network.getScale();
      context.strokeStyle = 'rgba(96, 127, 165, 0.32)';
      for (let depth = 1; depth <= currentDepth; depth += 1) {
        const radius = 145 + ((depth - 1) * 125);
        context.beginPath();
        context.arc(0, 0, radius, 0, Math.PI * 2);
        context.stroke();
      }
      context.restore();
    });

    const search = document.getElementById('symbol-search');
    search.addEventListener('input', () => {
      const query = search.value.trim().toLowerCase();
      clearTrace();
      if (!query) return;
      const matches = nodes.get().filter(node => node.label.toLowerCase().includes(query));
      nodes.update(nodes.get().map(node => ({
        id: node.id,
        opacity: matches.some(match => match.id === node.id) ? 1 : .12
      })));
      if (matches.length === 1) {
        network.selectNodes([matches[0].id]);
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
      }
    });

    document.getElementById('layout-select').onchange = event =>
      event.target.value === 'solar' ? applySolarLayout() : applyForceLayout();
    document.getElementById('btn-group').onclick = event => {
      groupByFile = !groupByFile;
      event.currentTarget.classList.toggle('active', groupByFile);
      visibleGraph();
      currentLayout === 'solar' ? applySolarLayout(false) : applyForceLayout();
      showToast(groupByFile ? 'File colors enabled' : 'Depth colors restored');
    };
    document.getElementById('btn-fit').onclick = () => network.fit({ animation: true });
    document.getElementById('btn-zoom-in').onclick = () => network.moveTo({ scale: network.getScale() * 1.2 });
    document.getElementById('btn-zoom-out').onclick = () => network.moveTo({ scale: network.getScale() * .82 });
    document.getElementById('btn-reset').onclick = () => {
      search.value = '';
      selectedId = null;
      clearTrace();
      currentLayout === 'solar' ? applySolarLayout() : applyForceLayout();
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
      currentLayout === 'solar' ? applySolarLayout(false) : applyForceLayout();
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
