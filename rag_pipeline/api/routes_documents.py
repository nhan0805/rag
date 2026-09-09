from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from auth.deps import CurrentUser, get_current_user
from config.db_connection import get_connection
from config.env_config import settings


router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("")
def list_documents(user: CurrentUser = Depends(get_current_user)) -> list[dict[str, object]]:
    if not user.classification_ids:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT d.id, d.source_path, c.name, d.content_sha256,
                   d.created_by, COUNT(ch.id) AS chunk_count,
                   d.created_at, d.updated_at
            FROM rag_documents d
            JOIN rag_classifications c ON c.id = d.classification_id
            LEFT JOIN rag_chunks ch ON ch.document_id = d.id
            WHERE d.classification_id = ANY(%s::uuid[])
            GROUP BY d.id, d.source_path, c.name, d.content_sha256,
                     d.created_by, d.created_at, d.updated_at
            ORDER BY d.updated_at DESC, d.source_path
            """,
            (list(user.classification_ids),),
        ).fetchall()
    return [
        {
            "id": str(row[0]),
            "source_path": row[1],
            "classification": row[2],
            "content_sha256": (row[3] or "")[:12],
            "created_by": str(row[4]) if row[4] else None,
            "chunk_count": row[5],
            "created_at": row[6].isoformat(),
            "updated_at": row[7].isoformat(),
        }
        for row in rows
    ]


def _remove_source_file(source_path: str) -> None:
    input_root = Path(settings.input_dir).resolve()
    candidate = (input_root / source_path).resolve()
    try:
        candidate.relative_to(input_root)
    except ValueError:
        return
    if candidate != input_root and candidate.is_file():
        candidate.unlink()


@router.delete("/{document_id}")
def delete_document(
    document_id: UUID,
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, str]:
    # Authorization is part of DELETE itself; a forbidden document is
    # indistinguishable from a missing one (404, never 403).
    if not user.classification_ids:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
    try:
        with get_connection() as conn:
            row = conn.execute(
                """
                DELETE FROM rag_documents
                 WHERE id = %s
                   AND classification_id = ANY(%s::uuid[])
                RETURNING source_path
                """,
                (document_id, list(user.classification_ids)),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu")
        _remove_source_file(row[0])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Xoá tài liệu thất bại: {exc}") from exc
    return {"document_id": str(document_id), "status": "deleted"}
