from __future__ import annotations


def _source_item(number: int, chunk: dict) -> dict:
    content = chunk["content"]
    vector_score = chunk.get("vector_score", chunk.get("similarity"))
    found_by = chunk.get("found_by")
    if found_by is None:
        found_by = ["vector"] if vector_score is not None else []
    return {
        "n": number,
        "source": chunk["source_path"],
        "chunk_index": chunk["chunk_index"],
        "score": chunk.get("score", chunk.get("rrf_score", vector_score)),
        "vector_score": vector_score,
        "vector_rank": chunk.get("vector_rank"),
        "lexical_score": chunk.get("lexical_score"),
        "lexical_rank": chunk.get("lexical_rank"),
        "rrf_score": chunk.get("rrf_score"),
        "rrf_rank": chunk.get("rrf_rank"),
        "found_by": list(found_by),
        "rerank_score": chunk.get("rerank_score"),
        "snippet": content[:240],
        "content": content,
        "token_count": chunk.get("token_count", len(content.split())),
    }


def make_sources(chunks: list[dict]) -> list[dict]:
    return [_source_item(index, chunk) for index, chunk in enumerate(chunks, start=1)]


def make_response(
    answer: str,
    chunks: list[dict],
    candidate_chunks: list[dict] | None = None,
    hybrid_used: bool = False,
) -> dict:
    response = {
        "answer": answer,
        "sources": make_sources(chunks),
        "hybrid_used": hybrid_used,
    }
    if candidate_chunks is not None:
        response["retrieved_sources"] = make_sources(candidate_chunks)
    return response
