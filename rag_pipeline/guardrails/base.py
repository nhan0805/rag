from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class GuardVerdict:
    """The shared, deliberately small contract returned by every guard."""

    allowed: bool
    stage: str
    code: str = "ok"
    message: str = ""
    warnings: list[str] = field(default_factory=list)
    redacted: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "stage": self.stage,
            "code": self.code,
            "message": self.message,
            "warnings": list(self.warnings),
            "redacted": self.redacted,
            "detail": dict(self.detail),
        }
