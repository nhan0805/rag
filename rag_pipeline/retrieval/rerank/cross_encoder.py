from __future__ import annotations

from functools import lru_cache

from config.env_config import settings
from retrieval.rerank.base import BaseReranker


@lru_cache(maxsize=4)
def _get_ranker(model_name: str, cache_dir: str):
    try:
        from flashrank import Ranker
    except ImportError as exc:
        raise RuntimeError(
            "FlashRank chưa được cài; hãy build lại rag-app với requirements.txt"
        ) from exc
    return Ranker(model_name=model_name, cache_dir=cache_dir)


class CrossEncoderReranker(BaseReranker):
    id = "cross_encoder"
    enabled = True

    def __init__(self, model_name: str | None = None, cache_dir: str | None = None):
        self.model_name = model_name or settings.rerank_model
        self.cache_dir = cache_dir or settings.rerank_cache_dir

    def score(self, query: str, chunks: list[dict]) -> list[float]:
        if not chunks:
            return []
        from flashrank import RerankRequest

        ranker = _get_ranker(self.model_name, self.cache_dir)
        passages = [
            {"id": str(index), "text": chunk["content"]}
            for index, chunk in enumerate(chunks)
        ]
        results = ranker.rerank(RerankRequest(query=query, passages=passages))

        scores_by_id: dict[str, float] = {}
        scores_by_text: dict[str, float] = {}
        for result in results:
            score = result.get("score")
            if score is None:
                continue
            if result.get("id") is not None:
                scores_by_id[str(result["id"])] = float(score)
            if result.get("text") is not None:
                scores_by_text[str(result["text"])] = float(score)

        # FlashRank normally preserves ids. The text fallback keeps this
        # backend compatible with older versions that drop the id field.
        return [
            scores_by_id.get(
                str(index), scores_by_text.get(chunk["content"], 0.0)
            )
            for index, chunk in enumerate(chunks)
        ]

