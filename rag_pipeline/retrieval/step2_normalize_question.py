from __future__ import annotations

import re


def normalize_question(question: str) -> str:
    return re.sub(r"\s+", " ", question).strip()

