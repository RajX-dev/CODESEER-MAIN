import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate():
    dsn = os.getenv("N3MO_DATABASE_URL")
    if not dsn:
        print("No N3MO_DATABASE_URL found.")
        return
        
    try:
        conn = psycopg2.connect(dsn)
        with conn.cursor() as cur:
            with open("n3mo/db/schema.sql", "r") as f:
                cur.execute(f.read())
            with open("n3mo/db/saas_schema.sql", "r") as f:
                cur.execute(f.read())
            
            # Make the first user an admin for testing if one exists
            cur.execute("UPDATE users SET is_admin = TRUE WHERE username = 'RajX-dev'")
            
            conn.commit()
            print("Migration successful.")
    except Exception as e:
        print(f"Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()

if __name__ == "__main__":
    migrate()
