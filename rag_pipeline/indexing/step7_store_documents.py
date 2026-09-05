from __future__ import annotations

from uuid import UUID

import psycopg


def upsert_document(conn: psycopg.Connection, source_path: str, raw_content: str) -> UUID:
    row = conn.execute(
        """
        INSERT INTO rag_documents (source_path, raw_content)
        VALUES (%s, %s)
        ON CONFLICT (source_path) DO UPDATE
        SET raw_content = EXCLUDED.raw_content, updated_at = NOW()
        RETURNING id
        """,
        (source_path, raw_content),
    ).fetchone()
    assert row is not None
    return row[0]

