from __future__ import annotations

from shared.md_frontmatter import ParsedMarkdown, split_frontmatter


def parse_document(text: str) -> ParsedMarkdown:
    return split_frontmatter(text)

