from __future__ import annotations

from config.db_connection import get_connection
from config.env_config import settings
from retrieval.hybrid.query_builder import build_tsquery


def lexical_search(
    question: str,
    limit: int | None = None,
    fetch_k: int | None = None,
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
    with get_connection() as conn:
        rows = conn.execute(
            """
            WITH query AS (
                SELECT to_tsquery(%s, %s) AS tsquery
            )
            SELECT
                c.id,
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
            ORDER BY lexical_score DESC, c.id
            LIMIT %s
            """,
            (config, tsquery, fetch_limit),
        ).fetchall()

    return [
        {
            "chunk_id": str(row[0]),
            "chunk_index": row[1],
            "content": row[2],
            "token_count": row[3],
            "source_path": row[4],
            "title": row[5],
            "lexical_score": float(row[6]),
            "lexical_rank": rank,
            "found_by": ["lexical"],
        }
        for rank, row in enumerate(rows, start=1)
    ]


# Keep a descriptive alias for callers that prefer verb-first naming.
search_lexical = lexical_search
