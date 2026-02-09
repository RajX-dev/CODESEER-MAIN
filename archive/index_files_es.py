import time
import psycopg2
from elasticsearch import Elasticsearch

import os

DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "dbname": os.getenv("POSTGRES_DB"),
    "user": os.getenv("POSTGRES_USER"),
    "password": os.getenv("POSTGRES_PASSWORD"),
}

ES_HOST = os.getenv("ELASTICSEARCH_HOST")
ES_INDEX = "files"

def wait_for_elasticsearch(es, retries=60, delay=2):
    for i in range(retries):
        try:
            info = es.info()
            version = info["version"]["number"]
            print(f"Elasticsearch ready (version {version})")
            return
        except Exception:
            print(f"Waiting for Elasticsearch HTTP... ({i+1}/{retries})")
            time.sleep(delay)

    raise RuntimeError("Elasticsearch not reachable after waiting")


def fetch_files_from_db():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, path, language, size_bytes
        FROM files;
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def ensure_index(es):
    if es.indices.exists(index=ES_INDEX):
        print("Elasticsearch index already exists")
        return

    es.indices.create(
        index=ES_INDEX,
        mappings={
            "properties": {
                "path": {"type": "text"},
                "language": {"type": "keyword"},
                "size_bytes": {"type": "integer"},
            }
        },
    )
    print("Elasticsearch index created")


def index_files():
    es = Elasticsearch(
        ES_HOST,
        request_timeout=30,
        retry_on_timeout=True,
        max_retries=5,
    )

    wait_for_elasticsearch(es)
    ensure_index(es)

    rows = fetch_files_from_db()

    for file_id, path, language, size_bytes in rows:
        es.index(
            index=ES_INDEX,
            id=file_id,
            document={
                "path": path,
                "language": language,
                "size_bytes": size_bytes,
            },
        )

    print(f"Indexed {len(rows)} files into Elasticsearch")


if __name__ == "__main__":
    index_files()
