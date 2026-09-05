from __future__ import annotations

from typing import Any

import httpx

from config.env_config import settings


def _embedding_from_response(data: dict[str, Any]) -> list[float]:
    if isinstance(data.get("embedding"), list):
        return [float(value) for value in data["embedding"]]
    embeddings = data.get("embeddings")
    if isinstance(embeddings, list) and embeddings and isinstance(embeddings[0], list):
        return [float(value) for value in embeddings[0]]
    raise RuntimeError(f"Ollama response không có embedding: {data.keys()}")


def embed_text(text: str) -> list[float]:
    """Call Ollama's embeddings endpoint, with compatibility for /api/embed."""
    timeout = httpx.Timeout(settings.http_timeout_seconds)
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            f"{settings.embedding_url}/api/embeddings",
            json={
                "model": settings.embedding_model,
                "prompt": text,
                "keep_alive": settings.ollama_keep_alive,
            },
        )
        if response.status_code == 404:
            response = client.post(
                f"{settings.embedding_url}/api/embed",
                json={
                    "model": settings.embedding_model,
                    "input": text,
                    "keep_alive": settings.ollama_keep_alive,
                },
            )
        response.raise_for_status()
        vector = _embedding_from_response(response.json())

    if len(vector) != settings.embedding_dim:
        raise RuntimeError(
            f"Embedding dimension mismatch: expected {settings.embedding_dim}, got {len(vector)}"
        )
    return vector
