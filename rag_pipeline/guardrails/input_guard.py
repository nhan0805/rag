from __future__ import annotations

from config.env_config import settings
from guardrails.base import GuardVerdict
from guardrails.patterns import INJECTION_PATTERNS, redact_pii


def check_question(question: str) -> GuardVerdict:
    """Block obvious instruction attacks and redact PII for safe logging."""
    redacted, pii_labels = redact_pii(question)
    warnings = [f"pii:{label}" for label in pii_labels]

    if len(question) > settings.guard_max_question_chars:
        return GuardVerdict(
            allowed=False,
            stage="input",
            code="question_too_long",
            message="I am unable to answer this request.",
            warnings=warnings,
            redacted=redacted,
            detail={"length": len(question)},
        )

    for code, pattern in INJECTION_PATTERNS:
        if pattern.search(question):
            # Never include the matched pattern in the public message.
            return GuardVerdict(
                allowed=False,
                stage="input",
                code="prompt_injection",
                message="I am unable to answer this request.",
                warnings=warnings,
                redacted=redacted,
                detail={"pattern": code},
            )

    return GuardVerdict(
        allowed=True,
        stage="input",
        code="pii_detected" if pii_labels else "ok",
        message="",
        warnings=warnings,
        redacted=redacted,
        detail={"pii_types": pii_labels},
    )
