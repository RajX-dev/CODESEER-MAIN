import os
from database import get_connection

def resolve_project_imports(project_id):
    conn = get_connection()
    try:
        # 1. Fetch all unresolved imports
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, file_path, module, name 
                FROM imports 
                WHERE project_id = %s AND resolved_symbol_id IS NULL
            """, (project_id,))
            imports = cur.fetchall() # Returns list of (id, file_path, module, name)

        print(f"🔗 Resolving {len(imports)} imports...")
        
        resolved_count = 0
        
        with conn.cursor() as cur:
            for imp in imports:
                imp_id, source_file, module, name = imp
                
                # --- RESOLUTION LOGIC ---
                # This is a naive implementation. Real Python resolution is complex.
                # Heuristic 1: If module is "utils", look for file "utils.py"
                
                # Convert dot notation to path: "libs.utils" -> "libs/utils"
                potential_path = module.replace(".", "/")
                
                # We search for a symbol that matches the NAME in a file that matches the MODULE
                query = """
                SELECT id FROM symbols 
                WHERE project_id = %s 
                  AND name = %s 
                  AND (
                      file_path LIKE %s OR 
                      file_path LIKE %s
                  )
                LIMIT 1
                """
                
                # Try finding "utils.py" OR "utils/__init__.py"
                path_variant_1 = f"%{potential_path}.py"
                path_variant_2 = f"%{potential_path}/__init__.py"
                
                cur.execute(query, (project_id, name, path_variant_1, path_variant_2))
                result = cur.fetchone()
                
                if result:
                    symbol_id = result[0]
                    # Update the import record to point to this symbol
                    cur.execute("""
                        UPDATE imports 
                        SET resolved_symbol_id = %s, is_resolved = TRUE 
                        WHERE id = %s
                    """, (symbol_id, imp_id))
                    resolved_count += 1
                    print(f"   ✅ Linked: {module}.{name} -> Symbol {symbol_id}")
                else:
                    # Optional: Print failures to debug
                    # print(f"   ❌ Could not resolve: {module}.{name}")
                    pass

            conn.commit()
            print(f"🎉 Resolution Complete. Linked {resolved_count}/{len(imports)} imports.")

    except Exception as e:
        conn.rollback()
        print(f"Error during resolution: {e}")
    finally:
        conn.close()