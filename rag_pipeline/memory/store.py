from __future__ import annotations

from typing import Any

from config.db_connection import get_connection
from config.env_config import settings


def append_turn(
    conversation_id: str,
    user_id: str,
    question: str,
    answer: str,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO rag_conversation_turns
                (conversation_id, user_id, question, answer)
            VALUES (%s, %s, %s, %s)
            """,
            (conversation_id, user_id, question, answer),
        )


def recent_turns(
    conversation_id: str,
    user_id: str,
    n: int | None = None,
) -> list[dict[str, Any]]:
    limit = settings.memory_turns if n is None else max(n, 0)
    if limit == 0:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT question, answer, created_at
            FROM rag_conversation_turns
            WHERE conversation_id = %s AND user_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (conversation_id, user_id, limit),
        ).fetchall()
    return [
        {"question": row[0], "answer": row[1], "created_at": row[2]}
        for row in reversed(rows)
    ]
