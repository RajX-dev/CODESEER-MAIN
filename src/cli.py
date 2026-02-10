import sys
import os
import argparse
import json
import http.server
import socketserver
from database import get_connection

# Try to import the indexer logic
try:
    from run_indexer import main as run_indexer_logic
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

def generate_graph_html(nodes, edges, target_name):
    nodes_list = [{"id": n, "label": n, "group": g} for n, g in nodes]
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

    // Calculate stats
    const directCount = nodesData.filter(n => n.group === 1).length;
    const totalCount = nodesData.filter(n => n.group > 0).length;
    document.getElementById('stat-direct').textContent = directCount;
    document.getElementById('stat-total').textContent = totalCount;

    // Setup network
    const nodes = new vis.DataSet(nodesData.map(n => ({{
      id: n.id,
      label: n.label,
      group: n.group,
      font: {{ 
        face: 'JetBrains Mono', 
        color: '#e6edf3',
        size: n.group === 0 ? 14 : 12
      }},
      shape: 'dot',
      borderWidth: 2,
      size: n.group === 0 ? 28 : n.group === 1 ? 18 : 12,
      color: {{
        background: n.group === 0 ? '#f85149' : '#161b22',
        border: n.group === 0 ? '#f85149' : n.group === 1 ? '#d29922' : '#2f81f7',
        highlight: {{ 
          background: n.group === 0 ? '#f85149' : '#1f6feb', 
          border: '#fff' 
        }}
      }}
    }})));

    const edges = new vis.DataSet(edgesData.map(e => ({{
      from: e.from, 
      to: e.to,
      arrows: {{ to: {{ enabled: true, scaleFactor: 0.5 }} }},
      color: {{ color: '#30363d', highlight: '#8b949e' }},
      width: 1,
      smooth: {{ type: 'curvedCW', roundness: 0.1 }}
    }})));

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
        stabilization: {{ iterations: 150 }}
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
                <span class="code-file">example.py</span>
                <span class="code-line-badge">Line 42</span>
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

          <a href="vscode://file/${{node.id}}" class="btn">Open in Editor</a>
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
    filename = None
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, file_path FROM symbols WHERE name = %s LIMIT 1", (symbol_name,))
            target = cur.fetchone()
            if not target:
                print(f"\n  {RED}✗{R} Symbol {WHITE}'{symbol_name}'{R} not found in index.\n")
                return
            target_id, real_name, target_file = target
            print(f"\n  {DIM}Analyzing{R}  {AMBER}{BOLD}{real_name}{R}")
            print(f"  {GRAY}Location: {DIM}{target_file}{R}\n")

            query = """
            WITH RECURSIVE impact_chain AS (
                SELECT s.name AS source, s.file_path, c.line_number, 1 AS depth, target_sym.name AS target
                FROM calls c
                JOIN symbols s ON c.source_symbol_id = s.id
                JOIN symbols target_sym ON c.resolved_symbol_id = target_sym.id
                WHERE c.resolved_symbol_id = %s
                UNION ALL
                SELECT s.name, s.file_path, c.line_number, ic.depth + 1, ic.source
                FROM impact_chain ic
                JOIN symbols current_target ON current_target.name = ic.source
                JOIN calls c ON c.resolved_symbol_id = current_target.id
                JOIN symbols s ON c.source_symbol_id = s.id
                WHERE ic.depth < 5
            )
            SELECT DISTINCT source, file_path, line_number, depth, target
            FROM impact_chain ORDER BY depth ASC, file_path;
            """
            cur.execute(query, (target_id,))
            results = cur.fetchall()
            if not results:
                print(f"  {CYAN}✓{R}  Safe to change — no dependencies found.\n")
                return
            print_ascii_tree(results, real_name)

            if args.graph:
                nodes_map = {real_name: 0}
                edges = set()
                for source, path, line, depth, target in results:
                    s_group = 1 if depth == 1 else 2
                    t_group = 1 if depth == 2 else 2
                    if target == real_name: t_group = 0
                    if source not in nodes_map or s_group < nodes_map[source]: nodes_map[source] = s_group
                    if target not in nodes_map or t_group < nodes_map[target]: nodes_map[target] = t_group
                    edges.add((source, target))

                nodes_set = set(nodes_map.items())
                filename = generate_graph_html(nodes_set, edges, real_name)

                PORT = 8000
                Handler = http.server.SimpleHTTPRequestHandler
                socketserver.TCPServer.allow_reuse_address = True
                print(f"  {CYAN}◈{R}  Graph ready")
                print(f"  {GRAY}{'─' * W}{R}")
                with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
                    print(f"  {BOLD}{WHITE}Server:{R}  {BLUE}\033[4mhttp://localhost:{PORT}/{filename}\033[0m{R}")
                    print(f"  {GRAY}Press Ctrl+C to exit{R}\n")
                    httpd.serve_forever()

    except KeyboardInterrupt:
        print(f"\n  {GRAY}Shutting down…{R}\n")
    except Exception as e:
        print(f"\n  {RED}✗  Error:{R} {e}\n")
    finally:
        if conn: conn.close()
        if filename and os.path.exists(filename):
            os.remove(filename)


def main():
    parser = argparse.ArgumentParser(prog="n3mo")
    subparsers = parser.add_subparsers(dest='command')
    parser_impact = subparsers.add_parser('impact')
    parser_impact.add_argument('symbol')
    parser_impact.add_argument('--graph', action='store_true')
    parser_impact.set_defaults(func=cmd_impact)
    parser_index = subparsers.add_parser('index')
    parser_index.set_defaults(func=lambda args: run_indexer_logic())
    args = parser.parse_args()
    if hasattr(args, 'func'): args.func(args)

if __name__ == '__main__':
    main()