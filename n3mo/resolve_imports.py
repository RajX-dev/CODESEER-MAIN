import os
import logging
from psycopg2.extras import execute_values
from n3mo.database import get_connection, release_connection

logger = logging.getLogger("n3mo")

def get_candidate_file_paths(importer_file, module):
    candidates = []
    if not module:
        return candidates
    
    # Normalize path separators
    importer_file = importer_file.replace('\\', '/')
    importer_dir = os.path.dirname(importer_file)
    
    # Handle relative imports (starts with dot)
    if module.startswith('.'):
        dots_count = 0
        while dots_count < len(module) and module[dots_count] == '.':
            dots_count += 1
        
        module_path = module[dots_count:].replace('.', '/')
        
        # Resolve directory hierarchy based on dot count
        curr_dir = importer_dir
        for _ in range(dots_count - 1):
            if curr_dir:
                curr_dir = os.path.dirname(curr_dir)
        
        base_path = f"{curr_dir}/{module_path}" if curr_dir else module_path
        base_path = base_path.strip('/')
        
        # Common language extensions
        for ext in ['', '.py', '.js', '.jsx', '.ts', '.tsx', '/__init__.py', '/index.js', '/index.jsx', '/index.ts', '/index.tsx']:
            candidates.append(base_path + ext)
            
    else:
        # Absolute/standard dot-path (Python) or relative-like module paths (JS/TS modules or standard libs)
        py_path = module.replace('.', '/')
        direct_path = module.replace('\\', '/')
        
        for p in [py_path, direct_path]:
            for ext in ['', '.py', '.js', '.jsx', '.ts', '.tsx', '.go', '.rs', '.java', '/__init__.py', '/index.js', '/index.jsx', '/index.ts', '/index.tsx']:
                candidates.append(p + ext)
                
    return [c for c in candidates if c]


def resolve_import_links(project_id):
    logger.info("🔗 Resolving Imports (Scope-Aware)...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Fetch all symbols in the project
            cur.execute(
                "SELECT id, name, file_path, parent_id FROM symbols WHERE project_id = %s",
                (project_id,)
            )
            symbols_rows = cur.fetchall()
            
            # Map of (file_path, name) -> symbol_id
            symbols_map = {}
            for s_id, s_name, s_file, s_parent in symbols_rows:
                s_file_norm = s_file.replace('\\', '/')
                symbols_map[(s_file_norm, s_name)] = s_id
                
            # 2. Fetch all imports in the project
            cur.execute(
                "SELECT id, file_path, module, name, alias FROM imports WHERE project_id = %s",
                (project_id,)
            )
            imports_rows = cur.fetchall()
            
            resolved_imports = []
            for imp_id, imp_file, imp_mod, imp_name, imp_alias in imports_rows:
                # We only resolve imports where imp_name is present
                # (meaning it is a 'from X import Y' type import)
                if not imp_name:
                    continue
                
                candidates = get_candidate_file_paths(imp_file, imp_mod)
                matched_id = None
                for candidate in candidates:
                    # Look up if symbol exists in that candidate file path
                    if (candidate, imp_name) in symbols_map:
                        matched_id = symbols_map[(candidate, imp_name)]
                        break
                
                if matched_id:
                    resolved_imports.append((matched_id, imp_id))
            
            # 3. Update database in bulk
            if resolved_imports:
                update_query = """
                UPDATE imports AS i 
                SET resolved_symbol_id = v.resolved_id::uuid 
                FROM (VALUES %s) AS v(resolved_id, import_id)
                WHERE i.id = v.import_id::uuid;
                """
                execute_values(cur, update_query, resolved_imports)
                conn.commit()
                logger.info(f"🔗 Resolved {len(resolved_imports)} imports using scope-aware file paths.")
            else:
                logger.info("🔗 No imports found to resolve.")
                
    except Exception as e:
        logger.error(f"❌ Import resolution failed: {e}")
        conn.rollback()
    finally:
        release_connection(conn)
