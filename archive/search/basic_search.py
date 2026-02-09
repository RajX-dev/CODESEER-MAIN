def search(query, index):
    q = query.lower()
    results = []

    for item in index:
        if q in item["path"].lower():
            results.append({
                "file": item["path"],
                "reason": "filename match"
            })
        elif q in item["content"]:
            results.append({
                "file": item["path"],
                "reason": "content match"
            })

    return results
