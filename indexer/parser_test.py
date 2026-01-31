from symbol_extractor import extract_symbols
import json

def test_mapper():
    print("--- 1. LOADING CODE ---")
    
    # A complex example with Hierarchy
    code_to_parse = """
class Database:
    def connect(self):
        print("Connecting...")
        
    def disconnect(self):
        print("Bye.")

def main():
    db = Database()
    db.connect()
"""
    print(code_to_parse)

    print("\n--- 2. EXTRACTING SYMBOLS ---")
    # Pass raw bytes to our new extractor
    symbols = extract_symbols(bytes(code_to_parse, "utf8"), "test_file.py")

    print("\n--- 3. VERIFYING HIERARCHY ---")
    
    # Let's see the JSON output
    print(json.dumps(symbols, indent=2))
    
    # Verification Tests
    class_sym = next((s for s in symbols if s["name"] == "Database"), None)
    func_sym = next((s for s in symbols if s["name"] == "connect"), None)
    
    if not class_sym:
        print(" FAILED: Could not find 'Database' class.")
        return

    if not func_sym:
        print(" FAILED: Could not find 'connect' function.")
        return

    # THE BIG TEST: Does 'connect' know that 'Database' is its father?
    if func_sym["parent_id"] == class_sym["id"]:
        print("\n SUCCESS: The Child (connect) is correctly linked to the Parent (Database)!")
    else:
        print(f"\n FAILURE: Parent ID Mismatch. Expected {class_sym['id']}, got {func_sym['parent_id']}")

if __name__ == "__main__":
    test_mapper()