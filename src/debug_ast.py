import os
from symbol_extractor import extract_symbols

def test_extraction():
    # We analyze the symbol_extractor.py file itself!
    target_file = "src/symbol_extractor.py"
    
    if not os.path.exists(target_file):
        print(f"❌ File not found: {target_file}")
        return

    print(f"🧠 analyzing {target_file}...")
    symbols, imports, calls = extract_symbols(target_file)

    print(f"\n📊 Found {len(calls)} calls:")
    found_visit = False
    
    for c in calls:
        name = c['call_name']
        line = c['line_number']
        # Check if we found the missing function
        if "_visit_imports" in name:
            found_visit = True
            print(f"   ✅ FOUND: {name} (Line {line})")
        else:
            # Print first 5 others just to prove it works
            if line < 20: 
                print(f"   📞 {name} (Line {line})")

    if not found_visit:
        print("\n❌ CRITICAL: The extractor completely MISSED '_visit_imports'!")
        print("   This means the bug is inside 'symbol_extractor.py' logic.")
    else:
        print("\n✅ The extractor SEES it. The bug is in the Database/Indexer.")

if __name__ == "__main__":
    test_extraction()