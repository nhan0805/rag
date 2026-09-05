from __future__ import annotations

from pathlib import Path


def markdown_files(input_dir: Path) -> list[Path]:
    input_dir.mkdir(parents=True, exist_ok=True)
    return sorted(
        path for path in input_dir.rglob("*") if path.is_file() and path.suffix.lower() == ".md"
    )


def source_path_for(path: Path, input_dir: Path) -> str:
    return path.resolve().relative_to(input_dir.resolve()).as_posix()


def safe_upload_name(filename: str) -> str:
    name = Path(filename).name.strip()
    if not name or name in {".", ".."}:
        raise ValueError("Tên file không hợp lệ")
    return name

