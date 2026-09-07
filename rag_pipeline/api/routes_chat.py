from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from retrieval.cache.store import purge
from retrieval.retrieval_runner import answer_question


router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    rerank: bool | None = None
    hybrid: bool | None = None
    retrieve_only: bool = False
    show_sources: bool = True
    conversation_id: str | None = Field(default=None, max_length=200)
    user_id: str = Field(default="anonymous", min_length=1, max_length=200)
    allowed_classification_ids: list[str] = Field(default_factory=list)


class Source(BaseModel):
    n: int
    source: str
    document_id: str | None = None
    chunk_index: int
    score: float | None = None
    vector_score: float | None = None
    vector_rank: int | None = None
    lexical_score: float | None = None
    lexical_rank: int | None = None
    rrf_score: float | None = None
    rrf_rank: int | None = None
    found_by: list[str] = Field(default_factory=list)
    rerank_score: float | None = None
    snippet: str
    content: str
    token_count: int


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]
    retrieved_sources: list[Source] = Field(default_factory=list)
    hybrid_used: bool = False
    blocked: bool = False
    guardrail: dict | None = None
    cache_hit: bool = False
    cache_similarity: float | None = None


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        runner_kwargs = dict(
            rerank=request.rerank,
            hybrid=request.hybrid,
            retrieve_only=request.retrieve_only,
        )
        if request.conversation_id is not None:
            runner_kwargs["conversation_id"] = request.conversation_id
        if request.user_id != "anonymous":
            runner_kwargs["user_id"] = request.user_id
        if request.allowed_classification_ids:
            runner_kwargs["allowed_classification_ids"] = request.allowed_classification_ids
        result = answer_question(
            request.question,
            **runner_kwargs,
        )
        if not request.show_sources:
            result["sources"] = []
            result["retrieved_sources"] = []
        return ChatResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Retrieval thất bại: {exc}") from exc


@router.post("/eval/cache/purge")
def purge_cache(expired_only: bool = True) -> dict[str, int | bool]:
    try:
        return {"deleted": purge(expired_only=expired_only), "expired_only": expired_only}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Purge cache thất bại: {exc}") from exc
