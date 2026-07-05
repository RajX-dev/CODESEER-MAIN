# Copyright (C) 2026 Raj shekhar
#
# This file is part of N3MO.
# N3MO is licensed under the PolyForm Noncommercial License 1.0.0.
# You may obtain a copy of the License at
# https://polyformproject.org/licenses/noncommercial/1.0.0

import os
import sys
import shutil
import tempfile
import pytest

# Reconfigure stdout to use utf-8 for Windows emoji support
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
#testing
from n3mo.run_indexer import calculate_sha256, main as run_indexer
from n3mo.database import (
    get_connection,
    release_connection,
    get_file_hashes,
    ensure_project,
)

@pytest.fixture(scope="module")
def db_conn():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM information_schema.tables WHERE table_name = 'projects'")
            exists = cur.fetchone()
            if not exists:
                tests_dir = os.path.dirname(os.path.abspath(__file__))
                n3mo_root = os.path.dirname(tests_dir)
                schema_path = os.path.join(n3mo_root, "n3mo", "db", "schema.sql")
                if not os.path.exists(schema_path):
                    schema_path = os.path.join(n3mo_root, "db", "schema.sql")
                if os.path.exists(schema_path):
                    with open(schema_path, "r", encoding="utf-8") as f:
                        schema_sql = f.read()
                    cur.execute(schema_sql)
                    conn.commit()
    except Exception as e:
        print(f"Failed to initialize schema in test setup: {e}")
    yield conn
    release_connection(conn)

@pytest.fixture
def temp_repo():
    # Setup a temporary repository directory with some python files
    repo_dir = tempfile.mkdtemp()
    
    # Create file A
    file_a = os.path.join(repo_dir, "file_a.py")
    with open(file_a, "w", encoding="utf-8") as f:
        f.write("def func_a():\n    return 'A'\n")
        
    # Create file B
    file_b = os.path.join(repo_dir, "file_b.py")
    with open(file_b, "w", encoding="utf-8") as f:
        f.write("def func_b():\n    from file_a import func_a\n    return func_a() + 'B'\n")

    yield repo_dir
    
    if os.path.exists(repo_dir):
        shutil.rmtree(repo_dir)

def test_calculate_sha256(temp_repo):
    file_path = os.path.join(temp_repo, "file_a.py")
    h = calculate_sha256(file_path)
    assert len(h) == 64
    assert h.isalnum()

def test_database_hashing_queries(db_conn):
    # Ensure project exists
    project_id = ensure_project("test-hash-project", "http://test-url-project")
    
    # Clean previous records if any
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM files WHERE project_id = %s", (project_id,))
    db_conn.commit()

    from n3mo.database import upsert_file_hash, get_file_hashes, delete_file_index
    
    # Upsert hash
    upsert_file_hash(project_id, "file_a.py", "hash123")
    
    # Get hashes
    hashes = get_file_hashes(project_id)
    assert "file_a.py" in hashes
    assert hashes["file_a.py"] == "hash123"
    
    # Clean up
    delete_file_index(project_id, "file_a.py")
    hashes = get_file_hashes(project_id)
    assert "file_a.py" not in hashes

def test_incremental_indexing(temp_repo, db_conn):
    # Clear target database projects
    temp_repo_abs = os.path.abspath(temp_repo)
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM projects WHERE repo_url = %s", (temp_repo_abs,))
    db_conn.commit()
    
    # Set environment variable
    os.environ["TARGET_CODE_DIR"] = temp_repo_abs
    
    # Run 1: First indexing (full index)
    run_indexer()
    
    # Verify both files got indexed
    project_id = ensure_project(os.path.basename(temp_repo), temp_repo_abs)
    hashes = get_file_hashes(project_id)
    assert "file_a.py" in hashes
    assert "file_b.py" in hashes
    
    hash_a_1 = hashes["file_a.py"]
    hash_b_1 = hashes["file_b.py"]
    
    # Run 2: Second indexing with no changes (should skip all files)
    run_indexer()
    
    # Run 3: Modify file A
    file_a = os.path.join(temp_repo, "file_a.py")
    with open(file_a, "a", encoding="utf-8") as f:
        f.write("\ndef func_new():\n    return 'new'\n")
        
    run_indexer()
    
    # Verify hash for file A updated, but file B remained the same
    hashes_run3 = get_file_hashes(project_id)
    assert hashes_run3["file_a.py"] != hash_a_1
    assert hashes_run3["file_b.py"] == hash_b_1
    
    # Run 4: Delete file B
    file_b = os.path.join(temp_repo, "file_b.py")
    os.remove(file_b)
    
    run_indexer()
    
    # Verify file B was pruned from the index database
    hashes_run4 = get_file_hashes(project_id)
    assert "file_a.py" in hashes_run4
    assert "file_b.py" not in hashes_run4

