import sys
import os
import argparse
import json
from src.database import get_connection
from src.graph_visualizer import generate_solar_graph_html

# Try to import the indexer logic
try:
    from src.run_indexer import main as run_indexer_logic
except ImportError:
    run_indexer_logic = None

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def get_code_context(file_path, line_number, context=2):
    if not os.path.exists(file_path):
        return []
    start = max(1, line_number - context)
    end = line_number + context
    results = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for current_line_num, content in enumerate(f, 1):
                if current_line_num >= start and current_line_num <= end:
                    results.append((current_line_num, content.rstrip()))
                if current_line_num > end:
                    break
    except Exception:
        return []
    return results

# ANSI color codes
R  = "\033[0m"
BOLD = "\033[1m"
DIM  = "\033[2m"
RED  = "\033[38;2;255;85;85m"
AMBER= "\033[38;2;255;189;46m"
BLUE = "\033[38;2;88;166;255m"
CYAN = "\033[38;2;79;212;190m"
GRAY = "\033[38;2;110;118;129m"
WHITE= "\033[38;2;230;237;243m"
BG_DARK = "\033[48;2;13;17;23m"

def print_ascii_tree(results, target_name):
    W = 64
    print()
    print(f"{BG_DARK}{CYAN}{BOLD}  ◈ IMPACT ANALYSIS  {R}")
    print(f"{GRAY}  {'─' * W}{R}")
    print(f"  {WHITE}{BOLD}Target:{R}  {AMBER}{BOLD}{target_name}{R}")
    print(f"{GRAY}  {'─' * W}{R}")

    seen = set()
    sorted_results = sorted(results, key=lambda x: (x[3], x[1]))

    direct = [(s, p, l, d, t) for s, p, l, d, t in sorted_results if d == 1]
    ripple = [(s, p, l, d, t) for s, p, l, d, t in sorted_results if d > 1]

    if direct:
        print(f"\n  {RED}{BOLD}◉ Direct Callers{R}  {GRAY}({len(set(r[0] for r in direct))} symbols){R}\n")
        seen_direct = set()
        for source, path, line, depth, target in direct:
            if source in seen_direct: continue
            seen_direct.add(source)
            short_path = os.path.basename(path)
            print(f"  {RED}▸{R} {WHITE}{BOLD}{source:<28}{R} {GRAY}{short_path}:{line}{R}")

    if ripple:
        print(f"\n  {BLUE}{BOLD}◎ Ripple Effects{R}  {GRAY}({len(set(r[0] for r in ripple))} symbols){R}\n")
        seen_ripple = set()
        for source, path, line, depth, target in ripple:
            key = (source, path, line)
            if key in seen_ripple: continue
            seen_ripple.add(key)
            short_path = os.path.basename(path)
            indent = "    " * (depth - 1)
            print(f"  {BLUE}{indent}╰─▸{R} {CYAN}{source:<26}{R} {GRAY}{short_path}:{line}{R}")

    total = len(set((r[0], r[1], r[2]) for r in sorted_results))
    print(f"\n{GRAY}  {'─' * W}{R}")
    print(f"  {DIM}Total impacted: {WHITE}{total} references{R}  {GRAY}│  depth ≤ {max(r[3] for r in sorted_results)}{R}\n")

# ==========================================
# 📊 GRAPH VISUALIZER (HTML Generator)
# ==========================================

