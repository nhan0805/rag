from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from shared.logger import logger


class BaseReranker(ABC):
    """Backend contract: score only; policy lives in ``apply_rerank``."""

    id: str = ""
    enabled: bool = False

    @abstractmethod
    def score(self, query: str, chunks: list[dict]) -> list[float]:
        """Return exactly one score per chunk, in input order."""
        raise NotImplementedError


def _vector_score(chunk: dict) -> float:
    value = chunk.get("vector_score", chunk.get("similarity", chunk.get("score", 0.0)))
    return float(value if value is not None else 0.0)


def apply_rerank(
    query: str,
    chunks: Sequence[dict],
    backend: BaseReranker,
    top_n: int,
    min_score: float | None = None,
) -> list[dict]:
    """Apply the shared rerank policy to any scoring backend.

    The input list is copied so the original vector candidate list remains
    available for observability and evaluation.
    """
    if top_n <= 0:
        raise ValueError("top_n must be positive")
    if not chunks:
        return []

    candidates = []
    for index, chunk in enumerate(chunks, start=1):
        item = dict(chunk)
        item["vector_rank"] = int(item.get("vector_rank") or index)
        # A lexical-only candidate has no cosine score. Preserve that null so
        # the API remains truthful while still using 0.0 as reranker fallback.
        if "vector_score" in item or "similarity" in item:
            item["vector_score"] = _vector_score(item)
        candidates.append(item)

    scores = backend.score(query, candidates)
    if len(scores) != len(candidates):
        raise ValueError(
            f"Reranker {backend.id!r} returned {len(scores)} scores for "
            f"{len(candidates)} chunks"
        )

    for item, score in zip(candidates, scores):
        item["rerank_score"] = float(score)

    ranked = candidates
    if min_score is not None:
        ranked = [item for item in ranked if item["rerank_score"] >= min_score]
        if not ranked:
            # Keep the best candidate instead of silently building an empty
            # prompt. This makes an overly strict threshold observable but safe.
            fallback = max(candidates, key=lambda item: item["rerank_score"])
            ranked = [fallback]
            logger.warning(
                "RERANK_MIN_SCORE=%s filtered every chunk; keeping vector_rank=%s",
                min_score,
                fallback["vector_rank"],
            )

    ranked.sort(key=lambda item: item["rerank_score"], reverse=True)
    return ranked[:top_n]
