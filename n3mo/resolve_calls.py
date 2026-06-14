import logging
from psycopg2.extras import execute_values
from n3mo.database import get_connection, release_connection
from n3mo.resolve_imports import get_candidate_file_paths

logger = logging.getLogger("n3mo")

def resolve_call_links(project_id):
    logger.info("🔗 Linking function calls (Scope-Aware Strategy)...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Fetch all symbols in the project
            cur.execute(
                "SELECT id, name, file_path, parent_id FROM symbols WHERE project_id = %s",
                (project_id,)
            )
            symbols_rows = cur.fetchall()
            
            # Map of symbol_id -> symbol_info
            symbol_by_id = {}
            # Map of (file_path, name) -> list of symbol_ids
            symbols_by_file_name = {}
            # Map of name -> list of symbol_ids (global fallback)
            symbols_by_name = {}
            # Map of (class_id, name) -> symbol_id
            symbols_by_class_member = {}
            
            for s_id, s_name, s_file, s_parent in symbols_rows:
                s_file_norm = s_file.replace('\\', '/')
                symbol_info = {
                    "id": s_id,
                    "name": s_name,
                    "file_path": s_file_norm,
                    "parent_id": s_parent
                }
                symbol_by_id[s_id] = symbol_info
                
                symbols_by_file_name.setdefault((s_file_norm, s_name), []).append(s_id)
                symbols_by_name.setdefault(s_name, []).append(s_id)
                if s_parent:
                    symbols_by_class_member[(s_parent, s_name)] = s_id

            # 2. Fetch all resolved imports
            cur.execute(
                "SELECT file_path, module, name, alias, resolved_symbol_id FROM imports WHERE project_id = %s",
                (project_id,)
            )
            imports_rows = cur.fetchall()
            
            # Map of (file_path, import_alias_or_name) -> resolved_symbol_id
            imports_by_alias = {}
            # Map of (file_path, import_alias_or_name) -> module_name
            imports_modules_by_alias = {}
            
            for imp_file, imp_mod, imp_name, imp_alias, resolved_id in imports_rows:
                imp_file_norm = imp_file.replace('\\', '/')
                alias = imp_alias or imp_name
                if alias:
                    if resolved_id:
                        imports_by_alias[(imp_file_norm, alias)] = resolved_id
                    imports_modules_by_alias[(imp_file_norm, alias)] = imp_mod
                else:
                    # e.g., import module_name
                    # we can map the last part of module path as alias
                    mod_alias = imp_mod.split('.')[-1].split('/')[-1]
                    imports_modules_by_alias[(imp_file_norm, mod_alias)] = imp_mod

            # 3. Fetch all calls
            cur.execute(
                "SELECT id, source_symbol_id, call_name, line_number FROM calls WHERE project_id = %s",
                (project_id,)
            )
            calls_rows = cur.fetchall()
            
            resolved_calls = []
            for call_id, src_sym_id, call_name, line in calls_rows:
                src_sym = symbol_by_id.get(src_sym_id)
                if not src_sym:
                    continue
                
                caller_file = src_sym["file_path"]
                parent_id = src_sym["parent_id"]
                
                norm_call_name = call_name
                is_method_call = False
                if norm_call_name.startswith("self."):
                    norm_call_name = norm_call_name[5:]
                    is_method_call = True
                elif norm_call_name.startswith("this."):
                    norm_call_name = norm_call_name[5:]
                    is_method_call = True
                
                matched_id = None
                
                # --- STRATEGY A: Class Scope (class members) ---
                if parent_id and (parent_id, norm_call_name) in symbols_by_class_member:
                    matched_id = symbols_by_class_member[(parent_id, norm_call_name)]
                
                # --- STRATEGY B: Local File Scope ---
                if not matched_id and not is_method_call:
                    local_syms = symbols_by_file_name.get((caller_file, norm_call_name))
                    if local_syms:
                        matched_id = local_syms[0]
                
                # --- STRATEGY C: Direct Imports ---
                if not matched_id and not is_method_call:
                    matched_id = imports_by_alias.get((caller_file, norm_call_name))
                
                # --- STRATEGY D: Qualified Imports (e.g. module.func) ---
                if not matched_id and '.' in norm_call_name:
                    parts = norm_call_name.split('.')
                    prefix = parts[0]
                    suffix = parts[-1]
                    
                    imported_module = imports_modules_by_alias.get((caller_file, prefix))
                    if imported_module:
                        candidates = get_candidate_file_paths(caller_file, imported_module)
                        for candidate in candidates:
                            cand_syms = symbols_by_file_name.get((candidate, suffix))
                            if cand_syms:
                                matched_id = cand_syms[0]
                                break
                                
                # --- STRATEGY E: Global Fallback ---
                if not matched_id:
                    global_syms = symbols_by_name.get(norm_call_name)
                    if global_syms:
                        matched_id = global_syms[0]
                        
                if matched_id:
                    resolved_calls.append((matched_id, call_id))
            
            # 4. Write back to database in bulk
            if resolved_calls:
                update_query = """
                UPDATE calls AS c 
                SET resolved_symbol_id = v.resolved_id::uuid 
                FROM (VALUES %s) AS v(resolved_id, call_id)
                WHERE c.id = v.call_id::uuid;
                """
                execute_values(cur, update_query, resolved_calls)
                conn.commit()
                logger.info(f"🔗 Resolved {len(resolved_calls)} calls using scope-aware analysis.")
            else:
                logger.info("🔗 No calls resolved.")
                
    except Exception as e:
        logger.error(f"❌ Call resolution failed: {e}")
        conn.rollback()
    finally:
        release_connection(conn)