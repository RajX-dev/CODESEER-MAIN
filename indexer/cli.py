import sys
import os
import argparse
import json
import webbrowser
from database import get_connection

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def get_code_context(file_path, line_number, context=2):
    """
    Reads the file at file_path and returns lines around line_number.
    """
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

# ==========================================
# 📊 GRAPH VISUALIZER (Pro UI Version)
# ==========================================

def generate_graph_html(nodes, edges, target_name):
    """
    Creates a modern, dark-themed interactive HTML graph.
    """
    nodes_list = [{"id": n, "label": n, "group": g} for n, g in nodes]
    edges_list = [{"from": u, "to": v} for u, v in edges]
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <title>CodeSeer Impact: {target_name}</title>
        <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
        <style>
            :root {{
                --bg-color: #0d1117;
                --text-primary: #e6edf3;
                --text-secondary: #8b949e;
                --danger-color: #ff4d4d;
                --warn-color: #ffbd2e;
                --info-color: #58a6ff;
                --border-color: #30363d;
            }}
            body {{ 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
                background: var(--bg-color); 
                color: var(--text-primary); 
                margin: 0; 
                overflow: hidden; 
            }}
            #mynetwork {{ 
                width: 100vw; 
                height: 100vh; 
                background: radial-gradient(circle at center, #161b22 0%, #0d1117 100%);
            }}
            .legend {{ 
                position: absolute; 
                top: 24px; 
                left: 24px; 
                background: rgba(22, 27, 34, 0.75); 
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                padding: 20px; 
                border-radius: 12px; 
                border: 1px solid var(--border-color);
                box-shadow: 0 8px 32px rgba(0,0,0,0.4); 
                z-index: 1000;
                min-width: 260px;
                animation: fadeIn 0.5s ease-out;
            }}
            h3 {{ 
                margin: 0 0 16px 0; 
                font-size: 16px; 
                font-weight: 600; 
                color: var(--text-primary);
                display: flex;
                align-items: center;
                gap: 8px;
            }}
            .item {{ 
                display: flex; 
                align-items: center; 
                margin-bottom: 12px; 
                font-size: 13px; 
                color: var(--text-secondary);
                font-family: 'JetBrains Mono', monospace;
            }}
            .item:last-child {{ margin-bottom: 0; }}
            .dot {{ 
                width: 10px; 
                height: 10px; 
                border-radius: 50%; 
                margin-right: 12px; 
                display: inline-block; 
                box-shadow: 0 0 8px currentColor;
            }}
            @keyframes fadeIn {{
                from {{ opacity: 0; transform: translateY(-10px); }}
                to {{ opacity: 1; transform: translateY(0); }}
            }}
        </style>
    </head>
    <body>
        <div class="legend">
            <h3>🔮 Blast Radius Analysis</h3>
            <div class="item" style="color: #ffaaaa"><span class="dot" style="background:var(--danger-color); color:var(--danger-color)"></span>{target_name} (Target)</div>
            <div class="item"><span class="dot" style="background:var(--warn-color); color:var(--warn-color)"></span>Direct Callers</div>
            <div class="item"><span class="dot" style="background:var(--info-color); color:var(--info-color)"></span>Ripple Effect</div>
        </div>
        <div id="mynetwork"></div>
        <script type="text/javascript">
            var nodes = new vis.DataSet({json.dumps(nodes_list)});
            var edges = new vis.DataSet({json.dumps(edges_list)});
            var container = document.getElementById('mynetwork');
            var data = {{ nodes: nodes, edges: edges }};
            var options = {{
                nodes: {{
                    shape: 'dot',
                    font: {{ 
                        size: 14, 
                        color: '#e6edf3', 
                        face: 'Inter',
                        strokeWidth: 4, 
                        strokeColor: '#0d1117'
                    }},
                    borderWidth: 2,
                    shadow: {{ enabled: true, color: 'rgba(0,0,0,0.5)', size: 10, x: 5, y: 5 }}
                }},
                groups: {{
                    0: {{ 
                        color: {{ background: '#ff4d4d', border: '#ff4d4d' }}, 
                        size: 30,
                        font: {{ size: 18, color: '#ffaaaa' }}
                    }}, 
                    1: {{ 
                        color: {{ background: '#ffbd2e', border: '#ffbd2e' }}, 
                        size: 15 
                    }}, 
                    2: {{ 
                        color: {{ background: '#58a6ff', border: '#58a6ff' }}, 
                        size: 10 
                    }}  
                }},
                edges: {{
                    width: 1,
                    color: {{ color: '#30363d', highlight: '#58a6ff', opacity: 0.6 }},
                    arrows: {{ to: {{ enabled: true, scaleFactor: 0.5 }} }},
                    smooth: {{ type: 'continuous', roundness: 0 }}
                }},
                interaction: {{
                    hover: true,
                    tooltipDelay: 200,
                    hideEdgesOnDrag: true
                }},
                physics: {{
                    stabilization: false,
                    forceAtlas2Based: {{
                        gravitationalConstant: -50,
                        centralGravity: 0.005,
                        springLength: 200,
                        springConstant: 0.08
                    }},
                    maxVelocity: 50,
                    solver: 'forceAtlas2Based',
                    timestep: 0.35,
                    adaptiveTimestep: true
                }}
            }};
            var network = new vis.Network(container, data, options);
        </script>
    </body>
    </html>
    """
    
    filename = "impact_graph.html"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html_content)
    return filename

# ==========================================
# 🚀 COMMAND: IMPACT
# ==========================================

def cmd_impact(args):
    print("\n🔮 CodeSeer CLI")
    print("==============================")
    conn = get_connection()
    symbol_name = args.symbol
    
    try:
        with conn.cursor() as cur:
            # 1. Find Target
            cur.execute("SELECT id, name, file_path FROM symbols WHERE name = %s LIMIT 1", (symbol_name,))
            target = cur.fetchone()
            
            if not target:
                print(f"❌ Symbol '{symbol_name}' not found.")
                return

            target_id, real_name, target_file = target
            print(f"🎯 Target: \033[1m{real_name}\033[0m")
            print(f"   Location: \033[90m{target_file}\033[0m")
            print("--------------------------------------------------")

            # 2. Recursive Query
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
                print("✅ Safe to change! No dependencies found.")
                return

            # --- MODE 1: LOCALHOST SERVER (GRAPH) ---
            if args.graph:
                print(f"🌊 Found {len(results)} connections. Preparing graph...")
                
                # Deduplication & Grouping Logic
                nodes_map = {real_name: 0} 
                edges = set()
                
                for source, path, line, depth, target in results:
                    s_group = 1 if depth == 1 else 2
                    t_group = 1 if depth == 2 else 2
                    if target == real_name: t_group = 0 
                    
                    if source not in nodes_map or s_group < nodes_map[source]:
                        nodes_map[source] = s_group
                        
                    if target not in nodes_map or t_group < nodes_map[target]:
                        nodes_map[target] = t_group

                    edges.add((source, target))
                
                nodes_set = set(nodes_map.items())
                filename = generate_graph_html(nodes_set, edges, real_name)
                
                import http.server
                import socketserver

                PORT = 8000
                Handler = http.server.SimpleHTTPRequestHandler

                print(f"\n🚀 \033[1;32mServer Running!\033[0m")
                print(f"   Open this URL: \033[4;34mhttp://localhost:9000/{filename}\033[0m")
                print("   (Press Ctrl+C to stop)")

                socketserver.TCPServer.allow_reuse_address = True
                
                # Bind to all interfaces
                with socketserver.TCPServer(("0.0.0.0", PORT), Handler) as httpd:
                    httpd.serve_forever()

            # --- MODE 2: TEXT LIST ---
            else:
                seen = set()
                for name, path, line, depth, target in results:
                    unique_key = (name, path, line)
                    if unique_key in seen: continue
                    seen.add(unique_key)
                    
                    human_line = line + 1
                    indent = "   " * (depth - 1)
                    icon = "🔥" if depth == 1 else "🧨"
                    print(f"{indent}{icon} \033[1m{name:<20}\033[0m \033[90min {path}:{human_line}\033[0m")
                    if depth == 1:
                        code_snippet = get_code_context(path, human_line, context=1)
                        for num, content in code_snippet:
                            if num == human_line:
                                print(f"{indent}   \033[31m{num:>4}: {content}\033[0m") 
                            else:
                                print(f"{indent}   \033[90m{num:>4}: {content}\033[0m")
                        print("")

    except Exception as e:
        print(f"❌ Error: {e}")
    except KeyboardInterrupt:
        print("\n🛑 Server stopped.")
    finally:
        if conn:
            conn.close()


# ==========================================
# 💀 COMMAND: UNUSED
# ==========================================

def cmd_unused(args):
    print("\n🔮 CodeSeer CLI")
    print("==============================")
    conn = get_connection()
    
    try:
        with conn.cursor() as cur:
            query = """
            SELECT s.name, s.file_path
            FROM symbols s
            LEFT JOIN calls c ON s.id = c.resolved_symbol_id
            WHERE c.id IS NULL
            AND s.name NOT LIKE '\\_\\_%'
            AND s.file_path NOT LIKE '%test%'
            ORDER BY s.file_path, s.name
            LIMIT 50;
            """
            
            cur.execute(query)
            results = cur.fetchall()
            
            if not results:
                print("✅ No dead code found! Your project is lean.")
            else:
                print(f"👻 \033[1mFound {len(results)} unused symbols (excluding tests):\033[0m")
                print("(Check these manually - they might be API endpoints or CLI entry points)")
                print("--------------------------------------------------")
                
                current_file = ""
                for name, path in results:
                    if path != current_file:
                        print(f"\n📂 \033[90m{path}\033[0m")
                        current_file = path
                    
                    print(f"   💀 {name:<30}")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()

# ==========================================
# 🏁 MAIN ENTRY POINT
# ==========================================

def main():
    parser = argparse.ArgumentParser(description="CodeSeer CLI Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    parser_impact = subparsers.add_parser('impact', help='Analyze blast radius')
    parser_impact.add_argument('symbol', help='The symbol to analyze')
    parser_impact.add_argument('--graph', action='store_true', help='Open visualization in browser')
    parser_impact.set_defaults(func=cmd_impact)

    parser_unused = subparsers.add_parser('unused', help='Find potential dead code')
    parser_unused.set_defaults(func=cmd_unused)

    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()