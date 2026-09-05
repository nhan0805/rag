from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedMarkdown:
    frontmatter: str
    body: str


_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


def split_frontmatter(text: str) -> ParsedMarkdown:
    """Split YAML-like frontmatter from Markdown without interpreting metadata.

    Metadata extraction is intentionally left for the next lab; this step only
    ensures frontmatter does not become part of the embedded body.
    """
    normalized = text.lstrip("\ufeff")
    match = _FRONTMATTER.match(normalized)
    if not match:
        return ParsedMarkdown(frontmatter="", body=normalized)
    return ParsedMarkdown(frontmatter=match.group(1).strip(), body=match.group(2))

