# Copyright (C) 2026 Raj shekhar
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from psycopg2.extras import execute_values
from psycopg2 import pool
import os
import uuid



_pool = None

def get_pool():
    global _pool
    if _pool is None:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            _pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                dsn=db_url
            )
        else:
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
    """Return a connection back to the pool, ensuring aborted transactions are cleared."""
    if conn:
        try:
            if not conn.closed:
                conn.rollback()
        except Exception:
            pass
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
                seen_syms = set()
                unique_syms = []
                for sym in symbols:
                    key = (sym["parent_id"], sym["name"])
                    if key not in seen_syms:
                        seen_syms.add(key)
                        unique_syms.append(sym)

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
                        for sym in unique_syms
                    ],
                )

            if imports:
                seen_imps = set()
                unique_imps = []
                for imp in imports:
                    key = (imp["module"], imp.get("name"), imp.get("alias"))
                    if key not in seen_imps:
                        seen_imps.add(key)
                        unique_imps.append(imp)

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
                        for imp in unique_imps
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



# 6. File Hashing Helpers for Incremental Indexing
def get_file_hashes(project_id):
    """Retrieve all file paths and their SHA-256 hashes for a project."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT file_path, sha256 FROM files WHERE project_id = %s", (project_id,))
            return {row[0]: row[1] for row in cur.fetchall()}
    finally:
        release_connection(conn)

def upsert_file_hash(project_id, file_path, sha256):
    """Insert or update a file's SHA-256 hash."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO files (project_id, file_path, sha256)
                VALUES (%s, %s, %s)
                ON CONFLICT (project_id, file_path)
                DO UPDATE SET sha256 = EXCLUDED.sha256
                """,
                (project_id, file_path, sha256)
            )
            conn.commit()
    finally:
        release_connection(conn)

def delete_file_index(project_id, file_path):
    """Fully remove a file's index records and hash from the database."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Clear links to definitions in this file
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
            # Delete calls from this file
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
            # Delete imports from this file
            cur.execute(
                "DELETE FROM imports WHERE project_id = %s AND file_path = %s",
                (project_id, file_path),
            )
            # Delete symbols from this file
            cur.execute(
                "DELETE FROM symbols WHERE project_id = %s AND file_path = %s",
                (project_id, file_path),
            )
            # Delete file hash record
            cur.execute(
                "DELETE FROM files WHERE project_id = %s AND file_path = %s",
                (project_id, file_path),
            )
            conn.commit()
    finally:
        release_connection(conn)

