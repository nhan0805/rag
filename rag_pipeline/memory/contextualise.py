from __future__ import annotations

import re
from collections.abc import Sequence


_DEPENDENT = re.compile(
    r"^(?:thế còn|the con|còn|con|vậy còn|vay con|what about|and what about|how about|and)\b|\b(asking about|nói về|noi ve)\b",
    re.IGNORECASE,
)


def _last_topic(history: Sequence[dict]) -> str:
    if not history:
        return ""
    previous = str(history[-1].get("question", "")).strip()
    return previous


def contextualise(question: str, history: Sequence[dict] | None) -> str:
    """Turn a dependent follow-up into a retrieval-friendly query.

    The deterministic path intentionally preserves independent first-turn
    questions exactly; that avoids an extra model call and avoids rewriting a
    question that already retrieves well.
    """
    if not history:
        return question
    stripped = question.strip()
    if not _DEPENDENT.search(stripped):
        return question

    previous = _last_topic(history)
    if not previous:
        return question
    if re.match(r"^(?:thế còn|the con|còn|con|vậy còn|vay con)\b", stripped, re.I):
        follow_up = re.sub(r"^(?:thế còn|the con|còn|con|vậy còn|vay con)\s*", "", stripped, flags=re.I)
        return f"{previous}. Additional question about {follow_up}"
    return f"{previous}. {stripped}"
