from dataclasses import dataclass
from typing import List, Optional
import hashlib


@dataclass
class Chunk:
    """
    Represents a semantic unit of a repository (e.g., function, class, doc section).
    Used later for vectorization and advanced search.
    """
    id: str
    file_path: str
    language: Optional[str]
    chunk_type: str       # e.g., "function", "class", "doc", "config"
    start_line: int
    end_line: int
    content: str
    



def _stable_chunk_id(file_path: str, start_line: int, chunk_type: str) -> str:
    raw = f"{file_path}:{start_line}:{chunk_type}"
    return hashlib.sha1(raw.encode()).hexdigest()


def chunk_config(file_path: str, content: str) -> List[Chunk]:
    """
    Chunk config files by blank-line–separated blocks.
    Works for YAML, ENV, and simple config formats.
    """
    chunks: List[Chunk] = []
    lines = content.splitlines()

    current = []
    start_line = 0

    for i, line in enumerate(lines):
        if line.strip() == "":
            if current:
                chunk_id = _stable_chunk_id(file_path, start_line, "config")
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        file_path=file_path,
                        language=None,
                        chunk_type="config",
                        start_line=start_line + 1,
                        end_line=i,
                        content="\n".join(current).strip()
                    )
                )
                current = []
            start_line = i + 1
        else:
            current.append(line)

    if current:
        chunk_id = _stable_chunk_id(file_path, start_line, "config")
        chunks.append(
            Chunk(
                id=chunk_id,
                file_path=file_path,
                language=None,
                chunk_type="config",
                start_line=start_line + 1,
                end_line=len(lines),
                content="\n".join(current).strip()
            )
        )

    return chunks
