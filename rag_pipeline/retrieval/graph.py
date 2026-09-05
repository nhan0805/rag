from __future__ import annotations

from typing import TypedDict

from config.env_config import settings
from retrieval.hybrid.fusion import reciprocal_rank_fusion
from retrieval.hybrid.lexical import lexical_search
from retrieval.rerank import apply_rerank, get_reranker
from retrieval.similarity_search import top_k_chunks
from retrieval.step2_normalize_question import normalize_question
from retrieval.step3_embedding_question import embed_question
from retrieval.step7_build_context import build_context
from retrieval.step8_build_prompt import build_prompt
from retrieval.step9_generate_answer import generate_answer
from retrieval.step10_response import make_response


class RAGState(TypedDict, total=False):
    question: str
    query_vector: list[float]
    chunks: list[dict]
    candidate_chunks: list[dict]
    prompt: str
    answer: str
    rerank: bool
    hybrid: bool
    hybrid_used: bool
    retrieve_only: bool


def _with_rerank_flag(rerank: bool | None) -> bool:
    return settings.rerank_enabled if rerank is None else rerank


def _with_hybrid_flag(hybrid: bool | None) -> bool:
    return settings.hybrid_enabled if hybrid is None else hybrid


def _embed_question_node(state: RAGState) -> None:
    state["query_vector"] = embed_question(state["question"])


def _retrieve_node(state: RAGState) -> None:
    if state["rerank"] or state["hybrid"]:
        fetch_k = max(settings.retrieve_fetch_k, settings.rerank_top_n)
        chunks = top_k_chunks(
            state["query_vector"],
            fetch_k=fetch_k,
            similarity_threshold=settings.similarity_threshold,
        )
    else:
        chunks = top_k_chunks(
            state["query_vector"],
            top_k=settings.top_k,
            similarity_threshold=settings.similarity_threshold,
        )
    observed = [{**chunk, "found_by": ["vector"]} for chunk in chunks]
    state["candidate_chunks"] = observed
    state["chunks"] = observed


def _lexical_search_node(state: RAGState) -> None:
    if not state["hybrid"]:
        state["lexical_chunks"] = []
        return
    state["lexical_chunks"] = lexical_search(
        state["question"], limit=settings.lexical_fetch_k
    )


def _fuse_results_node(state: RAGState) -> None:
    vector_chunks = state.get("candidate_chunks", [])
    lexical_chunks = state.get("lexical_chunks", [])
    if not state["hybrid"] or not lexical_chunks:
        state["hybrid_used"] = False
        state["chunks"] = vector_chunks
        return

    fused = reciprocal_rank_fusion(
        {"vector": vector_chunks, "lexical": lexical_chunks},
        k=settings.rrf_k,
    )
    state["hybrid_used"] = bool(lexical_chunks)
    # ``vector_rank`` is the rank immediately before reranking. Once RRF has
    # changed the order, this is the rank that the reranker/UI must report.
    for rank, chunk in enumerate(fused, start=1):
        if "vector_rank" in chunk:
            chunk["vector_source_rank"] = chunk["vector_rank"]
        chunk["vector_rank"] = rank
    state["candidate_chunks"] = fused
    state["chunks"] = fused


def _rerank_node(state: RAGState) -> None:
    chunks = state.get("candidate_chunks", [])
    if not state["rerank"]:
        state["chunks"] = [
            {**chunk, "rerank_score": None} for chunk in chunks[: settings.top_k]
        ]
        return

    backend = get_reranker()
    if backend is None:
        state["chunks"] = [
            {**chunk, "rerank_score": None} for chunk in chunks[: settings.top_k]
        ]
        return
    state["chunks"] = apply_rerank(
        state["question"],
        chunks,
        backend,
        top_n=settings.rerank_top_n,
        min_score=settings.rerank_min_score,
    )


def _build_prompt_node(state: RAGState) -> None:
    state["prompt"] = build_prompt(
        state["question"], build_context(state.get("chunks", []))
    )


def _generate_node(state: RAGState) -> None:
    if state.get("retrieve_only"):
        state["answer"] = ""
    elif not state.get("chunks"):
        state["answer"] = (
            "I could not find a relevant document to answer this question."
        )
    else:
        state["answer"] = generate_answer(state["prompt"])


def run_graph(
    question: str,
    rerank: bool | None = None,
    hybrid: bool | None = None,
    retrieve_only: bool = False,
) -> dict:
    state: RAGState = {
        "question": normalize_question(question),
        "rerank": _with_rerank_flag(rerank),
        "hybrid": _with_hybrid_flag(hybrid),
        "hybrid_used": False,
        "retrieve_only": retrieve_only,
    }
    _embed_question_node(state)
    _retrieve_node(state)
    _lexical_search_node(state)
    _fuse_results_node(state)
    _rerank_node(state)
    _build_prompt_node(state)
    _generate_node(state)
    return make_response(
        state.get("answer", ""),
        state.get("chunks", []),
        state.get("candidate_chunks", []),
        hybrid_used=state.get("hybrid_used", False),
    )
