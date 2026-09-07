from __future__ import annotations

from collections.abc import Sequence

from config.env_config import settings
from guardrails.base import GuardVerdict


def check_retrieval(chunks: Sequence[dict]) -> GuardVerdict:
    """Reject an answer path with no usable evidence.

    RRF scores are not compared with vector scores.  If reranking is active,
    the calibrated reranker scale is the only optional score threshold used.
    """
    if not chunks:
        return GuardVerdict(
            allowed=False,
            stage="evidence",
            code="no_evidence",
            message="I could not find a relevant document to answer this question.",
        )

    rerank_scores = [
        float(chunk["rerank_score"])
        for chunk in chunks
        if chunk.get("rerank_score") is not None
    ]
    if rerank_scores and settings.guard_min_rerank_score is not None:
        best = max(rerank_scores)
        if best < settings.guard_min_rerank_score:
            return GuardVerdict(
                allowed=False,
                stage="evidence",
                code="weak_evidence",
                message="I am unable to answer this request.",
                detail={"best_rerank_score": best},
            )

    if not rerank_scores and settings.guard_min_vector_score is not None:
        vector_scores = [
            float(chunk.get("vector_score", chunk.get("similarity", 0.0)))
            for chunk in chunks
        ]
        best = max(vector_scores, default=0.0)
        if best < settings.guard_min_vector_score:
            return GuardVerdict(
                allowed=False,
                stage="evidence",
                code="weak_evidence",
                message="I am unable to answer this request.",
                detail={"best_vector_score": best},
            )

    return GuardVerdict(allowed=True, stage="evidence")
