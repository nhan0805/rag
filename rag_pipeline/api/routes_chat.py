from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from retrieval.retrieval_runner import answer_question


router = APIRouter()


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    rerank: bool | None = None
    hybrid: bool | None = None
    retrieve_only: bool = False
    show_sources: bool = True


class Source(BaseModel):
    n: int
    source: str
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


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        result = answer_question(
            request.question,
            rerank=request.rerank,
            hybrid=request.hybrid,
            retrieve_only=request.retrieve_only,
        )
        if not request.show_sources:
            result["sources"] = []
            result["retrieved_sources"] = []
        return ChatResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Retrieval thất bại: {exc}") from exc
