from __future__ import annotations

from collections.abc import Sequence

from config.db_connection import get_connection
from config.env_config import settings
from indexing.step8_store_chunks import vector_literal


def top_k_chunks(
    question_embedding: Sequence[float],
    top_k: int | None = None,
    fetch_k: int | None = None,
    similarity_threshold: float | None = None,
) -> list[dict]:
    """Retrieve candidates in vector order and preserve their original rank.

    ``fetch_k`` is intentionally separate from ``top_k``: reranking needs a
    larger candidate pool, while the non-reranked path keeps the old behavior.
    """
    limit = fetch_k if fetch_k is not None else (top_k if top_k is not None else settings.top_k)
    if limit <= 0:
        return []

    embedding = vector_literal(question_embedding)
    threshold = (
        settings.similarity_threshold
        if similarity_threshold is None
        else similarity_threshold
    )
    threshold_clause = ""
    params: list[object] = [embedding]
    if threshold > 0:
        threshold_clause = "WHERE 1 - (e.embedding <=> %s::vector) >= %s"
        params.extend([embedding, threshold])
    params.append(embedding)
    params.append(limit)

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                c.id,
                c.chunk_index,
                c.content,
                c.token_count,
                d.source_path,
                1 - (e.embedding <=> %s::vector) AS similarity
            FROM rag_embeddings e
            JOIN rag_chunks c ON c.id = e.chunk_id
            JOIN rag_documents d ON d.id = c.document_id
            {threshold_clause}
            ORDER BY e.embedding <=> %s::vector
            LIMIT %s
            """,
            tuple(params),
        ).fetchall()

    return [
        {
            "chunk_id": str(row[0]),
            "chunk_index": row[1],
            "content": row[2],
            "token_count": row[3],
            "source_path": row[4],
            "similarity": float(row[5]),
            "vector_score": float(row[5]),
            "vector_rank": rank,
        }
        for rank, row in enumerate(rows, start=1)
    ]
