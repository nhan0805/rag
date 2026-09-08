"""Data-only guardrail patterns.

Keeping these lists separate makes corpus- or language-specific tuning safe:
changing a phrase does not change the guard decision algorithm.
"""

from __future__ import annotations

import re


INJECTION_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "instruction_override",
        re.compile(
            r"\b(ignore|disregard|forget|override)\b.{0,80}\b(previous|above|prior|all)\b.{0,40}\b(instructions?|rules?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "prompt_exfiltration",
        re.compile(
            r"\b(print|reveal|show|tell|output|repeat|dump)\b.{0,80}\b(system prompt|developer prompt|hidden prompt|secret instructions?)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "instruction_override_vi",
        re.compile(
            r"\b(bỏ qua|bo qua|phớt lờ|phot lo|quên|quen|ghi đè|ghi de)\b.{0,100}\b(hướng dẫn|huong dan|chỉ dẫn|chi dan|quy tắc|quy tac)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
    (
        "prompt_exfiltration_vi",
        re.compile(
            r"\b(in|hiện|hien|tiết lộ|tiet lo|cho xem|lặp lại|lap lai)\b.{0,80}\b(system prompt|prompt hệ thống|prompt he thong|hướng dẫn ẩn|huong dan an)\b",
            re.IGNORECASE | re.DOTALL,
        ),
    ),
)

# These are warnings only.  A user may paste their own identifier into a
# support question; rejecting that question is the wrong security boundary.
_CONTEXTUAL_NATIONAL_ID = re.compile(
    r"(?P<prefix>\b(?:cccd|căn cước(?: công dân)?|can cuoc(?: cong dan)?)\b[^0-9]{0,24})"
    r"(?P<value>\d{7,12})(?!\d)",
    re.IGNORECASE,
)

PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("NATIONAL-ID", _CONTEXTUAL_NATIONAL_ID),
    ("NATIONAL-ID", re.compile(r"(?<!\d)\d{9,12}(?!\d)")),
    ("PHONE", re.compile(r"(?<!\d)(?:\+?84|0)(?:[ .-]?\d){8,10}(?!\d)")),
    (
        "EMAIL",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
)


def redact_pii(text: str) -> tuple[str, list[str]]:
    redacted = text
    found: list[str] = []
    for label, pattern in PII_PATTERNS:
        if pattern.search(redacted):
            if label not in found:
                found.append(label)
            if pattern is _CONTEXTUAL_NATIONAL_ID:
                redacted = pattern.sub(
                    lambda match: f"{match.group('prefix')}[{label}]", redacted
                )
            else:
                redacted = pattern.sub(f"[{label}]", redacted)
    return redacted, found
