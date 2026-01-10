import psycopg2
from elasticsearch import Elasticsearch

# ---- CONFIG ----
POSTGRES_DSN = "dbname=codeseer user=codeseer password=codeseer host=localhost port=5432"
ES_HOST = "http://localhost:9200"
ES_INDEX = "files"

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

# ---- INDEX INTO ELASTICSEARCH ----
for file_id, path, language, size_bytes in rows:
    doc = {
        "path": path,
        "language": language,
        "size_bytes": size_bytes,
    }

    es.index(
        index=ES_INDEX,
        id=str(file_id),   # IMPORTANT: stable ID
        document=doc
    )

print("Indexing complete")

pg_cursor.close()
pg_conn.close()
