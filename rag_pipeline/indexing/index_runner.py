from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from config.db_connection import get_connection
from config.env_config import settings
from indexing.step1_load_input import load_file, load_input_files
from indexing.step2_document_parsing import parse_document
from indexing.step3_chunking_strategy import chunk_text
from indexing.step4_preprocessing import clean_text
from indexing.step6_embedding_gen import embed_text
from indexing.step7_store_documents import upsert_document
from indexing.step8_store_chunks import replace_chunks
from retrieval.cache.store import invalidate_documents
from shared.file_utils import source_path_for
from shared.logger import logger


@dataclass(frozen=True)
class IndexResult:
    status: str
    source_path: str
    chunks_indexed: int = 0
    document_id: str | None = None


def content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _existing_document(conn, source_path: str):
    return conn.execute(
        """
        SELECT d.id, d.content_sha256,
               EXISTS (SELECT 1 FROM rag_chunks c WHERE c.document_id = d.id)
        FROM rag_documents d
        WHERE d.source_path = %s
        """,
        (source_path,),
    ).fetchone()


def _title_from_body(body: str) -> str | None:
    match = re.search(r"(?m)^#\s+(.+?)\s*$", body)
    return match.group(1).strip() if match else None


def index_file(
    path: Path,
    source_path: str | None = None,
    classification_id: UUID | str | None = None,
    user_id: UUID | str | None = None,
    force: bool = False,
    input_dir: Path | None = None,
) -> IndexResult:
    """Parse, hash, and index one file; skip only when hash and chunks exist."""
    input_root = (input_dir or Path(settings.input_dir)).resolve()
    path = path.resolve()
    source = source_path or source_path_for(path, input_root)

    raw_content = load_file(path)
    parsed = parse_document(raw_content)
    body = clean_text(parsed.body)
    digest = content_sha256(body)
    chunks = chunk_text(body, title=_title_from_body(body))
    if not chunks:
        return IndexResult(status="empty", source_path=source)

    # This is intentionally before chunk embedding. A source path alone is
    # not a content identity, and a document row without chunks is incomplete.
    with get_connection() as conn:
        existing = _existing_document(conn, source)
        if (
            existing is not None
            and not force
            and existing[1] == digest
            and bool(existing[2])
        ):
            return IndexResult(
                status="unchanged",
                source_path=source,
                document_id=str(existing[0]),
            )

    embeddings = [embed_text(chunk["content"]) for chunk in chunks]
    with get_connection() as conn:
        document_id = upsert_document(
            conn,
            source,
            body,
            content_sha256=digest,
            classification_id=classification_id,
            user_id=user_id,
        )
        invalidate_documents([str(document_id)], conn=conn)
        replace_chunks(conn, document_id, chunks, embeddings)

    logger.info("Indexed %s: %s chunks", source, len(chunks))
    return IndexResult(
        status="indexed",
        source_path=source,
        chunks_indexed=len(chunks),
        document_id=str(document_id),
    )


def index_all(
    input_dir: Path | None = None,
    user_id: UUID | str | None = None,
    force: bool = False,
) -> dict[str, IndexResult]:
    input_root = (input_dir or Path(settings.input_dir)).resolve()
    return {
        source_path_for(path, input_root): index_file(
            path, input_dir=input_root, user_id=user_id, force=force
        )
        for path in load_input_files(input_root)
    }


if __name__ == "__main__":
    print(index_all())
