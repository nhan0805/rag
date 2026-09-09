from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from auth.deps import CurrentUser, get_current_user, require_admin
from auth.permissions import classification_id_by_name, list_classifications
from config.env_config import settings
from indexing.index_runner import IndexResult, index_all, index_file
from shared.file_utils import safe_upload_name


router = APIRouter(tags=["documents"])


def validate_upload_classification(
    classification: str | None,
    user: CurrentUser,
) -> UUID:
    label = (classification or settings.default_classification).strip().upper()
    if not label:
        raise HTTPException(status_code=400, detail="Phải chọn classification")
    classification_id = classification_id_by_name(label)
    if classification_id is None:
        raise HTTPException(status_code=400, detail=f"Classification không tồn tại: {label}")
    if str(classification_id) not in set(user.classification_ids):
        raise HTTPException(status_code=403, detail="Bạn không có quyền ghi vào classification này")
    return classification_id


def _write_and_index(
    file: UploadFile,
    classification: str | None,
    user: CurrentUser,
) -> tuple[str, IndexResult]:
    filename = file.filename or ""
    if not filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file .md")
    try:
        safe_name = safe_upload_name(filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    classification_id = validate_upload_classification(classification, user)
    input_dir = Path(settings.input_dir).resolve()
    input_dir.mkdir(parents=True, exist_ok=True)
    destination = (input_dir / safe_name).resolve()
    if destination.parent != input_dir:
        raise HTTPException(status_code=400, detail="Đường dẫn upload không hợp lệ")

    # UploadFile has already been validated as a small, local Markdown input;
    # write it only after both classification checks have passed.
    content = file.file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File rỗng")
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="File phải là UTF-8") from exc
    destination.write_text(text, encoding="utf-8")
    try:
        result = index_file(
            destination,
            source_path=safe_name,
            classification_id=classification_id,
            user_id=user.id,
            input_dir=input_dir,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Indexing thất bại: {exc}") from exc
    return safe_name, result


@router.get("/upload/classifications")
def upload_classifications(user: CurrentUser = Depends(get_current_user)) -> list[dict[str, str]]:
    allowed = set(user.classification_ids)
    return [item for item in list_classifications() if item["id"] in allowed]


@router.post("/upload")
async def upload_markdown(
    file: UploadFile = File(...),
    classification: str = Form(""),
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, object]:
    filename, result = _write_and_index(file, classification, user)
    return {"filename": filename, **asdict(result)}


@router.post("/upload-folder")
async def upload_folder(
    files: list[UploadFile] = File(...),
    classification: str = Form(""),
    user: CurrentUser = Depends(get_current_user),
) -> dict[str, object]:
    results = []
    for file in files:
        filename, result = _write_and_index(file, classification, user)
        results.append({"filename": filename, **asdict(result)})
    return {"files": results, "indexed_count": sum(item["status"] == "indexed" for item in results)}


@router.post("/reindex")
def reindex_all(
    _: CurrentUser = Depends(require_admin),
) -> dict[str, object]:
    """Re-index mounted Markdown while preserving existing classification/owner."""
    try:
        results = index_all(Path(settings.input_dir).resolve())
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Reindex thất bại: {exc}") from exc
    serialized = {path: asdict(result) for path, result in results.items()}
    return {
        "indexed_count": sum(result.status == "indexed" for result in results.values()),
        "unchanged_count": sum(result.status == "unchanged" for result in results.values()),
        "empty_count": sum(result.status == "empty" for result in results.values()),
        "total_chunks": sum(result.chunks_indexed for result in results.values()),
        "files": serialized,
    }
