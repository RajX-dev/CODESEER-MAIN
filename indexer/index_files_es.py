import psycopg2
from elasticsearch import Elasticsearch

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "codeseer",
    "user": "codeseer",
    "password": "codeseer"
}

ES_HOST = "http://localhost:9200"
ES_INDEX = "files"


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
    try:
        es.indices.create(
            index=ES_INDEX,
            body={
                "mappings": {
                    "properties": {
                        "path": {"type": "text"},
                        "language": {"type": "keyword"},
                        "size_bytes": {"type": "integer"}
                    }
                }
            }
        )
        print("Elasticsearch index created")
    except Exception as e:
        # Index already exists → ignore
        if "resource_already_exists_exception" in str(e):
            print("Elasticsearch index already exists")
        else:
            raise




def index_files():
    es = Elasticsearch(ES_HOST)
    ensure_index(es)

    rows = fetch_files_from_db()

    for row in rows:
        file_id, path, language, size_bytes = row

        es.index(
            index=ES_INDEX,
            id=file_id,
            document={
                "path": path,
                "language": language,
                "size_bytes": size_bytes
            }
        )

    print(f"Indexed {len(rows)} files into Elasticsearch")


if __name__ == "__main__":
    index_files()
