from __future__ import annotations

import re
import time
from typing import Any

import httpx

from config.env_config import settings
from shared.logger import llm_file_logger, logger


ENGLISH_SYSTEM_PROMPT = (
    "You are a truthful RAG assistant. Use only the provided context. "
    "The final answer MUST be entirely in English. Translate relevant "
    "Vietnamese facts into English and never copy Vietnamese sentences. "
    "Do not invent details. Return only the answer."
)

LLM_OPTIONS = {"temperature": 0.0, "num_predict": 256}

# Vietnamese-specific letters catch the accented text that the local model
# most often copies from Vietnamese source documents.
_VIETNAMESE_TEXT = re.compile(r"[ăâđêôơưĂÂĐÊÔƠƯ]")


def _answer_from_response(data: dict[str, Any]) -> str:
    message = data.get("message")
    if isinstance(message, dict) and isinstance(message.get("content"), str):
        return message["content"].strip()
    if isinstance(data.get("response"), str):
        return data["response"].strip()
    raise RuntimeError("Ollama response không có nội dung trả lời")


def contains_vietnamese(text: str) -> bool:
    """Return whether text contains common Vietnamese-specific characters."""
    return bool(_VIETNAMESE_TEXT.search(text))


def _logged_text(text: str) -> str:
    if settings.llm_log_full_content:
        return text
    limit = max(settings.llm_log_max_chars, 0)
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n... [truncated; {len(text) - limit} chars omitted]"


def _log_llm_exchange(
    stage: str,
    system_prompt: str,
    user_prompt: str,
    data: dict[str, Any],
    output: str,
    elapsed_seconds: float,
) -> None:
    """Log the exact model messages, output, and Ollama usage metadata."""
    if not settings.llm_log_enabled:
        return

    usage = {
        "prompt_tokens": data.get("prompt_eval_count"),
        "output_tokens": data.get("eval_count"),
        "total_duration_ms": _duration_ms(data.get("total_duration")),
        "load_duration_ms": _duration_ms(data.get("load_duration")),
        "prompt_eval_duration_ms": _duration_ms(
            data.get("prompt_eval_duration")
        ),
        "eval_duration_ms": _duration_ms(data.get("eval_duration")),
        "client_elapsed_ms": round(elapsed_seconds * 1000, 2),
    }
    message = (
        "LLM exchange [%s] INPUT (system + user):\n%s\n--- USER PROMPT ---\n%s\n"
        "LLM exchange [%s] OUTPUT:\n%s\nLLM exchange [%s] USAGE: %s"
        % (
            stage,
            _logged_text(system_prompt),
            _logged_text(user_prompt),
            stage,
            _logged_text(output),
            stage,
            usage,
        )
    )
    logger.info(
        "%s",
        message,
    )
    llm_file_logger.info(
        "%s",
        message,
    )


def _duration_ms(value: Any) -> float | None:
    """Convert Ollama nanosecond durations to milliseconds for readable logs."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value) / 1_000_000, 2)
    return None


def generate_answer(prompt: str) -> str:
    timeout = httpx.Timeout(settings.http_timeout_seconds)
    with httpx.Client(timeout=timeout) as client:
        system_prompt = ENGLISH_SYSTEM_PROMPT
        started = time.perf_counter()
        response = client.post(
            f"{settings.llm_url}/api/chat",
            json={
                "model": settings.llm_model,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
                "options": LLM_OPTIONS,
                "keep_alive": settings.ollama_keep_alive,
            },
        )
        response.raise_for_status()
        data = response.json()
        answer = _answer_from_response(data)
        _log_llm_exchange(
            "answer",
            system_prompt,
            prompt,
            data,
            answer,
            time.perf_counter() - started,
        )
        # Return the first model response directly so prompt behavior can be
        # tested without a second English-rewrite model call.
        return answer
