from __future__ import annotations

from indexing.step6_embedding_gen import embed_text


def embed_question(question: str) -> list[float]:
    return embed_text(question)

