from __future__ import annotations

from pathlib import Path

from shared.file_utils import markdown_files


def load_input_files(input_dir: Path) -> list[Path]:
    """Return all Markdown files under input/, in deterministic order."""
    return markdown_files(input_dir)


def load_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")

