import os

IGNORED_DIRS = {".git", "node_modules", "dist", "build", "__pycache__"}

def scan_repo(root):
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        for f in filenames:
            full = os.path.join(dirpath, f)
            files.append({
                "path": os.path.relpath(full, root),
                "extension": os.path.splitext(f)[1],
                "size_kb": round(os.path.getsize(full) / 1024, 2)
            })
    return files
