from __future__ import annotations

from pathlib import Path

from config.db_connection import get_connection
from config.env_config import settings
from indexing.step1_load_input import load_file, load_input_files
from indexing.step2_document_parsing import parse_document
from indexing.step3_chunking_strategy import fixed_token_chunks
from indexing.step4_preprocessing import clean_text
from indexing.step6_embedding_gen import embed_text
from indexing.step7_store_documents import upsert_document
from indexing.step8_store_chunks import replace_chunks
from retrieval.cache.store import invalidate_documents
from shared.file_utils import source_path_for
from shared.logger import logger


def index_file(path: Path, input_dir: Path | None = None) -> int:
    input_root = input_dir or Path(settings.input_dir)
    path = path.resolve()
    input_root = input_root.resolve()
    source_path = source_path_for(path, input_root)

    raw_content = load_file(path)
    parsed = parse_document(raw_content)
    body = clean_text(parsed.body)
    chunks = fixed_token_chunks(body, settings.chunk_size, settings.chunk_overlap)
    embeddings = [embed_text(chunk["content"]) for chunk in chunks]

    with get_connection() as conn:
        document_id = upsert_document(conn, source_path, raw_content)
        # Reindexing is an UPDATE path; the database DELETE trigger cannot
        # observe it, so invalidate the cache in the same transaction.
        invalidate_documents([str(document_id)], conn=conn)
        replace_chunks(conn, document_id, chunks, embeddings)

    logger.info("Indexed %s: %s chunks", source_path, len(chunks))
    return len(chunks)


def index_all(input_dir: Path | None = None) -> dict[str, int]:
    input_root = (input_dir or Path(settings.input_dir)).resolve()
    return {
        source_path_for(path, input_root): index_file(path, input_root)
        for path in load_input_files(input_root)
    }


if __name__ == "__main__":
    print(index_all())
