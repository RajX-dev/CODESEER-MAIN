from indexer.chunk import chunk_config

def main():
    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        content = f.read()

    chunks = chunk_config("docker-compose.yml", content)

    print("Total chunks:", len(chunks))
    for c in chunks:
        print(f"{c.start_line}-{c.end_line}")

if __name__ == "__main__":
    main()
