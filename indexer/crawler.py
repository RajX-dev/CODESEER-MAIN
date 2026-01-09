import os
import uuid

# Folders we never want to scan
IGNORED_DIRS = {"node_modules", ".git", "dist", "build", "__pycache__"}


def detect_language(filename: str) -> str | None:
    if filename.endswith(".js"):
        return "javascript"
    if filename.endswith(".ts"):
        return "typescript"
    return None


def crawl_repo(repo_path: str):
    files = []

    for root, dirs, filenames in os.walk(repo_path):
        # Modify dirs in-place so os.walk skips them
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for filename in filenames:
            language = detect_language(filename)
            if not language:
                continue

            full_path = os.path.join(root, filename)

            try:
                size_bytes = os.path.getsize(full_path)
            except OSError:
                # Skip unreadable files
                continue

            files.append({
                "id": str(uuid.uuid4()),
                "path": full_path,
                "language": language,
                "size_bytes": size_bytes
            })

    return files


if __name__ == "__main__":
    repo_path = r"C:\Users\Raj shekhar\OneDrive\Documents\coding\DevType"

    result = crawl_repo(repo_path)

    print(f"Found {len(result)} code files")
    print("Sample:")
    for f in result[:5]:
        print(f)
