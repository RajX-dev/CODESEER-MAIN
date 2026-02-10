import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid
import time

# 1. Database Connection Config
def get_connection():
    """
    Establishes a connection to the PostgreSQL database.
    Retries up to 5 times if the database is not ready.
    """
    max_retries = 5  # <--- FIXED (Was "5a")
    for i in range(max_retries):
        try:
            return psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "postgres"),
                database=os.getenv("POSTGRES_DB", "n3mo"),
                user=os.getenv("POSTGRES_USER", "n3mo"),
                password=os.getenv("POSTGRES_PASSWORD", "n3mo")
            )
        except psycopg2.OperationalError:
            if i < max_retries - 1:
                time.sleep(2)
                continue
            else:
                raise

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
        if conn: conn.close()

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
        if conn: conn.close()

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
        if conn: conn.close()

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
        if conn: conn.close()