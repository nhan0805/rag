from __future__ import annotations

import re


# These words occur in almost every natural-language question and make the
# lexical branch noisier without helping it find an exact ID or code.
QUESTION_WORDS = frozenset(
    {
        "a",
        "about",
        "are",
        "bao",
        "can",
        "could",
        "do",
        "does",
        "how",
        "is",
        "nào",
        "nhiêu",
        "phải",
        "should",
        "the",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "would",
    }
)


def extract_terms(question: str) -> list[str]:
    """Extract stable lexical terms from a question.

    Hyphens, dots, and underscores are intentionally retained so identifiers
    such as ``ERR-6002``, ``1.2.3``, and ``fill_and_advance`` remain usable by
    PostgreSQL's ``simple`` text-search configuration. Every other separator
    becomes a space; removing it would incorrectly join two meaningful terms
    (for example, ``fetch_k=20`` -> ``fetch_k20``).
    """
    if not isinstance(question, str):
        return []

    separated = re.sub(r"[^\w\-.]", " ", question)
    terms: list[str] = []
    seen: set[str] = set()
    for raw_term in separated.lower().split():
        if len(raw_term) < 2 or raw_term in QUESTION_WORDS:
            continue
        # A token consisting only of punctuation is not a useful tsquery term.
        if not any(character.isalnum() for character in raw_term):
            continue
        if raw_term not in seen:
            seen.add(raw_term)
            terms.append(raw_term)
    return terms


def build_tsquery(question: str) -> str:
    """Build an OR-connected PostgreSQL tsquery expression.

    An empty string means the lexical branch should be skipped. Passing an
    empty string to ``to_tsquery`` would be a syntax error, while an empty
    result is a normal no-match outcome for hybrid retrieval.
    """
    return " | ".join(extract_terms(question))
