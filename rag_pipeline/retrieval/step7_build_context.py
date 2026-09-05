from __future__ import annotations

from config.env_config import settings


def build_context(chunks: list[dict]) -> str:
    blocks: list[str] = []
    total = 0
    for chunk in chunks:
        block = (
            f"[SOURCE: {chunk['source_path']} | chunk {chunk['chunk_index']}]\n"
            f"{chunk['content']}"
        )
        if total + len(block) > settings.max_context_chars:
            break
        blocks.append(block)
        total += len(block) + 2
    return "\n\n".join(blocks)
