"""Hybrid retrieval helpers: lexical search and reciprocal-rank fusion."""

from retrieval.hybrid.fusion import reciprocal_rank_fusion
from retrieval.hybrid.query_builder import build_tsquery, extract_terms

__all__ = [
    "build_tsquery",
    "extract_terms",
    "lexical_search",
    "reciprocal_rank_fusion",
]


def __getattr__(name: str):
    # Keep query-builder/fusion unit tests independent of the database driver.
    if name == "lexical_search":
        from retrieval.hybrid.lexical import lexical_search

        return lexical_search
    raise AttributeError(name)
