import psycopg2
from psycopg2.extras import RealDictCursor
import os
import uuid

# 1. Database Connection Config
def get_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        database=os.getenv("POSTGRES_DB", "codeseer"),
        user=os.getenv("POSTGRES_USER", "codeseer"),
        password=os.getenv("POSTGRES_PASSWORD", "codeseer")
    )

# 2. Ensure Project Exists (We need a Project ID before we can add symbols)
def ensure_project(name, repo_url):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Try to find existing project
            cur.execute("SELECT id FROM projects WHERE repo_url = %s", (repo_url,))
            result = cur.fetchone()
            
            if result:
                return result[0] # Return existing UUID
            
            # If not found, create new one
            new_id = str(uuid.uuid4())
            cur.execute(
                "INSERT INTO projects (id, name, repo_url) VALUES (%s, %s, %s) RETURNING id",
                (new_id, name, repo_url)
            )
            conn.commit()
            return new_id
    finally:
        conn.close()

# 3. Upsert Symbol (The Magic Function)
def upsert_symbol(project_id, symbol_data):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # We use ON CONFLICT to handle duplicates gracefully
            # Note: We rely on the unique constraint (project_id, file_path, parent_id, name)
            
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
                symbol_data["id"],          # We generated this in extraction, but might ignore it if updating
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
            return cur.fetchone()[0] # Return the UUID (either new or existing)
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Error inserting {symbol_data['name']}: {e}")
        raise e
    finally:
        conn.close()