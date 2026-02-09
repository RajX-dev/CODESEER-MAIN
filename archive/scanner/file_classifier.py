EXT_MAP = {
    "source_code": {".py", ".js", ".ts", ".tsx", ".cpp", ".c", ".java", ".go"},
    "config": {".json", ".yml", ".yaml", ".env", ".toml"},
    "docs": {".md", ".rst", ".txt"},
    "tests": {"test", "spec"},
    "assets": {".png", ".jpg", ".svg", ".css"},
}

def classify(file):
    ext = file["extension"]
    name = file["path"].lower()

    for category, exts in EXT_MAP.items():
        if ext in exts:
            return category
        if category == "tests" and any(k in name for k in exts):
            return "tests"

    return "other"
