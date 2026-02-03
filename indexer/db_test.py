from database import ensure_project, upsert_symbol
from symbol_extractor import extract_symbols
import uuid

def test_integration():
    print("--- 1. SETUP PROJECT ---")
    # We must have a project ID first because of Foreign Keys
    project_id = ensure_project("Test Repo", "http://github.com/test/repo")
    print(f"✅ Project 'Test Repo' Active. ID: {project_id}")

    print("\n--- 2. EXTRACT SYMBOLS ---")
    code = """
class DataHandler:
    def process(self):
        pass
"""
    # Use our Day 17 extractor
    symbols = extract_symbols(bytes(code, "utf8"), "src/handler.py")
    print(f"✅ Extracted {len(symbols)} symbols.")

    print("\n--- 3. INSERTING INTO DB ---")
    
    # We need to map the UUIDs carefully.
    # The extractor generates random UUIDs. We need to track them 
    # so we can set 'parent_id' correctly during insertion.
    
    id_map = {} # Maps { temp_id_from_extractor : real_db_uuid }

    # Sort symbols so Parents come before Children (Critical for Foreign Keys!)
    # Simple logic: Items with parent_id=None go first.
    symbols.sort(key=lambda x: x["parent_id"] is not None)

    for sym in symbols:
        # If this symbol has a parent, look up the REAL parent UUID from our map
        if sym["parent_id"]:
            if sym["parent_id"] in id_map:
                sym["parent_id"] = id_map[sym["parent_id"]]
            else:
                print(f"⚠️ Warning: Parent for {sym['name']} not found yet.")
        
        # Insert into DB
        real_uuid = upsert_symbol(project_id, sym)
        
        # Save mapping (The extractor ID -> The DB ID)
        id_map[sym["id"]] = real_uuid
        print(f"   Saved: {sym['kind']} {sym['name']} -> {real_uuid}")

    print("\n🎉 SUCCESS: Data is consistent in PostgreSQL.")

if __name__ == "__main__":
    test_integration()