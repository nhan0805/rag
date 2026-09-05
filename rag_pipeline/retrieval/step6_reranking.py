from __future__ import annotations

from retrieval.rerank.base import BaseReranker, apply_rerank


def rerank(
    chunks: list[dict],
    question: str,
    backend: BaseReranker,
    top_n: int,
    min_score: float | None = None,
) -> list[dict]:
    """Apply the shared rerank policy; backend selection lives in the registry."""
    return apply_rerank(question, chunks, backend, top_n, min_score)
