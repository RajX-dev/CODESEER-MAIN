from indexer.chunk import chunk_python

with open("indexer/chunk.py", "r", encoding="utf-8") as f:
    content = f.read()

chunks = chunk_python("indexer/chunk.py", content)

print("Total chunks:", len(chunks))
for c in chunks:
    print(f"{c.chunk_type} {c.start_line}-{c.end_line}")