def test_multilanguage_parsing(temp_repo):
    from n3mo.symbol_extractor import extract_symbols
    
    # 1. Test JS Parsing
    js_file = os.path.join(temp_repo, "index.js")
    with open(js_file, "w", encoding="utf-8") as f:
        f.write("""
        class MyClass {
            constructor() {}
            myMethod() {
                otherFunc();
            }
        }
        function standardFunc() {}
        const arrowFunc = () => {};
        import { dep } from "library";
        """)
    
    symbols, imports, calls = extract_symbols(js_file)
    symbol_names = [s["name"] for s in symbols]
    assert "MyClass" in symbol_names
    assert "myMethod" in symbol_names
    assert "standardFunc" in symbol_names
    assert "arrowFunc" in symbol_names
    
    # Verify imports
    import_modules = [i["module"] for i in imports]
    assert "library" in import_modules
    
    # Verify calls
    call_names = [c["call_name"] for c in calls]
    assert "otherFunc" in call_names

    # 2. Test Go Parsing
    go_file = os.path.join(temp_repo, "main.go")
    with open(go_file, "w", encoding="utf-8") as f:
        f.write("""
        package main
        import "fmt"
        func myGoFunc() {
            fmt.Println("hello");
        }
        """)
        
    symbols, imports, calls = extract_symbols(go_file)
    symbol_names = [s["name"] for s in symbols]
    assert "myGoFunc" in symbol_names
    assert "fmt" in [i["module"] for i in imports]

    # 3. Test Rust Parsing
    rs_file = os.path.join(temp_repo, "lib.rs")
    with open(rs_file, "w", encoding="utf-8") as f:
        f.write("""
        use std::collections::HashMap;
        struct MyStruct {}
        fn rust_func() {
            another_func();
        }
        """)
        
    symbols, imports, calls = extract_symbols(rs_file)
    symbol_names = [s["name"] for s in symbols]
    assert "rust_func" in symbol_names
    assert "MyStruct" in symbol_names
    assert "std::collections::HashMap" in [i["module"] for i in imports]
    assert "another_func" in [c["call_name"] for c in calls]

    # 4. Test Java Parsing
    java_file = os.path.join(temp_repo, "App.java")
    with open(java_file, "w", encoding="utf-8") as f:
        f.write("""
        import java.util.List;
        class App {
            void run() {
                doSomething();
            }
        }
        """)
        
    symbols, imports, calls = extract_symbols(java_file)
    symbol_names = [s["name"] for s in symbols]
    assert "App" in symbol_names
    assert "run" in symbol_names
    assert "java.util.List" in [i["module"] for i in imports]
    assert "doSomething" in [c["call_name"] for c in calls]

    # 5. Test C++ Parsing
    cpp_file = os.path.join(temp_repo, "main.cpp")
    with open(cpp_file, "w", encoding="utf-8") as f:
        f.write("""
        #include "helper.h"
        class CppClass {};
        int cpp_func() {
            call_helper();
        }
        """)
        
    symbols, imports, calls = extract_symbols(cpp_file)
    symbol_names = [s["name"] for s in symbols]
    assert "cpp_func" in symbol_names
    assert "CppClass" in symbol_names
    assert "helper.h" in [i["module"] for i in imports]
    assert "call_helper" in [c["call_name"] for c in calls]

