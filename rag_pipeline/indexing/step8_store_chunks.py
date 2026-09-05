from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import psycopg

from config.env_config import settings
from indexing.step3_chunking_strategy import Chunk


def vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(format(float(value), ".10g") for value in vector) + "]"


def replace_chunks(
    conn: psycopg.Connection,
    document_id: UUID,
    chunks: Sequence[Chunk],
    embeddings: Sequence[Sequence[float]],
) -> None:
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings must have the same length")

    # Reindexing the same source must not leave stale chunks behind.
    conn.execute("DELETE FROM rag_chunks WHERE document_id = %s", (document_id,))
    for chunk, embedding in zip(chunks, embeddings):
        row = conn.execute(
            """
            INSERT INTO rag_chunks (document_id, chunk_index, content, token_count)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (
                document_id,
                chunk["chunk_index"],
                chunk["content"],
                chunk["token_count"],
            ),
        ).fetchone()
        assert row is not None
        conn.execute(
            """
            INSERT INTO rag_embeddings (chunk_id, embedding, model)
            VALUES (%s, %s::vector, %s)
            """,
            (row[0], vector_literal(embedding), settings.embedding_model),
        )

