def detect_languages(files):
    langs = set()
    for f in files:
        if f["extension"] in {".ts", ".tsx"}:
            langs.add("typescript")
        if f["extension"] in {".js"}:
            langs.add("javascript")
        if f["extension"] == ".py":
            langs.add("python")
        if f["extension"] in {".cpp", ".h"}:
            langs.add("cpp")
    return list(langs)

def detect_repo_type(files):
    paths = [f["path"] for f in files]
    if any("frontend" in p or "src" in p for p in paths) and any("backend" in p for p in paths):
        return "fullstack"
    if any("src" in p for p in paths):
        return "frontend"
    if any("server" in p or "api" in p for p in paths):
        return "backend"
    return "library"