def test_crawler_exclusions(temp_repo):
    from n3mo.crawler import is_test_or_mock_file, crawl_repo
    
    # Assert on some filename patterns
    assert is_test_or_mock_file("test_helper.py")
    assert is_test_or_mock_file("mock_service.ts")
    assert is_test_or_mock_file("service.test.js")
    assert is_test_or_mock_file("user_spec.rb")
    assert is_test_or_mock_file("test.t")  # Perl .t files
    assert is_test_or_mock_file("utils_unittest.go")
    assert is_test_or_mock_file("fixture.java")
    assert is_test_or_mock_file("mocks.py")
    
    # Negative cases
    assert not is_test_or_mock_file("contest.py")
    assert not is_test_or_mock_file("mockingbird.py")
    assert not is_test_or_mock_file("special.py")
    assert not is_test_or_mock_file("main.py")
    
    # Now create folders and check crawl_repo
    test_dir = os.path.join(temp_repo, "tests")
    os.makedirs(test_dir, exist_ok=True)
    with open(os.path.join(test_dir, "valid.py"), "w", encoding="utf-8") as f:
        f.write("def dummy(): pass\n")
        
    mock_dir = os.path.join(temp_repo, "src", "mocks")
    os.makedirs(mock_dir, exist_ok=True)
    with open(os.path.join(mock_dir, "helper.py"), "w", encoding="utf-8") as f:
        f.write("def dummy(): pass\n")
        
    valid_dir = os.path.join(temp_repo, "src", "controllers")
    os.makedirs(valid_dir, exist_ok=True)
    valid_file = os.path.join(valid_dir, "user.py")
    with open(valid_file, "w", encoding="utf-8") as f:
        f.write("def create_user(): pass\n")
        
    # Also create a test file in the valid dir
    test_file_in_valid_dir = os.path.join(valid_dir, "user_test.py")
    with open(test_file_in_valid_dir, "w", encoding="utf-8") as f:
        f.write("def test_create(): pass\n")

    files = crawl_repo(temp_repo)
    # Convert absolute paths to relative paths for easy assertion
    rel_files = [os.path.relpath(f, temp_repo) for f in files]
    
    # We should only find the non-test file 'src/controllers/user.py'
    # 'tests/valid.py' is in an ignored directory
    # 'src/mocks/helper.py' is in an ignored directory
    # 'src/controllers/user_test.py' is a test file
    assert "src/controllers/user.py" in [r.replace("\\", "/") for r in rel_files]
    assert len(files) == 3
    
    # Verify the excluded files are not crawled
    norm_rel_files = [r.replace("\\", "/") for r in rel_files]
    assert "tests/valid.py" not in norm_rel_files
    assert "src/mocks/helper.py" not in norm_rel_files
    assert "src/controllers/user_test.py" not in norm_rel_files

def test_no_impact_file_exclusions(temp_repo, db_conn):
    temp_repo_abs = os.path.abspath(temp_repo)
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM projects WHERE repo_url = %s", (temp_repo_abs,))
    db_conn.commit()
    
    # Set env var
    os.environ["TARGET_CODE_DIR"] = temp_repo_abs
    
    # Create two files:
    # 1. An impactful Python file
    # 2. A no-impact Python file (e.g. empty or only comments, which has 0 symbols/imports/calls)
    file_impact = os.path.join(temp_repo, "impact.py")
    with open(file_impact, "w", encoding="utf-8") as f:
        f.write("def work():\n    pass\n")
        
    file_no_impact = os.path.join(temp_repo, "no_impact.py")
    with open(file_no_impact, "w", encoding="utf-8") as f:
        f.write("# Just a comment\n# Another comment\n")
        
    # Run indexer
    run_indexer()
    
    project_id = ensure_project(os.path.basename(temp_repo), temp_repo_abs)
    hashes = get_file_hashes(project_id)
    
    # Check that impact.py is in hashes, but no_impact.py is NOT (since it was skipped as no-impact)
    assert "impact.py" in hashes
    assert "no_impact.py" not in hashes
    
    # Verify that the DB has no records for no_impact.py
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM symbols WHERE project_id = %s AND file_path = 'no_impact.py'", (project_id,))
        assert cur.fetchone()[0] == 0
        
    # Now, let's turn impact.py into a no-impact file (blank it out)
    with open(file_impact, "w", encoding="utf-8") as f:
        f.write("\n\n")
        
    # Re-run indexer
    run_indexer()
    
    hashes_after = get_file_hashes(project_id)
    # Now impact.py should be deleted/pruned from hashes too!
    assert "impact.py" not in hashes_after
    
    # And no records in symbols for it
    with db_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM symbols WHERE project_id = %s AND file_path = 'impact.py'", (project_id,))
        assert cur.fetchone()[0] == 0


