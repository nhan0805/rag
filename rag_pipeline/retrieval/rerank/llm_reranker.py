from __future__ import annotations

import json
import re

from config.env_config import settings
from retrieval.rerank.base import BaseReranker
from retrieval.step9_generate_answer import generate_answer
from shared.logger import logger


def _parse_scores(raw: str, expected_count: int) -> list[float] | None:
    candidate = raw.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*|\s*```$", "", candidate, flags=re.IGNORECASE)
    start = candidate.find("[")
    end = candidate.rfind("]")
    if start < 0 or end <= start:
        return None
    try:
        payload = json.loads(candidate[start : end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list) or len(payload) != expected_count:
        return None

    scores: list[float] = []
    for item in payload:
        if isinstance(item, dict):
            value = item.get("score")
        else:
            value = item
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        scores.append(float(value))
    return scores


class LLMReranker(BaseReranker):
    id = "llm"
    enabled = True

    def score(self, query: str, chunks: list[dict]) -> list[float]:
        if not chunks:
            return []
        numbered = "\n\n".join(
            f"[{index}] {chunk['content']}" for index, chunk in enumerate(chunks)
        )
        prompt = f"""Chấm mức độ liên quan của từng đoạn văn với câu hỏi.
Trả về DUY NHẤT một JSON array có đúng {len(chunks)} phần tử, theo đúng thứ tự,
mỗi phần tử có dạng {{"index": 0, "score": 0}}. Score là số từ 0 đến 10.
Không giải thích và không thêm markdown.

CÂU HỎI:
{query}

CÁC ĐOẠN:
{numbered}
"""
        try:
            raw = generate_answer(prompt)
            parsed = _parse_scores(raw, len(chunks))
            if parsed is not None:
                return parsed
            raise ValueError("JSON có hình dạng không đúng")
        except Exception as exc:
            # A malformed/failed LLM response must never take down chat. Using
            # vector scores preserves the pre-rerank order through stable sort.
            logger.warning("LLM reranker fallback to vector order: %s", exc)
            return [
                float(chunk.get("vector_score", chunk.get("similarity", 0.0)) or 0.0)
                for chunk in chunks
            ]

