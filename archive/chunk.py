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


def chunk_docs(file_path: str, content: str) -> List[Chunk]:
    """
    Chunk documentation files by markdown-style section headers.
    """
    chunks: List[Chunk] = []
    lines = content.splitlines()

    current = []
    start_line = 0

    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            if current:
                chunk_id = _stable_chunk_id(file_path, start_line, "doc")
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        file_path=file_path,
                        language=None,
                        chunk_type="doc",
                        start_line=start_line + 1,
                        end_line=i,
                        content="\n".join(current).strip()
                    )
                )
                current = []

            start_line = i

        current.append(line)

    if current:
        chunk_id = _stable_chunk_id(file_path, start_line, "doc")
        chunks.append(
            Chunk(
                id=chunk_id,
                file_path=file_path,
                language=None,
                chunk_type="doc",
                start_line=start_line + 1,
                end_line=len(lines),
                content="\n".join(current).strip()
            )
        )

    return chunks


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


def chunk_python(file_path: str, content: str) -> List[Chunk]:
    """
    Chunk Python source files by top-level class and function definitions.
    """
    chunks: List[Chunk] = []
    lines = content.splitlines()

    current = []
    start_line = None
    chunk_type = None

    for i, line in enumerate(lines):
        stripped = line.lstrip()
        is_top_level = not line.startswith((" ", "\t"))

        if is_top_level and (stripped.startswith("def ") or stripped.startswith("class ")):
            if current and start_line is not None:
                chunk_id = _stable_chunk_id(file_path, start_line, chunk_type)
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        file_path=file_path,
                        language="python",
                        chunk_type=chunk_type,
                        start_line=start_line + 1,
                        end_line=i,
                        content="\n".join(current).strip()
                    )
                )
                current = []

            start_line = i
            chunk_type = "class" if stripped.startswith("class ") else "function"

        if start_line is not None:
            current.append(line)

    if current and start_line is not None:
        chunk_id = _stable_chunk_id(file_path, start_line, chunk_type)
        chunks.append(
            Chunk(
                id=chunk_id,
                file_path=file_path,
                language="python",
                chunk_type=chunk_type,
                start_line=start_line + 1,
                end_line=len(lines),
                content="\n".join(current).strip()
            )
        )

    return chunks
