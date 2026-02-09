def build_index(files, root):
    index = []
    for f in files:
        if f["extension"] in {".py", ".js", ".ts", ".tsx", ".md"}:
            try:
                with open(f"{root}/{f['path']}", encoding="utf-8", errors="ignore") as file:
                    content = file.read(500)
                index.append({
                    "path": f["path"],
                    "content": content.lower()
                })
            except:
                pass
    return index