def test_cte_cycle_guard(temp_repo, db_conn):
    # Verify cyclic dependencies are safely tracked and do not loop infinitely
    project_id = ensure_project("test-cycle-proj", temp_repo)
    
    import uuid
    id_a = str(uuid.uuid4())
    id_b = str(uuid.uuid4())
    
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM symbols WHERE project_id = %s", (project_id,))
        cur.execute("DELETE FROM calls WHERE project_id = %s", (project_id,))
        
        cur.execute(
            "INSERT INTO symbols (id, project_id, name, file_path, kind, start_line) VALUES (%s, %s, %s, %s, %s, %s)",
            (id_a, project_id, "func_a", "file_a.py", "FUNCTION", 1)
        )
        cur.execute(
            "INSERT INTO symbols (id, project_id, name, file_path, kind, start_line) VALUES (%s, %s, %s, %s, %s, %s)",
            (id_b, project_id, "func_b", "file_b.py", "FUNCTION", 1)
        )
        
        cur.execute(
            "INSERT INTO calls (id, project_id, source_symbol_id, call_name, line_number, resolved_symbol_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), project_id, id_a, "func_b", 2, id_b)
        )
        cur.execute(
            "INSERT INTO calls (id, project_id, source_symbol_id, call_name, line_number, resolved_symbol_id) VALUES (%s, %s, %s, %s, %s, %s)",
            (str(uuid.uuid4()), project_id, id_b, "func_a", 2, id_a)
        )
        db_conn.commit()
        
    with db_conn.cursor() as cur:
        query = """
        WITH RECURSIVE impact_chain AS (
            SELECT s.name AS source, s.file_path, c.line_number, 1 AS depth, target_sym.name AS target, c.source_symbol_id AS source_id,
                   ARRAY[c.source_symbol_id] AS path,
                   FALSE AS cycle
            FROM calls c
            JOIN symbols s ON c.source_symbol_id = s.id
            JOIN symbols target_sym ON c.resolved_symbol_id = target_sym.id
            WHERE c.resolved_symbol_id = %s
            UNION ALL
            SELECT s.name, s.file_path, c.line_number, ic.depth + 1, ic.source, c.source_symbol_id,
                   ic.path || c.source_symbol_id,
                   c.source_symbol_id = ANY(ic.path)
            FROM impact_chain ic
            JOIN calls c ON c.resolved_symbol_id = ic.source_id
            JOIN symbols s ON c.source_symbol_id = s.id
            WHERE ic.depth < 5 AND NOT ic.cycle
        )
        SELECT DISTINCT source, file_path, line_number, depth, target
        FROM impact_chain WHERE NOT cycle ORDER BY depth ASC, file_path;
        """
        cur.execute(query, (id_a,))
        results = cur.fetchall()
        
        assert len(results) >= 1


def test_scope_aware_call_resolution(temp_repo, db_conn):
    # Verify that calls to imported functions resolve to the correct target files
    os.makedirs(os.path.join(temp_repo, "src"), exist_ok=True)
    
    file_a = os.path.join(temp_repo, "src", "utils_a.py")
    with open(file_a, "w", encoding="utf-8") as f:
        f.write("def hello():\n    pass\n")
        
    file_b = os.path.join(temp_repo, "src", "utils_b.py")
    with open(file_b, "w", encoding="utf-8") as f:
        f.write("def hello():\n    pass\n")
        
    file_main = os.path.join(temp_repo, "src", "main.py")
    with open(file_main, "w", encoding="utf-8") as f:
        f.write("from utils_a import hello\n\ndef run():\n    hello()\n")
        
    temp_repo_abs = os.path.abspath(temp_repo)
    os.environ["TARGET_CODE_DIR"] = temp_repo_abs
    
    with db_conn.cursor() as cur:
        cur.execute("DELETE FROM projects WHERE repo_url = %s", (temp_repo_abs,))
    db_conn.commit()
    
    run_indexer()
    
    project_id = ensure_project(os.path.basename(temp_repo), temp_repo_abs)
    
    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.resolved_symbol_id, s.file_path, s.name 
            FROM calls c 
            JOIN symbols s ON c.resolved_symbol_id = s.id 
            WHERE c.project_id = %s AND c.call_name = 'hello'
            """,
            (project_id,)
        )
        row = cur.fetchone()
        assert row is not None
        resolved_file = row[1].replace("\\", "/")
        assert "utils_a.py" in resolved_file
        assert "utils_b.py" not in resolved_file


def test_api_server_endpoints():
    from n3mo.api_server import health
    res = health()
    assert res == {"status": "healthy", "service": "n3mo-api"}

