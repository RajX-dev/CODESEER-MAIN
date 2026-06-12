import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from psycopg2 import pool
import os
import uuid
import time



_pool = None

def get_pool():
    global _pool
    if _pool is None:
        _pool = pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=10,
            host=os.getenv("POSTGRES_HOST", "localhost"),
            port=os.getenv("POSTGRES_PORT", "5432"),
            database=os.getenv("POSTGRES_DB", "n3mo"),
            user=os.getenv("POSTGRES_USER", "n3mo"),
            password=os.getenv("POSTGRES_PASSWORD", "n3mo")
        )
    return _pool

# 1. Database Connection Config
def get_connection():
    """Borrow a connection from the pool."""
    return get_pool().getconn()

def release_connection(conn):
    """Return a connection back to the pool."""
    if conn:
        get_pool().putconn(conn)

# 2. Ensure Project Exists
def ensure_project(name, repo_url):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM projects WHERE repo_url = %s", (repo_url,))
            result = cur.fetchone()
            
            if result:
                return result[0]
            
            new_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO projects (id, name, repo_url) VALUES (%s, %s, %s) RETURNING id",
                (new_id, name, repo_url)
            )
            conn.commit()
            return new_id
    finally:
        release_connection(conn)

# 3. Upsert Symbol
def upsert_symbol(project_id, symbol_data):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """
            INSERT INTO symbols 
                (id, project_id, parent_id, file_path, name, kind, signature, start_line, end_line)
            VALUES 
                (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (project_id, file_path, parent_id, name) 
            DO UPDATE SET 
            file_path = EXCLUDED.file_path,
            signature = EXCLUDED.signature,
            start_line = EXCLUDED.start_line,
            end_line = EXCLUDED.end_line
            RETURNING id;
            """
            
            cur.execute(query, (
                symbol_data["id"],
                project_id,
                symbol_data["parent_id"],
                symbol_data["file_path"],
                symbol_data["name"],
                symbol_data["kind"],
                symbol_data["signature"],
                symbol_data["start_line"],
                symbol_data["end_line"]
            ))
            
            conn.commit()
            result = cur.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        conn.rollback()
        if "duplicate key" not in str(e):
            print(f"❌ Error inserting {symbol_data['name']}: {e}")
        raise e
    finally:
        release_connection(conn)
def batch_upsert_symbols(project_id, symbols):
    """Insert all symbols for a file in one transaction."""
    if not symbols:
        return {}
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            values = [
                (
                    sym["id"],
                    project_id,
                    sym["parent_id"],
                    sym["file_path"],
                    sym["name"],
                    sym["kind"],
                    sym["signature"],
                    sym["start_line"],
                    sym["end_line"]
                )
                for sym in symbols
            ]
            
            execute_values(cur, """
                INSERT INTO symbols 
                    (id, project_id, parent_id, file_path, name, kind, signature, start_line, end_line)
                VALUES %s
                ON CONFLICT (project_id, file_path, parent_id, name)
                DO UPDATE SET
                    file_path = EXCLUDED.file_path,
                    signature = EXCLUDED.signature,
                    start_line = EXCLUDED.start_line,
                    end_line = EXCLUDED.end_line
                RETURNING id, name
            """, values)
            
            rows = cur.fetchall()
            conn.commit()
            
            return {row[1]: row[0] for row in rows}
    finally:
        release_connection(conn)

def batch_upsert_imports(project_id, imports):
    """Insert all imports for a file in one transaction."""
    if not imports:
        return
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            values = [
                (
                    imp["id"],
                    project_id,
                    imp["file_path"],
                    imp["module"],
                    imp["name"],
                    imp["alias"]
                )
                for imp in imports
            ]
            
            execute_values(cur, """
                INSERT INTO imports 
                    (id, project_id, file_path, module, name, alias)
                VALUES %s
                ON CONFLICT (project_id, file_path, module, name)
                DO NOTHING
            """, values)
            
            conn.commit()
    finally:
        release_connection(conn)

def replace_file_index(project_id, file_path, symbols, imports, calls):
    """Replace one file's graph records using a single transaction."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Clear links to definitions that are about to receive new IDs.
            cur.execute(
                """
                UPDATE calls
                SET resolved_symbol_id = NULL
                WHERE resolved_symbol_id IN (
                    SELECT id
                    FROM symbols
                    WHERE project_id = %s AND file_path = %s
                )
                """,
                (project_id, file_path),
            )
            cur.execute(
                """
                DELETE FROM calls
                WHERE project_id = %s
                  AND source_symbol_id IN (
                      SELECT id
                      FROM symbols
                      WHERE project_id = %s AND file_path = %s
                  )
                """,
                (project_id, project_id, file_path),
            )
            cur.execute(
                "DELETE FROM imports WHERE project_id = %s AND file_path = %s",
                (project_id, file_path),
            )
            cur.execute(
                "DELETE FROM symbols WHERE project_id = %s AND file_path = %s",
                (project_id, file_path),
            )

            if symbols:
                execute_values(
                    cur,
                    """
                    INSERT INTO symbols
                        (id, project_id, parent_id, file_path, name, kind,
                         signature, start_line, end_line)
                    VALUES %s
                    """,
                    [
                        (
                            sym["id"],
                            project_id,
                            sym["parent_id"],
                            file_path,
                            sym["name"],
                            sym["kind"],
                            sym["signature"],
                            sym["start_line"],
                            sym["end_line"],
                        )
                        for sym in symbols
                    ],
                )

            if imports:
                execute_values(
                    cur,
                    """
                    INSERT INTO imports
                        (id, project_id, file_path, module, name, alias)
                    VALUES %s
                    """,
                    [
                        (
                            imp["id"],
                            project_id,
                            file_path,
                            imp["module"],
                            imp["name"],
                            imp["alias"],
                        )
                        for imp in imports
                    ],
                )

            if calls:
                execute_values(
                    cur,
                    """
                    INSERT INTO calls
                        (id, project_id, source_symbol_id, call_name, line_number)
                    VALUES %s
                    """,
                    [
                        (
                            call["id"],
                            project_id,
                            call["source_symbol_id"],
                            call["call_name"],
                            call["line_number"],
                        )
                        for call in calls
                    ],
                )

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)

# 4. Upsert Import
def upsert_import(project_id, import_data):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """
            INSERT INTO imports 
                (id, project_id, file_path, module, name, alias)
            VALUES 
                (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (project_id, file_path, module, name) 
            DO NOTHING
            RETURNING id;
            """
            
            cur.execute(query, (
                import_data["id"],
                project_id,
                import_data["file_path"],
                import_data["module"],
                import_data["name"],
                import_data["alias"]
            ))
            
            conn.commit()
            result = cur.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        conn.rollback()
        print(f"⚠️ Error inserting import {import_data['module']}: {e}")
        return None
    finally:
        release_connection(conn)

# 5. Upsert Call
def upsert_call(project_id, call_data):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            query = """
            INSERT INTO calls 
                (id, project_id, source_symbol_id, call_name, line_number)
            VALUES 
                (%s, %s, %s, %s, %s)
            """
            cur.execute(query, (
                call_data["id"],
                project_id,
                call_data["source_symbol_id"],
                call_data["call_name"],
                call_data["line_number"]
            ))
            conn.commit()
    except Exception as e:
        conn.rollback()
    finally:
        release_connection(conn)
