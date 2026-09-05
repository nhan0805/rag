from __future__ import annotations

from retrieval.graph import run_graph
from retrieval.step1_receive_question import validate_question


def answer_question(
    question: str,
    rerank: bool | None = None,
    hybrid: bool | None = None,
    retrieve_only: bool = False,
) -> dict:
    return run_graph(
        validate_question(question),
        rerank=rerank,
        hybrid=hybrid,
        retrieve_only=retrieve_only,
    )
