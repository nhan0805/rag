from __future__ import annotations

import re
from typing import TypedDict


class Chunk(TypedDict):
    chunk_index: int
    content: str
    token_count: int


def fixed_token_chunks(text: str, chunk_size: int = 800, overlap: int = 120) -> list[Chunk]:
    """Split text into overlapping whitespace-token windows.

    The lab calls this fixed-token chunking. Whitespace tokens keep the
    implementation dependency-free and make the overlap behavior explicit.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")

    tokens = re.findall(r"\S+", text)
    if not tokens:
        return []

    step = chunk_size - overlap
    chunks: list[Chunk] = []
    for index, start in enumerate(range(0, len(tokens), step)):
        window = tokens[start : start + chunk_size]
        if not window:
            break
        chunks.append(
            {
                "chunk_index": index,
                "content": " ".join(window),
                "token_count": len(window),
            }
        )
        if start + chunk_size >= len(tokens):
            break
    return chunks

