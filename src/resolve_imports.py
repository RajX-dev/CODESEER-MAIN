from database import get_connection

def resolve_import_links(project_id):
    print("🔗 Resolving Imports...")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Simple Logic: If I import 'x', connect it to the symbol 'x'
            query = """
            UPDATE imports i
            SET resolved_symbol_id = s.id
            FROM symbols s
            WHERE i.name = s.name
            AND i.project_id = s.project_id
            AND s.project_id = %s
            AND i.resolved_symbol_id IS NULL;
            """
            cur.execute(query, (project_id,))
            conn.commit()
    finally:
        conn.close()