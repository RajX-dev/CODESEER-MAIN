import sys
import os
import argparse
from database import get_connection

# ==========================================
# 🛠️ HELPER FUNCTIONS
# ==========================================

def get_code_context(file_path, line_number, context=2):
    """
    Reads the file at file_path and returns lines around line_number.
    context=2 means show 2 lines before and 2 lines after.
    """
    if not os.path.exists(file_path):
        return []

    # Ensure we don't go below line 1
    start = max(1, line_number - context)
    end = line_number + context
    
    results = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Enumerate starts at 1 to match human line numbers
            for current_line_num, content in enumerate(f, 1):
                if current_line_num >= start and current_line_num <= end:
                    # Strip newline characters for cleaner printing
                    results.append((current_line_num, content.rstrip()))
                
                if current_line_num > end:
                    break
    except Exception:
        return []

    return results

# ==========================================
# 🚀 COMMAND: IMPACT (Blast Radius)
# ==========================================

def cmd_impact(args):
    """
    Shows which functions depend on the given symbol (Recursive Blast Radius).
    Usage: python cli.py impact "upsert_symbol"
    """
    print("\n🔮 CodeSeer CLI")
    print("==============================")
    conn = get_connection()
    symbol_name = args.symbol
    
    try:
        with conn.cursor() as cur:
            # 1. Find Target Symbol ID
            cur.execute("SELECT id, name, file_path FROM symbols WHERE name = %s LIMIT 1", (symbol_name,))
            target = cur.fetchone()
            
            if not target:
                print(f"❌ Symbol '{symbol_name}' not found.")
                return

            target_id, real_name, target_file = target
            print(f"🎯 Target: \033[1m{real_name}\033[0m")
            print(f"   Location: \033[90m{target_file}\033[0m")
            print("--------------------------------------------------")

            # 2. Recursive Query (The "Blast Radius")
            # Returns 4 columns: name, file_path, line_number, DEPTH
            query = """
            WITH RECURSIVE impact_chain AS (
                -- Base Case: Direct callers of the target symbol
                SELECT 
                    s.id AS symbol_id,
                    s.name AS function_name,
                    s.file_path,
                    c.line_number,
                    1 AS depth
                FROM calls c
                JOIN symbols s ON c.source_symbol_id = s.id
                WHERE c.resolved_symbol_id = %s
                
                UNION ALL
                
                -- Recursive Step: Find callers of the symbols found above
                SELECT 
                    s.id,
                    s.name,
                    s.file_path,
                    c.line_number,
                    ic.depth + 1
                FROM impact_chain ic
                JOIN calls c ON c.resolved_symbol_id = ic.symbol_id
                JOIN symbols s ON c.source_symbol_id = s.id
                WHERE ic.depth < 5  -- Safety limit to prevent infinite loops
            )
            SELECT DISTINCT function_name, file_path, line_number, depth 
            FROM impact_chain
            ORDER BY depth ASC, file_path;
            """
            
            cur.execute(query, (target_id,))
            callers = cur.fetchall()
            
            if not callers:
                print("✅ Safe to change! No dependencies found.")
            else:
                print(f"⚠️  IMPACT WARNING: Changing this breaks \033[1m{len(callers)}\033[0m places:")
                print("")
                
                for name, path, line, depth in callers:
                    # Fix off-by-one error (DB is 0-indexed, editors are 1-indexed)
                    human_line = line + 1
                    
                    # Indentation for indirect impacts
                    indent = "   " * (depth - 1)
                    
                    # Visual cue for direct vs indirect impact
                    icon = "🔥" if depth == 1 else "🧨"
                    
                    # Print the function info
                    print(f"{indent}{icon} \033[1m{name:<20}\033[0m \033[90min {path}:{human_line}\033[0m")
                    
                    # Show code snippet ONLY for direct impacts (depth 1) to keep output clean
                    if depth == 1:
                        code_snippet = get_code_context(path, human_line, context=1)
                        for num, content in code_snippet:
                            if num == human_line:
                                # Highlight the specific line in RED
                                print(f"{indent}   \033[31m{num:>4}: {content}\033[0m") 
                            else:
                                # Context lines in GREY
                                print(f"{indent}   \033[90m{num:>4}: {content}\033[0m")
                        print("") # Add spacing

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()


# ==========================================
# 💀 COMMAND: UNUSED (Dead Code Finder)
# ==========================================

def cmd_unused(args):
    """
    Finds symbols that have 0 callers (potential dead code).
    Ignores test files to reduce noise.
    Usage: python cli.py unused
    """
    print("\n🔮 CodeSeer CLI")
    print("==============================")
    conn = get_connection()
    
    try:
        with conn.cursor() as cur:
            # FIX: Added filter to exclude test files
            query = """
            SELECT s.name, s.file_path
            FROM symbols s
            LEFT JOIN calls c ON s.id = c.resolved_symbol_id
            WHERE c.id IS NULL
            AND s.name NOT LIKE '\\_\\_%'      -- Exclude magic methods like __init__
            AND s.file_path NOT LIKE '%test%'  -- Exclude test files
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

    # 1. Impact Command
    parser_impact = subparsers.add_parser('impact', help='Analyze blast radius of a symbol change')
    parser_impact.add_argument('symbol', help='The function or class name to analyze')
    parser_impact.set_defaults(func=cmd_impact)

    # 2. Unused Command
    parser_unused = subparsers.add_parser('unused', help='Find potential dead code')
    parser_unused.set_defaults(func=cmd_unused)

    args = parser.parse_args()
    
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()