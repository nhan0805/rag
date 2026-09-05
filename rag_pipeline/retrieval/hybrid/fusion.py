from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def _retriever_name(items: Sequence[dict[str, Any]], index: int) -> str:
    if items:
        sample = items[0]
        if "lexical_score" in sample or "lexical_rank" in sample:
            return "lexical"
        if "vector_score" in sample or "vector_rank" in sample:
            return "vector"
    if index == 0:
        return "vector"
    if index == 1:
        return "lexical"
    return f"retriever_{index + 1}"


def _normalise_lists(
    ranked_lists: Mapping[str, Sequence[dict[str, Any]]]
    | Sequence[Sequence[dict[str, Any]]],
) -> list[tuple[str, Sequence[dict[str, Any]]]]:
    if isinstance(ranked_lists, Mapping):
        return [(str(name), values) for name, values in ranked_lists.items()]
    return [
        (name, values)
        for index, values in enumerate(ranked_lists)
        for name in [_retriever_name(values, index)]
    ]


def reciprocal_rank_fusion(
    ranked_lists: Mapping[str, Sequence[dict[str, Any]]]
    | Sequence[Sequence[dict[str, Any]]],
    k: int = 60,
    key: str = "chunk_id",
) -> list[dict]:
    """Fuse pre-ranked result lists using reciprocal rank fusion.

    The input lists and their dictionaries are never mutated. A chunk found
    by multiple retrievers keeps the union of its fields and records the
    retrievers in ``found_by``.
    """
    if k <= 0:
        raise ValueError("k must be positive")

    merged: dict[Any, dict[str, Any]] = {}
    rrf_scores: dict[Any, float] = {}
    found_by: dict[Any, list[str]] = {}
    first_seen: dict[Any, int] = {}
    seen_order = 0

    for retriever, ranked in _normalise_lists(ranked_lists):
        for rank, raw_item in enumerate(ranked, start=1):
            item = dict(raw_item)
            identity = item.get(key)
            if identity is None and key == "chunk_id" and item.get("id") is not None:
                identity = str(item["id"])
                item[key] = identity
            if identity is None:
                raise ValueError(f"every result must contain {key!r}")

            if identity not in merged:
                merged[identity] = item
                found_by[identity] = []
                first_seen[identity] = seen_order
                seen_order += 1
            else:
                # Keep the first value when two retrievers expose the same
                # field, but fill every field that was absent/null before.
                current = merged[identity]
                for field, value in item.items():
                    if field not in current or current[field] is None:
                        current[field] = value

            if retriever not in found_by[identity]:
                found_by[identity].append(retriever)
            rrf_scores[identity] = rrf_scores.get(identity, 0.0) + 1 / (k + rank)

    ranked_items = sorted(
        merged.items(),
        key=lambda pair: (-rrf_scores[pair[0]], first_seen[pair[0]]),
    )
    result: list[dict] = []
    for rank, (identity, item) in enumerate(ranked_items, start=1):
        output = dict(item)
        output["rrf_score"] = float(rrf_scores[identity])
        output["rrf_rank"] = rank
        output["score"] = output["rrf_score"]
        output["found_by"] = list(found_by[identity])
        result.append(output)
    return result


# Descriptive aliases keep the small module convenient for graph nodes and
# callers that use the shorter name from the lab diagram.
fuse_results = reciprocal_rank_fusion
rrf_fuse = reciprocal_rank_fusion
