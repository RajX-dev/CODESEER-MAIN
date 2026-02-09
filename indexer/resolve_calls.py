from database import get_connection

def resolve_project_calls(project_id):
    conn = get_connection()
    try:
        print("🔗 Resolving Function Calls...")
        
        # We process calls in batches to avoid locking the DB
        
        # 1. STRATEGY: Resolve via Explicit Imports
        # Logic: If I call 'upsert_symbol' AND I have 'from database import upsert_symbol', 
        # then I know exactly which Symbol ID it is.
        
        query_imports = """
        UPDATE calls c
        SET resolved_symbol_id = i.resolved_symbol_id
        FROM imports i
        WHERE c.project_id = %s
          AND c.project_id = i.project_id
          AND c.resolved_symbol_id IS NULL  -- Only fix unresolved ones
          AND i.file_path = (SELECT file_path FROM symbols WHERE id = c.source_symbol_id) -- Same file
          AND i.name = c.call_name -- Name matches (e.g. "upsert_symbol")
          AND i.resolved_symbol_id IS NOT NULL;
        """
        
        with conn.cursor() as cur:
            cur.execute(query_imports, (project_id,))
            import_matches = cur.rowcount
            print(f"   ✅ Linked {import_matches} calls via Imports.")
            
        # 2. STRATEGY: Resolve via Local Definitions
        # Logic: If I call 'process_file' AND 'process_file' is defined in the same file.
        
        query_local = """
        UPDATE calls c
        SET resolved_symbol_id = s_target.id
        FROM symbols s_source, symbols s_target
        WHERE c.project_id = %s
          AND c.resolved_symbol_id IS NULL
          AND c.source_symbol_id = s_source.id
          -- Target must be in same file
          AND s_target.file_path = s_source.file_path
          AND s_target.name = c.call_name;
        """
        
        with conn.cursor() as cur:
            cur.execute(query_local, (project_id,))
            local_matches = cur.rowcount
            print(f"   ✅ Linked {local_matches} calls via Local Definitions.")

        conn.commit()
        
        total = import_matches + local_matches
        print(f"🎉 Call Resolution Complete. Resolved {total} calls.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error resolving calls: {e}")
    finally:
        conn.close()