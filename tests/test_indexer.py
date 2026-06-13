import os
import sys
import shutil
import tempfile
import pytest
import psycopg2

# Reconfigure stdout to use utf-8 for Windows emoji support
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
#testing
from src.run_indexer import calculate_sha256, main as run_indexer
from src.database import (
    get_connection,
    release_connection,
    get_file_hashes,
    ensure_project,
)

@pytest.fixture(scope="module")
def db_conn():
    conn = get_connection()
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

    from src.database import upsert_file_hash, get_file_hashes, delete_file_index
    
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
