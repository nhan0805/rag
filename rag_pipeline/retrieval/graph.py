from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

from config.env_config import settings
from guardrails import GuardVerdict, check_answer, check_question, check_retrieval
from memory.contextualise import contextualise
from memory.store import append_turn, log_memory_event, recent_turns
from retrieval.cache.key import scope_key
from retrieval.cache.store import lookup as cache_lookup
from retrieval.cache.store import save as cache_save
from retrieval.hybrid.fusion import reciprocal_rank_fusion
from retrieval.hybrid.lexical import lexical_search
from retrieval.rerank import apply_rerank, get_reranker
from retrieval.similarity_search import top_k_chunks
from retrieval.step2_normalize_question import normalize_question
from retrieval.step3_embedding_question import embed_question
from retrieval.step7_build_context import build_context
from retrieval.step8_build_prompt import build_prompt
from retrieval.step9_generate_answer import generate_answer
from retrieval.step10_response import make_response, make_sources
from shared.logger import guardrail_file_logger, logger


class RAGState(TypedDict, total=False):
    raw_question: str
    question: str
    query_vector: list[float]
    chunks: list[dict]
    candidate_chunks: list[dict]
    lexical_chunks: list[dict]
    prompt: str
    answer: str
    rerank: bool
    hybrid: bool
    hybrid_used: bool
    retrieve_only: bool
    allowed_classification_ids: list[str]
    user_id: str
    conversation_id: str | None
    blocked: bool
    guardrail: dict
    cache_hit: bool
    cache_similarity: float | None


def _with_rerank_flag(rerank: bool | None) -> bool:
    return settings.rerank_enabled if rerank is None else rerank


def _with_hybrid_flag(hybrid: bool | None) -> bool:
    return settings.hybrid_enabled if hybrid is None else hybrid


def _public_guard(verdict: GuardVerdict) -> dict:
    """Expose a safe diagnostic; never expose the matched pattern detail."""
    return {
        "allowed": verdict.allowed,
        "stage": verdict.stage,
        "code": verdict.code,
        "message": verdict.message,
        "warnings": list(verdict.warnings),
    }


def _record_question_log(verdict: GuardVerdict, question: str) -> None:
    # ``redacted`` is the only question representation allowed into logs.
    safe_question = verdict.redacted if verdict.redacted is not None else question
    logger.info(
        "guard_question stage=%s code=%s question=%s",
        verdict.stage,
        verdict.code,
        safe_question,
    )
    guardrail_file_logger.info(
        "guard_question stage=%s code=%s warnings=%s question=%s",
        verdict.stage,
        verdict.code,
        ",".join(verdict.warnings) or "none",
        safe_question,
    )


def _guard_question_node(state: RAGState) -> None:
    verdict = check_question(state["raw_question"])
    _record_question_log(verdict, state["raw_question"])
    state["guardrail"] = _public_guard(verdict)
    if not verdict.allowed:
        state["blocked"] = True
        state["answer"] = verdict.message
        state["chunks"] = []


def _contextualise_node(state: RAGState) -> None:
    conversation_id = state.get("conversation_id")
    if not settings.memory_enabled:
        log_memory_event("skip", reason="disabled")
        return
    if not conversation_id:
        log_memory_event("skip", reason="no_conversation")
        return
    original_question = state["question"]
    user_id = state.get("user_id", "anonymous")
    history = recent_turns(
        conversation_id,
        user_id,
        n=settings.memory_turns,
    )
    state["question"] = contextualise(original_question, history)
    log_memory_event(
        "context",
        conversation_id,
        user_id,
        turns=len(history),
        changed=int(state["question"] != original_question),
        question_chars=len(original_question),
    )


def _embed_question_node(state: RAGState) -> None:
    state["query_vector"] = embed_question(state["question"])


def _cache_scope(state: RAGState) -> str:
    return scope_key(
        state.get("allowed_classification_ids", []),
        state["rerank"],
        state["hybrid"],
    )


def _check_cache_node(state: RAGState) -> dict | None:
    if not settings.cache_enabled or state.get("retrieve_only"):
        return None
    try:
        return cache_lookup(
            state["query_vector"],
            _cache_scope(state),
            min_similarity=settings.cache_min_similarity,
        )
    except Exception as exc:
        # A cache outage must degrade to a normal RAG request.
        logger.warning("Cache lookup skipped: %s", exc)
        return None


def _retrieve_node(state: RAGState) -> None:
    allowed_ids = state.get("allowed_classification_ids", [])
    # Authenticated HTTP calls always carry a list, including an empty list
    # (fail closed).  The None path keeps pure graph unit tests independent of
    # PostgreSQL; it is never used by the API dependency.
    common = {"allowed_classification_ids": allowed_ids} if allowed_ids is not None else {}
    if state["rerank"] or state["hybrid"]:
        fetch_k = max(settings.retrieve_fetch_k, settings.rerank_top_n)
        chunks = top_k_chunks(
            state["query_vector"],
            fetch_k=fetch_k,
            similarity_threshold=settings.similarity_threshold,
            **common,
        )
    else:
        chunks = top_k_chunks(
            state["query_vector"],
            top_k=settings.top_k,
            similarity_threshold=settings.similarity_threshold,
            **common,
        )
    observed = [{**chunk, "found_by": ["vector"]} for chunk in chunks]
    state["candidate_chunks"] = observed
    state["chunks"] = observed


