from fastapi import FastAPI
import psycopg2
import psycopg2.extras
from elasticsearch import Elasticsearch
from config import DEBUG



app = FastAPI()
es = Elasticsearch("http://codeseer-es:9200")




DB_CONFIG = {
    "host": "postgres",
    "port": 5432,
    "dbname": "codeseer",
    "user": "codeseer",
    "password": "codeseer",
}


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/search")
def search_files(q: str):
    response = es.search(
        index="files",
        body={
            "query": {
                "match": {
                    "path": q
                }
            }
        }
    )

    results = [
        {
            "id": hit["_id"],
            "path": hit["_source"]["path"],
            "language": hit["_source"]["language"],
            "size_bytes": hit["_source"]["size_bytes"]
        }
        for hit in response["hits"]["hits"]
    ]

    return {
        "query": q,
        "count": len(results),
        "results": results
    }



@app.get("/files")
def get_files():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("SELECT * FROM files ORDER BY created_at DESC;")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows
