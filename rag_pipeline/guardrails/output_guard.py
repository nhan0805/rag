from __future__ import annotations

import re
from collections.abc import Iterable

from config.env_config import settings
from guardrails.base import GuardVerdict
from guardrails.patterns import PII_PATTERNS


_PROMPT_LEAK = re.compile(
    r"\b(system prompt|developer message|hidden instructions?|internal prompt)\b",
    re.IGNORECASE,
)
_NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)?%?(?![A-Za-z])")


def _context_text(context: str | Iterable[dict] | None) -> str:
    if context is None:
        return ""
    if isinstance(context, str):
        return context
    return "\n".join(str(item.get("content", "")) for item in context)


def check_answer(
    answer: str,
    context: str | Iterable[dict] | None = None,
) -> GuardVerdict:
    """Check model output; unsupported numeric claims remain warnings by default."""
    if _PROMPT_LEAK.search(answer):
        return GuardVerdict(
            allowed=False,
            stage="output",
            code="prompt_leak",
            message="I am unable to answer this request.",
        )

    context_text = _context_text(context)
    for label, pattern in PII_PATTERNS:
        if pattern.search(answer) and not pattern.search(context_text):
            return GuardVerdict(
                allowed=False,
                stage="output",
                code="uncontextualized_pii",
                message="I am unable to answer this request.",
                detail={"pii_type": label},
            )

    warnings: list[str] = []
    if _NUMBER.search(answer) and not _NUMBER.search(context_text):
        warnings.append("unsupported_number")

    if settings.guard_output_action == "block" and warnings:
        return GuardVerdict(
            allowed=False,
            stage="output",
            code="unsupported_number",
            message="I am unable to answer this request.",
            warnings=warnings,
        )

    return GuardVerdict(allowed=True, stage="output", warnings=warnings)
