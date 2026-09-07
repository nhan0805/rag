from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
import json
from typing import Any

from config.db_connection import get_connection
from config.env_config import settings
from indexing.step8_store_chunks import vector_literal


def lookup(
    question_vector: Sequence[float],
    scope: str,
    min_similarity: float | None = None,
) -> dict[str, Any] | None:
    threshold = settings.cache_min_similarity if min_similarity is None else min_similarity
    vector = vector_literal(question_vector)
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT id, question, answer, sources, document_ids,
                   1 - (question_vec <=> %s::vector) AS similarity
            FROM rag_query_cache
            WHERE scope_key = %s
              AND (expires_at IS NULL OR expires_at > NOW())
              AND 1 - (question_vec <=> %s::vector) >= %s
            ORDER BY question_vec <=> %s::vector
            LIMIT 1
            """,
            (vector, scope, vector, threshold, vector),
        ).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE rag_query_cache SET hit_count = hit_count + 1 WHERE id = %s", (row[0],))

    return {
        "id": str(row[0]),
        "question": row[1],
        "answer": row[2],
        "sources": row[3] or [],
        "document_ids": [str(value) for value in (row[4] or [])],
        "similarity": float(row[5]),
    }


def save(
    question: str,
    question_vector: Sequence[float],
    scope: str,
    answer: str,
    sources: list[dict],
    document_ids: Sequence[str],
    ttl_hours: int | None = None,
) -> None:
    if not document_ids:
        return
    ttl = settings.cache_ttl_hours if ttl_hours is None else ttl_hours
    expires_at = datetime.utcnow() + timedelta(hours=ttl) if ttl > 0 else None
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO rag_query_cache
                (question, question_vec, scope_key, answer, sources, document_ids, expires_at)
            VALUES (%s, %s::vector, %s, %s, %s::jsonb, %s::uuid[], %s)
            """,
            (
                question,
                vector_literal(question_vector),
                scope,
                answer,
                json.dumps(sources, ensure_ascii=False),
                list(document_ids),
                expires_at,
            ),
        )


def invalidate_documents(document_ids: Sequence[str], conn: Any | None = None) -> int:
    ids = [str(value) for value in document_ids if value]
    if not ids:
        return 0

    def execute(connection: Any) -> int:
        cursor = connection.execute(
            "DELETE FROM rag_query_cache WHERE document_ids && %s::uuid[]",
            (ids,),
        )
        return cursor.rowcount

    if conn is not None:
        return execute(conn)
    with get_connection() as connection:
        return execute(connection)


def purge(expired_only: bool = True) -> int:
    sql = (
        "DELETE FROM rag_query_cache WHERE expires_at IS NOT NULL AND expires_at <= NOW()"
        if expired_only
        else "DELETE FROM rag_query_cache"
    )
    with get_connection() as conn:
        cursor = conn.execute(sql)
        return cursor.rowcount
