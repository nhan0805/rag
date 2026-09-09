from __future__ import annotations

from collections.abc import Sequence

from config.db_connection import get_connection
from config.env_config import settings
from indexing.step8_store_chunks import vector_literal


def top_k_chunks(
    question_embedding: Sequence[float],
    allowed_classification_ids: Sequence[str],
    top_k: int | None = None,
    fetch_k: int | None = None,
    similarity_threshold: float | None = None,
) -> list[dict]:
    """Retrieve candidates in vector order and preserve their original rank.

    ``fetch_k`` is intentionally separate from ``top_k``: reranking needs a
    larger candidate pool, while the non-reranked path keeps the old behavior.
    """
    if not allowed_classification_ids:
        return []
    limit = fetch_k if fetch_k is not None else (top_k if top_k is not None else settings.top_k)
    if limit <= 0:
        return []

    embedding = vector_literal(question_embedding)
    threshold = (
        settings.similarity_threshold
        if similarity_threshold is None
        else similarity_threshold
    )
    clauses: list[str] = ["d.classification_id = ANY(%s::uuid[])"]
    params: list[object] = [embedding, list(allowed_classification_ids)]
    if threshold > 0:
        clauses.append("1 - (e.embedding <=> %s::vector) >= %s")
        params.extend([embedding, threshold])
    params.append(embedding)
    params.append(limit)
    where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""

    with get_connection() as conn:
        rows = conn.execute(
            f"""
            SELECT
                c.id,
                c.document_id,
                c.chunk_index,
                c.content,
                c.token_count,
                d.source_path,
                1 - (e.embedding <=> %s::vector) AS similarity
            FROM rag_embeddings e
            JOIN rag_chunks c ON c.id = e.chunk_id
            JOIN rag_documents d ON d.id = c.document_id
            {where_clause}
            ORDER BY e.embedding <=> %s::vector
            LIMIT %s
            """,
            tuple(params),
        ).fetchall()

    return [
        {
            "chunk_id": str(row[0]),
            "document_id": str(row[1]),
            "chunk_index": row[2],
            "content": row[3],
            "token_count": row[4],
            "source_path": row[5],
            "similarity": float(row[6]),
            "vector_score": float(row[6]),
            "vector_rank": rank,
        }
        for rank, row in enumerate(rows, start=1)
    ]
