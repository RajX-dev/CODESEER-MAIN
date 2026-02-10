from symbol_extractor import extract_symbols_and_imports
import json

def test_imports():
    print("--- 1. PARSING IMPORTS ---")
    
    code = """
import os
import numpy as np
from utils import helper, Database
from ..libs import config
"""
    print(code)

    print("\n--- 2. EXTRACTING ---")
    symbols, imports = extract_symbols_and_imports(bytes(code, "utf8"), "test.py")

    print(json.dumps(imports, indent=2))
    
    # Verification
    helper_import = next((i for i in imports if i["name"] == "helper"), None)
    numpy_import = next((i for i in imports if i["module"] == "numpy"), None)

    if helper_import and helper_import["module"] == "utils":
        print("✅ Success: Found 'from utils import helper'")
    else:
        print("❌ Failed: 'helper' import not found correctly.")

    if numpy_import and numpy_import["alias"] == "np":
        print("✅ Success: Found 'import numpy as np'")
    else:
        print("❌ Failed: 'numpy' alias not found.")

if __name__ == "__main__":
    test_imports()