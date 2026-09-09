from __future__ import annotations

import hashlib
from typing import Any

from config.db_connection import get_connection
from config.env_config import settings
from shared.logger import memory_file_logger


def _fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def log_memory_event(
    event: str,
    conversation_id: str | None = None,
    user_id: str | None = None,
    **fields: object,
) -> None:
    """Write memory telemetry without putting questions/answers in a log file."""
    safe_fields = {
        "conversation": _fingerprint(conversation_id) if conversation_id else "none",
        "user": _fingerprint(user_id) if user_id else "none",
        **fields,
    }
    details = " ".join(f"{key}={safe_fields[key]}" for key in sorted(safe_fields))
    memory_file_logger.info("memory_%s %s", event, details)


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
    log_memory_event(
        "write",
        conversation_id,
        user_id,
        question_chars=len(question),
        answer_chars=len(answer),
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
    result = [
        {"question": row[0], "answer": row[1], "created_at": row[2]}
        for row in reversed(rows)
    ]
    log_memory_event(
        "read",
        conversation_id,
        user_id,
        turns=len(result),
        limit=limit,
    )
    return result
