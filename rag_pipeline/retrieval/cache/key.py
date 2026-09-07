from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable


def scope_key(
    allowed_classification_ids: Iterable[str] | None,
    rerank: bool,
    hybrid: bool,
) -> str:
    """Return a deterministic cache scope for permissions and retrieval config."""
    ids = sorted({str(value) for value in (allowed_classification_ids or [])})
    canonical = json.dumps(
        {"allowed_classification_ids": ids, "rerank": bool(rerank), "hybrid": bool(hybrid)},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
