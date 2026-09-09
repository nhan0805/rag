from __future__ import annotations

from uuid import UUID

import psycopg


def upsert_document(
    conn: psycopg.Connection,
    source_path: str,
    raw_content: str,
    content_sha256: str | None = None,
    classification_id: UUID | str | None = None,
    user_id: UUID | str | None = None,
) -> UUID:
    row = conn.execute(
        """
        INSERT INTO rag_documents
            (source_path, raw_content, content_sha256, classification_id, created_by, updated_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_path) DO UPDATE
        SET raw_content = EXCLUDED.raw_content,
            content_sha256 = EXCLUDED.content_sha256,
            classification_id = COALESCE(EXCLUDED.classification_id, rag_documents.classification_id),
            created_by = COALESCE(rag_documents.created_by, EXCLUDED.created_by),
            updated_by = COALESCE(EXCLUDED.updated_by, rag_documents.updated_by),
            updated_at = NOW()
        RETURNING id
        """,
        (source_path, raw_content, content_sha256, classification_id, user_id, user_id),
    ).fetchone()
    assert row is not None
    return row[0]
