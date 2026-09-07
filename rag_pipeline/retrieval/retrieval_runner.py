from __future__ import annotations

from collections.abc import Sequence

from retrieval.graph import run_graph
from retrieval.step1_receive_question import validate_question


def answer_question(
    question: str,
    rerank: bool | None = None,
    hybrid: bool | None = None,
    retrieve_only: bool = False,
    allowed_classification_ids: Sequence[str] | None = None,
    user_id: str = "anonymous",
    conversation_id: str | None = None,
) -> dict:
    return run_graph(
        validate_question(question),
        rerank=rerank,
        hybrid=hybrid,
        retrieve_only=retrieve_only,
        allowed_classification_ids=allowed_classification_ids,
        user_id=user_id,
        conversation_id=conversation_id,
    )
