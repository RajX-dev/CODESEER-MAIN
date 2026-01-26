import psycopg2
from elasticsearch import Elasticsearch

from indexer.chunk import (
    chunk_docs,
    chunk_config,
    chunk_python,
)
from indexer.chunk_store import insert_chunks


# ---- CONFIG ----
POSTGRES_DSN = "dbname=codeseer user=codeseer password=codeseer host=localhost port=5432"
ES_HOST = "http://localhost:9200"
ES_INDEX = "files"


def generate_chunks(file_path: str, content: str, language: str):
    """
    Route file content to the appropriate chunking strategy.
    """
    if language == "python":
        return chunk_python(file_path, content)

    if language in ("yaml", "yml", "env"):
        return chunk_config(file_path, content)

    if language in ("markdown", "md"):
        return chunk_docs(file_path, content)

    return []


def run_indexing():
    # ---- CONNECT ----
    pg_conn = psycopg2.connect(POSTGRES_DSN)
    pg_cursor = pg_conn.cursor()

    es = Elasticsearch(ES_HOST)

    # ---- CREATE INDEX IF NOT EXISTS ----
    if not es.indices.exists(index=ES_INDEX):
        es.indices.create(
            index=ES_INDEX,
            mappings={
                "properties": {
                    "path": {"type": "text"},
                    "language": {"type": "keyword"},
                    "size_bytes": {"type": "integer"},
                }
            }
        )

    print("Elasticsearch index ready")

    # ---- FETCH FILES FROM POSTGRES ----
    pg_cursor.execute("""
        SELECT id, path, language, size_bytes
        FROM files
    """)

    rows = pg_cursor.fetchall()
    print(f"Indexing {len(rows)} files")

    # ---- INDEX + CHUNK PIPELINE ----
    for file_id, path, language, size_bytes in rows:
        # ---- Phase 2: File-level indexing (unchanged) ----
        es.index(
            index=ES_INDEX,
            id=str(file_id),
            document={
                "path": path,
                "language": language,
                "size_bytes": size_bytes,
            }
        )

        # ---- Phase 3: Load content ----
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            print(f"Skipping content for {path}: {e}")
            continue

        # ---- Phase 3: Generate + Persist Chunks (Day 12) ----
        chunks = generate_chunks(path, content, language)
        insert_chunks(pg_conn, chunks)

    print("Indexing complete")

    pg_cursor.close()
    pg_conn.close()


if __name__ == "__main__":
    run_indexing()
