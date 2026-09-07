from __future__ import annotations

from collections.abc import Sequence

from config.db_connection import get_connection
from config.env_config import settings
from retrieval.hybrid.query_builder import build_tsquery


def lexical_search(
    question: str,
    limit: int | None = None,
    fetch_k: int | None = None,
    allowed_classification_ids: Sequence[str] | None = None,
) -> list[dict]:
    """Find chunks using PostgreSQL full-text search and ``ts_rank``.

    The query is parameterized and the generated tsquery uses OR between
    meaningful terms, which lets exact identifiers rescue vector misses.
    """
    tsquery = build_tsquery(question)
    if not tsquery:
        return []

    if limit is not None and fetch_k is not None:
        raise ValueError("pass either limit or fetch_k, not both")
    requested_limit = fetch_k if fetch_k is not None else limit
    fetch_limit = (
        settings.lexical_fetch_k
        if requested_limit is None
        else int(requested_limit)
    )
    if fetch_limit <= 0:
        return []

    config = settings.text_search_config
    classification_clause = ""
    params: list[object] = [config, tsquery]
    if allowed_classification_ids:
        classification_clause = "AND d.classification_id = ANY(%s)"
        params.append(list(allowed_classification_ids))
    params.append(fetch_limit)
    with get_connection() as conn:
        rows = conn.execute(
            f"""
            WITH query AS (
                SELECT to_tsquery(%s, %s) AS tsquery
            )
            SELECT
                c.id,
                c.document_id,
                c.chunk_index,
                c.content,
                c.token_count,
                d.source_path,
                d.title,
                ts_rank(c.content_tsv, query.tsquery) AS lexical_score
            FROM rag_chunks c
            JOIN rag_documents d ON d.id = c.document_id
            CROSS JOIN query
            WHERE c.content_tsv @@ query.tsquery
              {classification_clause}
            ORDER BY lexical_score DESC, c.id
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
            "title": row[6],
            "lexical_score": float(row[7]),
            "lexical_rank": rank,
            "found_by": ["lexical"],
        }
        for rank, row in enumerate(rows, start=1)
    ]


# Keep a descriptive alias for callers that prefer verb-first naming.
search_lexical = lexical_search
