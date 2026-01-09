import psycopg2
from crawler import crawl_repo

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "codeseer",
    "user": "codeseer",
    "password": "codeseer"
}

REPO_PATH = r"C:\Users\Raj shekhar\OneDrive\Documents\coding\DevType"


def insert_files(files):
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    query = """
        INSERT INTO files (id, path, language, size_bytes)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING;
    """

    for f in files:
        cur.execute(query, (
            f["id"],
            f["path"],
            f["language"],
            f["size_bytes"]
        ))

    conn.commit()
    cur.close()
    conn.close()


if __name__ == "__main__":
    files = crawl_repo(REPO_PATH)
    insert_files(files)
    print(f"Inserted {len(files)} files into database")
