from __future__ import annotations


def validate_question(question: str) -> str:
    if not isinstance(question, str) or not question.strip():
        raise ValueError("question không được để trống")
    return question

