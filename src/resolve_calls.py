from src.database import get_connection, release_connection

def resolve_call_links(project_id):
    """
    Connects calls to definitions, handling 'self.' and 'module.' prefixes.
    """
    print("🔗 Linking function calls (Smart Strategy)...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # 1. Exact Match (Best case)
            query_exact = """
            UPDATE calls c
            SET resolved_symbol_id = s.id
            FROM symbols s
            WHERE c.call_name = s.name
            AND c.project_id = s.project_id
            AND s.project_id = %s
            AND c.resolved_symbol_id IS NULL;
            """
            cur.execute(query_exact, (project_id,))
            match_exact = cur.rowcount

            # 2. Smart Match - split at last '.' instead of LIKE
            query_smart = """
            UPDATE calls c
            SET resolved_symbol_id = s.id
            FROM symbols s
            WHERE SPLIT_PART(c.call_name, '.', -1) = s.name
            AND c.project_id = s.project_id
            AND s.project_id = %s
            AND c.resolved_symbol_id IS NULL;
            """
            cur.execute(query_smart, (project_id,))
            match_smart = cur.rowcount

            conn.commit()
            print(f"🔗 Connected {match_exact + match_smart} calls ({match_exact} exact, {match_smart} smart).")

    except Exception as e:
        print(f"❌ Linking failed: {e}")
    finally:
        release_connection(conn) 