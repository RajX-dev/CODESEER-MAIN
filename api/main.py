from fastapi import FastAPI
import psycopg2
import psycopg2.extras

app = FastAPI()

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


@app.get("/files")
def get_files():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("SELECT * FROM files ORDER BY created_at DESC;")
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows
