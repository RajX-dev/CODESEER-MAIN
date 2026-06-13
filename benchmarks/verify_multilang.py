import os
import shutil
import tempfile
import sys

# Reconfigure stdout to use utf-8 for Windows emoji support
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure project root is in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.run_indexer import main as run_indexer
from src.database import get_connection, release_connection

def create_multilang_project(dir_path):
    os.makedirs(dir_path, exist_ok=True)
    
    # 1. Python
    with open(os.path.join(dir_path, "prog.py"), "w", encoding="utf-8") as f:
        f.write("class PyClass:\n    def py_func(self):\n        other_func()\n")
        
    # 2. JavaScript
    with open(os.path.join(dir_path, "prog.js"), "w", encoding="utf-8") as f:
        f.write("class JSClass { jsMethod() { callJS(); } }\nfunction jsFunc() {}\n")
        
    # 3. TypeScript
    with open(os.path.join(dir_path, "prog.ts"), "w", encoding="utf-8") as f:
        f.write("class TSClass { tsMethod() { callTS(); } }\n")
        
    # 4. Go
    with open(os.path.join(dir_path, "prog.go"), "w", encoding="utf-8") as f:
        f.write("package main\nimport \"fmt\"\nfunc goFunc() { fmt.Println(); }\n")
        
    # 5. Rust
    with open(os.path.join(dir_path, "prog.rs"), "w", encoding="utf-8") as f:
        f.write("struct RustStruct;\nfn rust_func() { call_rust(); }\n")
        
    # 6. Java
    with open(os.path.join(dir_path, "prog.java"), "w", encoding="utf-8") as f:
        f.write("class JavaClass { void javaMethod() { callJava(); } }\n")
        
    # 7. C++
    with open(os.path.join(dir_path, "prog.cpp"), "w", encoding="utf-8") as f:
        f.write("#include \"header.h\"\nint cppFunc() { callCpp(); }\n")
        
    # 8. C
    with open(os.path.join(dir_path, "prog.c"), "w", encoding="utf-8") as f:
        f.write("int cFunc() { callC(); }\n")

def main():
    temp_dir = tempfile.mkdtemp()
    temp_dir_abs = os.path.abspath(temp_dir)
    print(f"📁 Created temporary multi-language project at: {temp_dir_abs}")
    
    try:
        create_multilang_project(temp_dir_abs)
        
        # Set environment variable for the indexer
        os.environ["TARGET_CODE_DIR"] = temp_dir_abs
        
        print("\n🚀 Running N3MO Indexer on the multi-language project...")
        run_indexer()
        
        # Connect to DB and check results
        print("\n🔍 Checking database counts...")
        conn = get_connection()
        try:
            with conn.cursor() as cur:
                # Get Project ID
                cur.execute("SELECT id FROM projects WHERE repo_url = %s", (temp_dir_abs,))
                row = cur.fetchone()
                if not row:
                    print("❌ Error: Project not found in database!")
                    return
                project_id = row[0]
                
                # Query symbols count
                cur.execute("SELECT file_path, name, kind FROM symbols WHERE project_id = %s ORDER BY file_path", (project_id,))
                symbols = cur.fetchall()
                print(f"\n📚 Extracted Symbols ({len(symbols)} total):")
                for file_path, name, kind in symbols:
                    print(f"   - [{file_path}] {kind}: {name}")
                    
                # Query calls count
                cur.execute("""
                    SELECT s.file_path, s.name, c.call_name 
                    FROM calls c 
                    JOIN symbols s ON c.source_symbol_id = s.id 
                    WHERE c.project_id = %s
                """, (project_id,))
                calls = cur.fetchall()
                print(f"\n📞 Extracted Call Expressions ({len(calls)} total):")
                for file_path, src_name, call_name in calls:
                    print(f"   - [{file_path}] inside '{src_name}' calls '{call_name}'")
                    
                # Query imports count
                cur.execute("SELECT file_path, module FROM imports WHERE project_id = %s", (project_id,))
                imports = cur.fetchall()
                print(f"\n🔗 Extracted Imports ({len(imports)} total):")
                for file_path, module in imports:
                    print(f"   - [{file_path}] imports '{module}'")
                    
        finally:
            release_connection(conn)
            
    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up {temp_dir_abs}...")
        if os.path.exists(temp_dir_abs):
            shutil.rmtree(temp_dir_abs)

if __name__ == "__main__":
    main()
