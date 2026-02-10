from database import get_connection

def inspect():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            print("\n🔍 --- DEBUG: SYMBOLS (What we defined) ---")
            cur.execute("SELECT name, file_path FROM symbols ORDER BY name LIMIT 10")
            for name, path in cur.fetchall():
                print(f"   📦 {name:<30} (in {path})")

            print("\n🔍 --- DEBUG: CALLS (What we used) ---")
            cur.execute("SELECT call_name, resolved_symbol_id FROM calls LIMIT 10")
            for name, resolved in cur.fetchall():
                status = "✅ Linked" if resolved else "❌ Unlinked"
                print(f"   📞 {name:<30} {status}")

            print("\n-------------------------------------------")
    finally:
        conn.close()

if __name__ == "__main__":
    inspect()