import os
import uuid

# Folders we never want to scan
IGNORED_DIRS = {
    "node_modules", ".git", "dist", "build", "__pycache__", 
    ".venv", "venv", "env", ".idea", ".vscode"
}

def detect_language(filename: str) -> str | None:
    # --- ADDED: Python Support ---
    if filename.endswith(".py"):
        return "python"
    # -----------------------------
    if filename.endswith(".js"):
        return "javascript"
    if filename.endswith(".ts"):
        return "typescript"
    return None

def crawl_repo(repo_path: str):
    """
    Scans the repo and returns a list of file paths.
    """
    files = []

    for root, dirs, filenames in os.walk(repo_path):
        # Modify dirs in-place so os.walk skips them
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for filename in filenames:
            language = detect_language(filename)
            if not language:
                continue

            full_path = os.path.join(root, filename)
            
            # For the N3MO CLI, we just need the path string right now.
            # But we can keep the dictionary logic commented out if you prefer that format later.
            files.append(full_path) 
            
            # --- OLD DICTIONARY FORMAT (Preserved but commented) ---
            # try:
            #     size_bytes = os.path.getsize(full_path)
            # except OSError:
            #     continue
            # files.append({
            #     "id": str(uuid.uuid4()),
            #     "path": full_path,
            #     "language": language,
            #     "size_bytes": size_bytes
            # })
            # -------------------------------------------------------

    return files

# Wrapper function to match what run_indexer.py expects
def crawl_directory(repo_path):
    return crawl_repo(repo_path)

if __name__ == "__main__":
    # Test it locally
    repo_path = os.getcwd()
    result = crawl_repo(repo_path)
    print(f"Found {len(result)} code files")
    for f in result[:5]:
        print(f)