def _lexical_search_node(state: RAGState) -> None:
    if not state["hybrid"]:
        state["lexical_chunks"] = []
        return
    allowed_ids = state.get("allowed_classification_ids", [])
    if allowed_ids is not None:
        state["lexical_chunks"] = lexical_search(
            state["question"], limit=settings.lexical_fetch_k,
            allowed_classification_ids=allowed_ids,
        )
    else:
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
            {**chunk, "rerank_score": None} for chunk in chunks
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


def _guard_evidence_node(state: RAGState) -> None:
    verdict = check_retrieval(state.get("chunks", []))
    if not verdict.allowed:
        state["blocked"] = True
        state["guardrail"] = _public_guard(verdict)
        state["answer"] = verdict.message
        state["chunks"] = []


def _build_prompt_node(state: RAGState) -> None:
    state["prompt"] = build_prompt(
        state["question"], build_context(state.get("chunks", []))
    )


def _generate_node(state: RAGState) -> None:
    if state.get("retrieve_only"):
        state["answer"] = ""
    else:
        state["answer"] = generate_answer(state["prompt"])


def _guard_answer_node(state: RAGState) -> None:
    verdict = check_answer(
        state.get("answer", ""), build_context(state.get("chunks", []))
    )
    if verdict.warnings or not verdict.allowed:
        state["guardrail"] = _public_guard(verdict)
    if not verdict.allowed:
        state["blocked"] = True
        state["answer"] = verdict.message
        state["chunks"] = []


def _store_cache_node(state: RAGState) -> None:
    if (
        not settings.cache_enabled
        or state.get("retrieve_only")
        or state.get("blocked")
        or not state.get("answer")
    ):
        return
    chunks = state.get("chunks", [])
    document_ids = [
        str(chunk["document_id"])
        for chunk in chunks
        if chunk.get("document_id")
    ]
    if not document_ids:
        return
    try:
        cache_save(
            state["question"],
            state["query_vector"],
            _cache_scope(state),
            state["answer"],
            make_sources(chunks),
            document_ids,
        )
    except Exception as exc:
        logger.warning("Cache save skipped: %s", exc)


def _store_memory_node(state: RAGState) -> None:
    conversation_id = state.get("conversation_id")
    user_id = state.get("user_id", "anonymous")
    if not settings.memory_enabled:
        log_memory_event("skip", reason="disabled")
        return
    if not conversation_id:
        log_memory_event("skip", reason="no_conversation", user_id=user_id)
        return
    if state.get("blocked"):
        log_memory_event("skip", conversation_id, user_id, reason="blocked")
        return
    try:
        append_turn(
            conversation_id,
            user_id,
            state["question"],
            state.get("answer", ""),
        )
    except Exception as exc:
        log_memory_event(
            "error",
            conversation_id,
            user_id,
            operation="write",
            error_type=type(exc).__name__,
        )
        logger.warning("Memory save skipped: %s", exc)


def run_graph(
    question: str,
    rerank: bool | None = None,
    hybrid: bool | None = None,
    retrieve_only: bool = False,
    allowed_classification_ids: Sequence[str] | None = None,
    user_id: str = "anonymous",
    conversation_id: str | None = None,
) -> dict:
    normalized = normalize_question(question)
    state: RAGState = {
        "raw_question": normalized,
        "question": normalized,
        "rerank": _with_rerank_flag(rerank),
        "hybrid": _with_hybrid_flag(hybrid),
        "hybrid_used": False,
        "retrieve_only": retrieve_only,
        "allowed_classification_ids": (
            None
            if allowed_classification_ids is None
            else [str(value) for value in allowed_classification_ids]
        ),
        "user_id": user_id,
        "conversation_id": conversation_id,
        "blocked": False,
        "cache_hit": False,
        "cache_similarity": None,
    }

    _guard_question_node(state)
    if state.get("blocked"):
        return make_response(
            state["answer"], [], [], blocked=True, guardrail=state["guardrail"]
        )

    _contextualise_node(state)
    _embed_question_node(state)
    cached = _check_cache_node(state)
    if cached is not None:
        state["cache_hit"] = True
        state["cache_similarity"] = cached.get("similarity")
        _store_memory_node({**state, "answer": cached["answer"]})
        return {
            "answer": cached["answer"],
            "sources": cached.get("sources", []),
            "retrieved_sources": cached.get("sources", []),
            "hybrid_used": state["hybrid"],
            "blocked": False,
            "guardrail": state.get("guardrail"),
            "cache_hit": True,
            "cache_similarity": cached.get("similarity"),
        }

    _retrieve_node(state)
    _lexical_search_node(state)
    _fuse_results_node(state)
    _rerank_node(state)
    _guard_evidence_node(state)
    if state.get("blocked"):
        return make_response(
            state["answer"], [], [], blocked=True, guardrail=state["guardrail"]
        )

    _build_prompt_node(state)
    _generate_node(state)
    _guard_answer_node(state)
    _store_cache_node(state)
    _store_memory_node(state)
    return make_response(
        state.get("answer", ""),
        state.get("chunks", []),
        [] if state.get("blocked") else state.get("candidate_chunks", []),
        hybrid_used=state.get("hybrid_used", False),
        blocked=state.get("blocked", False),
        guardrail=state.get("guardrail"),
        cache_hit=state.get("cache_hit", False),
        cache_similarity=state.get("cache_similarity"),
    )
