from __future__ import annotations

from functools import lru_cache

from config.env_config import settings
from retrieval.rerank.base import BaseReranker, apply_rerank


@lru_cache(maxsize=4)
def get_reranker(backend: str | None = None) -> BaseReranker | None:
    selected = (backend or settings.rerank_backend).strip().lower()
    if selected == "none":
        return None
    if selected == "cross_encoder":
        from retrieval.rerank.cross_encoder import CrossEncoderReranker

        return CrossEncoderReranker()
    if selected == "llm":
        from retrieval.rerank.llm_reranker import LLMReranker

        return LLMReranker()
    raise ValueError(
        f"RERANK_BACKEND không hợp lệ: {selected!r}; "
        "chọn cross_encoder, llm hoặc none"
    )


__all__ = ["BaseReranker", "apply_rerank", "get_reranker"]

