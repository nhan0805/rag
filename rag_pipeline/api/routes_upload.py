from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from uuid import UUID

from config.db_connection import get_connection
from config.env_config import settings
from indexing.index_runner import index_all, index_file
from shared.file_utils import safe_upload_name


router = APIRouter()


@router.post("/upload")
async def upload_markdown(file: UploadFile = File(...)) -> dict[str, int | str]:
    filename = file.filename or ""
    if not filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .md")
    try:
        safe_name = safe_upload_name(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File rỗng")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File phải là UTF-8") from exc

    input_dir = Path(settings.input_dir)
    input_dir.mkdir(parents=True, exist_ok=True)
    destination = input_dir / safe_name
    destination.write_text(text, encoding="utf-8")
    try:
        chunks_indexed = index_file(destination, input_dir)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Indexing thất bại: {exc}") from exc
    return {"filename": safe_name, "chunks_indexed": chunks_indexed}


@router.post("/reindex")
def reindex_all() -> dict[str, object]:
    """Re-index every Markdown file currently mounted under input/."""
    try:
        indexed = index_all(Path(settings.input_dir))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Reindex thất bại: {exc}") from exc
    return {
        "indexed_count": len(indexed),
        "total_chunks": sum(indexed.values()),
        "files": indexed,
    }


@router.delete("/documents/{document_id}")
def delete_document(document_id: UUID) -> dict[str, str]:
    """Delete a document; the database trigger removes dependent cache rows."""
    try:
        with get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM rag_documents WHERE id = %s",
                (document_id,),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Xoá tài liệu thất bại: {exc}") from exc
    return {"document_id": str(document_id), "status": "deleted"}