def generate_graph_html(nodes, edges, target_name, max_depth=3):
    nodes_list = [{"id": n, "label": n, "group": d["group"], "path": d.get("path", ""), "line": d.get("line", 0)} for n, d in nodes]
    edges_list = [{"from": u, "to": v} for u, v in edges]

    nodes_json = json.dumps(nodes_list)
    edges_json = json.dumps(edges_list)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>N3MO Impact Tracker</title>
  <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg: #0d1117;
      --sidebar: #161b22;
      --card-bg: #0d1117;
      --border: #30363d;
      --border-subtle: #21262d;
      --text-main: #e6edf3;
      --text-dim: #8b949e;
      --text-muted: #6e7681;
      --accent: #2f81f7;
      --accent-hover: #58a6ff;
      --danger: #f85149;
      --warning: #d29922;
      --success: #3fb950;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body, html {{
      width: 100%; height: 100%;
      background: var(--bg);
      color: var(--text-main);
      font-family: 'Inter', sans-serif;
      overflow: hidden;
      -webkit-font-smoothing: antialiased;
    }}

    /* Layout */
    #app {{ display: flex; width: 100vw; height: 100vh; }}

    #graph-container {{
      flex: 1;
      position: relative;
      background: var(--bg);
    }}

    #sidebar {{
      width: 360px;
      background: var(--sidebar);
      border-left: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      overflow-y: auto;
      box-shadow: -4px 0 24px rgba(0,0,0,0.3);
    }}

    /* Header */
    .header {{
      padding: 24px 20px 20px;
      border-bottom: 1px solid var(--border-subtle);
      background: linear-gradient(180deg, var(--sidebar) 0%, rgba(13,17,23,0.4) 100%);
    }}

    .logo {{
      font-family: 'JetBrains Mono';
      font-weight: 600;
      font-size: 11px;
      color: var(--accent);
      letter-spacing: 2px;
      margin-bottom: 8px;
      opacity: 0.9;
    }}

    .target-box {{
      font-size: 18px;
      font-weight: 600;
      color: #fff;
      font-family: 'JetBrains Mono';
      word-break: break-all;
      line-height: 1.4;
    }}

    /* Stats */
    .stats {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      padding: 20px;
      border-bottom: 1px solid var(--border-subtle);
    }}

    .stat {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px;
      transition: border-color 0.2s;
    }}

    .stat:hover {{
      border-color: var(--border);
    }}

    .stat-label {{
      font-size: 10px;
      text-transform: uppercase;
      color: var(--text-muted);
      letter-spacing: 0.5px;
      margin-bottom: 6px;
      font-weight: 500;
    }}

    .stat-value {{
      font-family: 'JetBrains Mono';
      font-size: 24px;
      font-weight: 600;
      line-height: 1;
    }}

    .stat.direct .stat-value {{ color: var(--warning); }}
    .stat.ripple .stat-value {{ color: var(--accent); }}

    /* Inspector */
    .inspector {{
      padding: 20px;
      flex: 1;
    }}

    .card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 16px;
      margin-bottom: 16px;
      transition: all 0.2s;
    }}

    .card:hover {{
      border-color: var(--border);
    }}

    .card-label {{
      font-size: 10px;
      text-transform: uppercase;
      color: var(--text-muted);
      margin-bottom: 10px;
      letter-spacing: 0.5px;
      font-weight: 500;
    }}

    .card-value {{
      font-family: 'JetBrains Mono';
      font-size: 13px;
      word-break: break-all;
      line-height: 1.5;
      color: var(--text-main);
    }}

    .badge {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.3px;
    }}

    .badge.target {{ background: rgba(248,81,73,0.15); color: var(--danger); border: 1px solid rgba(248,81,73,0.3); }}
    .badge.direct {{ background: rgba(210,153,34,0.15); color: var(--warning); border: 1px solid rgba(210,153,34,0.3); }}
    .badge.ripple {{ background: rgba(47,129,247,0.15); color: var(--accent); border: 1px solid rgba(47,129,247,0.3); }}

    /* Code Preview */
    .code-preview {{
      background: var(--bg);
      border: 1px solid var(--border-subtle);
      border-radius: 6px;
      overflow: hidden;
      margin-top: 10px;
    }}

    .code-header {{
      background: rgba(22,27,34,0.6);
      padding: 8px 12px;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .code-file {{
      font-family: 'JetBrains Mono';
      font-size: 11px;
      color: var(--text-dim);
    }}

    .code-line-badge {{
      font-family: 'JetBrains Mono';
      font-size: 10px;
      color: var(--text-muted);
      background: var(--bg);
      padding: 2px 6px;
      border-radius: 3px;
    }}

    .code-content {{
      padding: 12px;
      font-family: 'JetBrains Mono';
      font-size: 12px;
      line-height: 1.6;
      overflow-x: auto;
    }}

    .code-line {{
      display: flex;
      gap: 12px;
      padding: 2px 0;
    }}

    .code-line.highlight {{
      background: rgba(210,153,34,0.1);
      margin: 0 -12px;
      padding: 2px 12px;
      border-left: 2px solid var(--warning);
    }}

    .line-num {{
      color: var(--text-muted);
      text-align: right;
      min-width: 30px;
      user-select: none;
      opacity: 0.6;
    }}

    .line-code {{
      color: var(--text-dim);
      white-space: pre;
    }}

    /* Empty State */
    .empty-state {{
      text-align: center;
      padding: 40px 20px;
      color: var(--text-muted);
    }}

    .empty-state svg {{
      width: 48px;
      height: 48px;
      opacity: 0.3;
      margin-bottom: 12px;
    }}

    .empty-text {{
      font-size: 13px;
      line-height: 1.6;
    }}

    /* Button */
    .btn {{
      display: block;
      width: 100%;
      background: var(--accent);
      color: white;
      border: none;
      border-radius: 8px;
      padding: 12px;
      font-weight: 600;
      font-size: 14px;
      cursor: pointer;
      text-align: center;
      text-decoration: none;
      transition: all 0.2s;
      font-family: 'Inter', sans-serif;
    }}

    .btn:hover {{
      background: var(--accent-hover);
      transform: translateY(-1px);
      box-shadow: 0 4px 12px rgba(47,129,247,0.3);
    }}

    .btn:active {{
      transform: translateY(0);
    }}

    .btn-secondary {{
      background: var(--card-bg);
      color: var(--text-main);
      border: 1px solid var(--border);
    }}

    .btn-secondary:hover {{
      background: var(--sidebar);
      border-color: var(--border);
      box-shadow: none;
    }}

    /* Graph Controls */
    .graph-controls {{
      position: absolute;
      bottom: 20px;
      right: 20px;
      display: flex;
      gap: 8px;
      background: var(--sidebar);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 8px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    }}

    .control-btn {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 6px;
      color: var(--text-dim);
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      font-size: 16px;
      transition: all 0.2s;
      font-family: 'Inter', sans-serif;
      font-weight: 500;
    }}

    .control-btn:hover {{
      background: var(--sidebar);
      color: var(--text-main);
      border-color: var(--border);
    }}

    /* Legend */
    .legend {{
      position: absolute;
      bottom: 20px;
      left: 20px;
      background: var(--sidebar);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 12px 16px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.4);
    }}

    .legend-title {{
      font-size: 10px;
      text-transform: uppercase;
      color: var(--text-muted);
      letter-spacing: 0.5px;
      margin-bottom: 10px;
      font-weight: 600;
    }}

    .legend-item {{
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;
      font-size: 12px;
    }}

    .legend-item:last-child {{
      margin-bottom: 0;
    }}

    .legend-dot {{
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }}

    .legend-dot.target {{ background: var(--danger); }}
    .legend-dot.direct {{ background: var(--warning); }}
    .legend-dot.ripple {{ background: var(--accent); }}

    /* Network Canvas */
    #mynetwork {{ width: 100%; height: 100%; }}

    /* Scrollbar */
    ::-webkit-scrollbar {{ width: 8px; }}
    ::-webkit-scrollbar-track {{ background: var(--sidebar); }}
    ::-webkit-scrollbar-thumb {{ background: var(--border); border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--border); }}

    /* Animations */
    @keyframes fadeIn {{
      from {{ opacity: 0; transform: translateY(10px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    .card, .stat {{ animation: fadeIn 0.3s ease; }}
  </style>
</head>
<body>

  <div id="app">
    <div id="graph-container">
      <div id="mynetwork"></div>

      <!-- Graph Controls -->
      <div class="graph-controls">
        <button class="control-btn" id="btn-fit" title="Fit to view">⊡</button>
        <button class="control-btn" id="btn-zoom-in" title="Zoom in">+</button>
        <button class="control-btn" id="btn-zoom-out" title="Zoom out">−</button>
        <div style="display:flex; align-items:center; gap:6px; padding: 4px 8px;">
          <span style="font-size:11px; color:#8b949e;">Depth</span>
          <input type="range" id="depth-slider" min="1" max="5" value="{max_depth}" style="width:80px; accent-color:#2f81f7;">
          <span id="depth-label" style="font-size:11px; color:#e6edf3; min-width:8px;">{max_depth}</span>
        </div>
      </div>

      <!-- Legend -->
      <div class="legend">
        <div class="legend-title">Legend</div>
        <div class="legend-item">
          <span class="legend-dot target"></span>
          <span>Target</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot direct"></span>
          <span>Direct</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot ripple"></span>
          <span>Ripple</span>
        </div>
      </div>
    </div>

    <div id="sidebar">
      <div class="header">
        <div class="logo">N3MO IMPACT SYSTEM</div>
        <div class="target-box">{target_name}</div>
      </div>

      <div class="stats">
        <div class="stat direct">
          <div class="stat-label">Direct</div>
          <div class="stat-value" id="stat-direct">0</div>
        </div>
        <div class="stat ripple">
          <div class="stat-label">Total</div>
          <div class="stat-value" id="stat-total">0</div>
        </div>
      </div>

      <div class="inspector" id="inspector-content">
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>
          <div class="empty-text">Click a node to inspect details</div>
        </div>
      </div>
    </div>
  </div>

<script>
    const nodesData = {nodes_json};
    const edgesData = {edges_json};

    // 1. Pre-calculate formatted nodes with all styling applied
    const formattedNodes = nodesData.map(n => ({{
      id: n.id,
      label: n.label,
      group: n.group,
      path: n.path,
      line: n.line,
      font: {{
        face: 'JetBrains Mono',
        color: '#e6edf3',
        size: n.group === 0 ? 14 : 12
      }},
      shape: 'dot',
      borderWidth: 2,
      size: n.group === 0 ? 28 : n.group === 1 ? 18 : Math.max(8, 16 - (n.group - 1) * 2),
      color: {{
        background: n.group === 0 ? '#f85149' : '#161b22',
        border: n.group === 0 ? '#f85149' : n.group === 1 ? '#d29922' : `hsl(210, 80%, ${{Math.max(30, 70 - (n.group - 1) * 10)}}%)`,
        highlight: {{
          background: n.group === 0 ? '#f85149' : '#1f6feb',
          border: '#fff'
        }}
      }}
    }}));

    // 2. Pre-calculate formatted edges with all styling applied
    const formattedEdges = edgesData.map(e => ({{
      from: e.from,
      to: e.to,
      arrows: {{ to: {{ enabled: true, scaleFactor: 0.5 }} }},
      color: {{ color: '#30363d', highlight: '#8b949e' }},
      width: 1,
      smooth: {{ type: 'curvedCW', roundness: 0.1 }}
    }}));

    // Calculate stats
    const directCount = nodesData.filter(n => n.group === 1).length;
    const totalCount = nodesData.filter(n => n.group > 0).length;
    document.getElementById('stat-direct').textContent = directCount;
    document.getElementById('stat-total').textContent = totalCount;

    // 3. Setup network using the formatted arrays instead of mapping inline
    const nodes = new vis.DataSet(formattedNodes);
    const edges = new vis.DataSet(formattedEdges);

    const container = document.getElementById('mynetwork');
    const network = new vis.Network(container, {{ nodes, edges }}, {{
      physics: {{
        forceAtlas2Based: {{
          gravitationalConstant: -50,
          springLength: 120,
          springConstant: 0.05,
          damping: 0.4
        }},
        solver: 'forceAtlas2Based',
        stabilization: {{ iterations: 150, fit: true }},
        adaptiveTimestep: true
      }},
      interaction: {{
        hover: true,
        tooltipDelay: 100
      }}
    }});

    // Inspector Logic
    network.on("click", function (params) {{
      if (params.nodes.length > 0) {{
        const nodeId = params.nodes[0];
        const node = nodesData.find(n => n.id === nodeId);

        const classification =
          node.group === 0 ? 'target' :
          node.group === 1 ? 'direct' : 'ripple';

        const classText =
          node.group === 0 ? 'TARGET · Root Change' :
          node.group === 1 ? 'DIRECT · High Risk' :
          `RIPPLE · Depth ${{node.group}}`;

        const inspectorHTML = `
          <div class="card">
            <div class="card-label">Selected Symbol</div>
            <div class="card-value">${{node.label}}</div>
          </div>

          <div class="card">
            <div class="card-label">Classification</div>
            <span class="badge ${{classification}}">${{classText}}</span>
          </div>

          <div class="card">
            <div class="card-label">Call Site Preview</div>
            <div class="code-preview">
              <div class="code-header">
                <span class="code-file">${{node.path}}</span>
                <span class="code-line-badge">Line ${{node.line}}</span>
              </div>
              <div class="code-content">
                <div class="code-line">
                  <span class="line-num">40</span>
                  <span class="line-code">def process_data(items):</span>
                </div>
                <div class="code-line">
                  <span class="line-num">41</span>
                  <span class="line-code">    results = []</span>
                </div>
                <div class="code-line highlight">
                  <span class="line-num">42</span>
                  <span class="line-code">    ${{node.label}}(item)</span>
                </div>
                <div class="code-line">
                  <span class="line-num">43</span>
                  <span class="line-code">    return results</span>
                </div>
              </div>
            </div>
          </div>

          <a href="vscode://file/${{node.path}}:${{node.line}}" class="btn">Open in Editor</a>
          <button class="btn btn-secondary" onclick="network.focus('${{node.id}}', {{ scale: 1.5, animation: true }})">Focus Node</button>
        `;

        document.getElementById('inspector-content').innerHTML = inspectorHTML;
      }}
    }});

    // Graph Controls
    document.getElementById('btn-fit').addEventListener('click', () => {{
      network.fit({{ animation: {{ duration: 300 }} }});
    }});

    document.getElementById('btn-zoom-in').addEventListener('click', () => {{
      network.moveTo({{ scale: network.getScale() * 1.2 }});
    }});

    document.getElementById('btn-zoom-out').addEventListener('click', () => {{
      network.moveTo({{ scale: network.getScale() * 0.8 }});
    }});

    // Depth slider
    document.getElementById('depth-slider').addEventListener('input', function() {{
        const depth = parseInt(this.value);
        document.getElementById('depth-label').textContent = depth;

        // 4. Filter against the fully styled arrays
        const filteredNodes = formattedNodes.filter(n => n.group <= depth);
        const filteredNodeIds = new Set(filteredNodes.map(n => n.id));
        const filteredEdges = formattedEdges.filter(e =>
            filteredNodeIds.has(e.from) && filteredNodeIds.has(e.to)
        );

        nodes.clear();
        edges.clear();
        nodes.add(filteredNodes);
        edges.add(filteredEdges);
    }});

    // Auto-fit after stabilization
    network.once('stabilizationIterationsDone', () => {{
      setTimeout(() => network.fit({{ animation: {{ duration: 500 }} }}), 100);
    }});
  </script>
</body>
</html>"""

    filename = "impact_graph.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    return filename

# ==========================================
# 🚀 COMMAND: IMPACT
# ==========================================

def cmd_impact(args):
    W = 64
    print()
    print(f"{BG_DARK}{CYAN}{BOLD}  N3MO  {R}{GRAY}  ◈  impact tracker{R}")
    print(f"{GRAY}  {'─' * W}{R}")

    conn = get_connection()
    symbol_name = args.symbol
    file_filter = args.file if hasattr(args, 'file') else None
    filename = None
    try:
        with conn.cursor() as cur:
            target_dir = os.getenv("TARGET_CODE_DIR", os.getcwd())
            cur.execute("SELECT id FROM projects WHERE repo_url = %s", (target_dir,))
            proj = cur.fetchone()
            if not proj:
                print(f"\n  {RED}✗{R} No index found for this directory. Run `n3mo index` first.\n")
                return
            project_id = proj[0]

            if file_filter:
                cur.execute(
                    "SELECT id, name, file_path, start_line FROM symbols WHERE name = %s AND project_id = %s AND file_path LIKE %s LIMIT 1",
                    (symbol_name, project_id, f"%{file_filter}%")
                )
            else:
                cur.execute(
                    "SELECT id, name, file_path, start_line FROM symbols WHERE name = %s AND project_id = %s LIMIT 1",
                    (symbol_name, project_id)
                )
            target = cur.fetchone()
            if not target:
                print(f"\n  {RED}✗{R} Symbol {WHITE}'{symbol_name}'{R} not found in index.\n")
                return
            target_id, real_name, target_file, target_start_line = target
            print(f"\n  {DIM}Analyzing{R}  {AMBER}{BOLD}{real_name}{R}")
            print(f"  {GRAY}Location: {DIM}{target_file}{R}\n")

            query = """
            WITH RECURSIVE impact_chain AS (
                SELECT s.name AS source, s.file_path, c.line_number, 1 AS depth, target_sym.name AS target, c.source_symbol_id AS source_id
                FROM calls c
                JOIN symbols s ON c.source_symbol_id = s.id
                JOIN symbols target_sym ON c.resolved_symbol_id = target_sym.id
                WHERE c.resolved_symbol_id = %s
                UNION ALL
                SELECT s.name, s.file_path, c.line_number, ic.depth + 1, ic.source, c.source_symbol_id
                FROM impact_chain ic
                JOIN calls c ON c.resolved_symbol_id = ic.source_id
                JOIN symbols s ON c.source_symbol_id = s.id
                WHERE ic.depth < %s + 1
            )
            SELECT DISTINCT source, file_path, line_number, depth, target
            FROM impact_chain ORDER BY depth ASC, file_path;
            """
            cur.execute(query, (target_id, args.depth))
            results = cur.fetchall()
            if not results:
                print(f"  {CYAN}✓{R}  Safe to change — no dependencies found.\n")
                return
            print_ascii_tree(results, real_name)

            if args.graph:
                # Auto-detect terminal directory so VS Code links work perfectly
                base_dir = args.root or os.getcwd()

                target_full_path = f"{base_dir}/{target_file}".replace("\\", "/") if target_file else ""
                target_start_line = target_start_line or 1
                target_code_ctx = get_code_context(target_full_path, target_start_line)

                nodes_map = {real_name: {"group": 0, "path": target_full_path, "line": target_start_line, "code_context": target_code_ctx}}
                edges = set()

                for source, path, line, depth, target_node in results:
                    s_group = depth
                    t_group = max(depth - 1, 0)
                    if target_node == real_name:
                        t_group = 0

                    full_path = ""
                    if path:
                        full_path = f"{base_dir}/{path}".replace("\\", "/")

                    code_ctx = get_code_context(full_path, line)

                    if source not in nodes_map or s_group < nodes_map[source]["group"]:
                        nodes_map[source] = {"group": s_group, "path": full_path, "line": line, "code_context": code_ctx}
                    if target_node not in nodes_map or t_group < nodes_map[target_node]["group"]:
                        nodes_map[target_node] = {"group": t_group, "path": full_path, "line": line, "code_context": code_ctx}
                    edges.add((source, target_node))

                nodes_set = list(nodes_map.items())
                filename = generate_solar_graph_html(nodes_set, edges, real_name, args.depth)
                abs_filename = os.path.abspath(filename)
                serve_dir = os.path.dirname(abs_filename)
                serve_file = os.path.basename(abs_filename)
                url = f"http://127.0.0.1:8080/{serve_file}"

                print(f"  {CYAN}◈{R}  Graph ready")
                print(f"  {BOLD}{WHITE}Server:{R}  {BLUE}\033[4m{url}\033[0m{R}")
                print(f"  {CYAN}◈{R}  Opening browser automatically... Press Ctrl+C to stop server")

                import subprocess
                import threading
                import webbrowser

                # Bind to 127.0.0.1 to avoid Windows Firewall popups
                server = subprocess.Popen(
                    ["python", "-m", "http.server", "8080", "--bind", "127.0.0.1"],
                    cwd=serve_dir
                )

                # Wait 1.5s for the server to boot, then pop the browser
                threading.Timer(1.5, lambda: webbrowser.open(url)).start()

                try:
                    server.wait()
                except KeyboardInterrupt:
                    server.terminate()
                    print(f"\n  {CYAN}◈{R}  Server stopped.")

    except KeyboardInterrupt:
        print(f"\n  {GRAY}Shutting down…{R}\n")
    except Exception as e:
        print(f"\n  {RED}✗  Error:{R} {e}\n")
    finally:
        if conn: conn.close()
        # Keep the file so the server can actually serve it!
        # if filename and os.path.exists(filename):
        #     os.remove(filename)


def cmd_clean(args):
    target_dir = os.getenv("TARGET_CODE_DIR", os.getcwd())
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM projects WHERE repo_url = %s RETURNING name", (target_dir,))
            row = cur.fetchone()
            conn.commit()
            if row:
                print(f"🗑️  Index cleared for project '{row[0]}'")
            else:
                print(f"⚠️  No index found for {target_dir}")
    finally:
        conn.close()


def main():
    if sys.stdout.encoding != 'utf-8':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    parser = argparse.ArgumentParser(prog="n3mo")
    subparsers = parser.add_subparsers(dest='command')
    parser_impact = subparsers.add_parser('impact')
    parser_impact.add_argument('symbol')
    parser_impact.add_argument('--graph', action='store_true')
    parser_impact.add_argument('--file', help="Filter by file path", default=None)
    parser_impact.add_argument('--depth', type=int, default=3, help="Blast radius depth (default: 3, max recommended: 5)")
    parser_impact.add_argument('--root', help="Absolute Windows path to project root for VS Code links", default="")
    parser_impact.set_defaults(func=cmd_impact)
    parser_index = subparsers.add_parser('index')
    parser_index.set_defaults(func=lambda args: run_indexer_logic())
    parser_clean = subparsers.add_parser('clean')
    parser_clean.set_defaults(func=cmd_clean)
    args = parser.parse_args()
    if hasattr(args, 'func'): args.func(args)


if __name__ == '__main__':
    main()