import sys
import json

from scanner.repo_scan import scan_repo
from scanner.file_classifier import classify
from scanner.language_detector import detect_languages, detect_repo_type
from search.index_builder import build_index
from search.basic_search import search


def scan_command(repo_path):
    files = scan_repo(repo_path)

    for f in files:
        f["category"] = classify(f)

    summary = {
        "languages": detect_languages(files),
        "repo_type": detect_repo_type(files),
        "total_files": len(files),
        "by_category": {}
    }

    for f in files:
        c = f["category"]
        summary["by_category"][c] = summary["by_category"].get(c, 0) + 1

    print(json.dumps(summary, indent=2))


def search_command(repo_path, query):
    files = scan_repo(repo_path)
    index = build_index(files, repo_path)
    results = search(query, index)
    print(json.dumps(results, indent=2))


def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python codeseer.py scan <repo_path>")
        print("  python codeseer.py search <repo_path> \"query\"")
        return

    command = sys.argv[1]

    if command == "scan":
        scan_command(sys.argv[2])
    elif command == "search" and len(sys.argv) >= 4:
        search_command(sys.argv[2], sys.argv[3])
    else:
        print("Invalid command")


if __name__ == "__main__":
    main()
