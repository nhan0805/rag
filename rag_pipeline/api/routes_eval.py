from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.deps import CurrentUser, get_current_user
from retrieval.retrieval_runner import answer_question


router = APIRouter(prefix="/eval", tags=["evaluation"])


class EvalItem(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    expected_sources: list[str] = Field(default_factory=list)


class EvalRequest(BaseModel):
    items: list[EvalItem] = Field(min_length=1, max_length=100)
    rerank: bool = False
    hybrid: bool = False


@router.post("/run")
def run_eval(
    request: EvalRequest,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, object]:
    results: list[dict[str, object]] = []
    reciprocal_ranks: list[float] = []
    recall_hits = 0
    started = time.perf_counter()
    for item in request.items:
        try:
            payload = answer_question(
                item.question,
                rerank=request.rerank,
                hybrid=request.hybrid,
                retrieve_only=True,
                allowed_classification_ids=list(user.classification_ids),
                user_id=user.user_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Evaluation thất bại: {exc}") from exc
        sources = [source.get("source", "") for source in payload.get("sources", [])]
        retrieved = [
            source.get("source", "") for source in payload.get("retrieved_sources", [])
        ]
        expected = set(item.expected_sources)
        recall_hits += int(bool(expected.intersection(retrieved))) if expected else 0
        rank = next((index for index, source in enumerate(sources, 1) if source in expected), None)
        reciprocal_ranks.append(1 / rank if rank else 0.0)
        results.append(
            {
                "question": item.question,
                "sources": sources,
                "retrieved_sources": retrieved,
                "blocked": payload.get("blocked", False),
            }
        )
    real_count = sum(bool(item.expected_sources) for item in request.items)
    return {
        "count": len(results),
        "recall": recall_hits / real_count if real_count else 0.0,
        "mrr": sum(reciprocal_ranks) / len(reciprocal_ranks) if reciprocal_ranks else 0.0,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        "results": results,
    }
