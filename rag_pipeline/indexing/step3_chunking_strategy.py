from __future__ import annotations

import re
from typing import TypedDict

from config.env_config import settings


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


_QA_HEADING = re.compile(r"(?im)^##\s+Q\d+\s*:\s*.*$")


def _with_prefix(content: str, title: str | None, heading: str | None) -> str:
    prefix = [part.strip() for part in (title, heading) if part and part.strip()]
    return "\n\n".join([*prefix, content.strip()]).strip()


def qa_aware_chunks(
    text: str,
    chunk_size: int = 800,
    overlap: int = 120,
    title: str | None = None,
) -> list[Chunk]:
    """Keep Q&A answers together and repeat headings when a block is long."""
    headings = list(_QA_HEADING.finditer(text))
    if len(headings) < 2:
        return fixed_token_chunks(text, chunk_size, overlap)

    preamble = text[: headings[0].start()].strip()
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        heading = match.group(0).strip()
        body = text[match.end() : end].strip()
        if preamble:
            body = f"{preamble}\n\n{body}" if body else preamble
        blocks.append((heading, body))

    chunks: list[Chunk] = []
    for heading, body in blocks:
        base_prefix = _with_prefix("", title, heading)
        prefix_tokens = len(re.findall(r"\S+", base_prefix))
        available = max(chunk_size - prefix_tokens, 1)
        pieces = fixed_token_chunks(body, available, min(overlap, max(available - 1, 0)))
        if not pieces:
            pieces = [{"chunk_index": 0, "content": "", "token_count": 0}]
        for piece in pieces:
            content = _with_prefix(piece["content"], title, heading)
            chunks.append(
                {
                    "chunk_index": len(chunks),
                    "content": content,
                    "token_count": len(re.findall(r"\S+", content)),
                }
            )
    return chunks


def chunk_text(
    text: str,
    chunk_size: int | None = None,
    overlap: int | None = None,
    title: str | None = None,
    qa_aware: bool | None = None,
) -> list[Chunk]:
    """Select structural Q&A chunking only when the feature flag is enabled."""
    size = settings.chunk_size if chunk_size is None else chunk_size
    window_overlap = settings.chunk_overlap if overlap is None else overlap
    enabled = settings.qa_aware_chunking if qa_aware is None else qa_aware
    if enabled and len(_QA_HEADING.findall(text)) >= 2:
        return qa_aware_chunks(text, size, window_overlap, title)
    return fixed_token_chunks(text, size, window_overlap)
