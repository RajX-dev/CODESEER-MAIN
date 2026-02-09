from typing import List
import psycopg2
from psycopg2.extras import execute_batch

from indexer.chunk import Chunk


def insert_chunks(conn, chunks: List[Chunk]) -> None:
    """
    Persist chunks into Postgres.
    Idempotent by design: duplicate chunk IDs are ignored.
    """
    if not chunks:
        return

    query = """
        INSERT INTO chunks (
            id,
            file_id,
            file_path,
            chunk_type,
            language,
            start_line,
            end_line,
            content
        )
        VALUES (
            %(id)s,
            %(file_id)s,
            %(file_path)s,
            %(chunk_type)s,
            %(language)s,
            %(start_line)s,
            %(end_line)s,
            %(content)s
        )
        ON CONFLICT (id) DO NOTHING;
    """

    rows = [
        {
            "id": c.id,
            "file_id": c.file_id,
            "file_path": c.file_path,
            "chunk_type": c.chunk_type,
            "language": c.language,
            "start_line": c.start_line,
            "end_line": c.end_line,
            "content": c.content,
        }
        for c in chunks
    ]

    with conn.cursor() as cur:
        execute_batch(cur, query, rows)

    conn.commit()
