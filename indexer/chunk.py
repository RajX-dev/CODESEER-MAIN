from dataclasses import dataclass
from typing import Optional


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
    
