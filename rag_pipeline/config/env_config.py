from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# Docker injects env_file values. This also makes local `python main.py`
# convenient when it is launched from the session4-rag directory.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {value!r}") from exc


def _float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc


def _optional_float(name: str, default: float | None = None) -> float | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number or empty, got {value!r}") from exc


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean, got {value!r}")


@dataclass(frozen=True)
class Settings:
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = _int("POSTGRES_HOST_PORT", 6024)
    postgres_user: str = os.getenv("POSTGRES_USER", "ai_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "ai_pass")
    postgres_db: str = os.getenv("POSTGRES_DB", "ai_db")

    embedding_dim: int = _int("EMBEDDING_DIM", 768)
    embedding_host: str = os.getenv("OLLAMA_NOMIC_EMBED_TEXT_HOST", "localhost")
    embedding_port: int = _int("OLLAMA_NOMIC_EMBED_TEXT_HOST_PORT", 11437)
    embedding_model: str = os.getenv(
        "OLLAMA_NOMIC_EMBED_TEXT_MODEL", "nomic-embed-text"
    )

    llm_host: str = os.getenv("OLLAMA_LLAMA31_HOST", "localhost")
    llm_port: int = _int("OLLAMA_LLAMA31_HOST_PORT", 11436)
    llm_model: str = os.getenv("OLLAMA_LLAMA31_MODEL", "llama3.2:3b")
    ollama_keep_alive: str = os.getenv("OLLAMA_KEEP_ALIVE", "10m")

    chunk_size: int = _int("CHUNK_SIZE", 800)
    chunk_overlap: int = _int("CHUNK_OVERLAP", 120)
    top_k: int = _int("TOP_K", 4)
    retrieve_fetch_k: int = _int("RETRIEVE_FETCH_K", 20)
    similarity_threshold: float = _float("SIMILARITY_THRESHOLD", 0.0)
    hybrid_enabled: bool = _bool("HYBRID_ENABLED", False)
    lexical_fetch_k: int = _int("LEXICAL_FETCH_K", 20)
    rrf_k: int = _int("RRF_K", 60)
    text_search_config: str = os.getenv("TEXT_SEARCH_CONFIG", "simple")
    rerank_enabled: bool = _bool("RERANK_ENABLED", False)
    rerank_backend: str = os.getenv("RERANK_BACKEND", "cross_encoder")
    rerank_model: str = os.getenv(
        "RERANK_MODEL", "ms-marco-MiniLM-L-12-v2"
    )
    rerank_top_n: int = _int("RERANK_TOP_N", 4)
    rerank_min_score: float | None = _optional_float("RERANK_MIN_SCORE")
    rerank_cache_dir: str = os.getenv("RERANK_CACHE_DIR", "/opt/rerank-cache")
    max_context_chars: int = _int("MAX_CONTEXT_CHARS", 14000)
    http_timeout_seconds: float = _float("HTTP_TIMEOUT_SECONDS", 180.0)
    llm_log_enabled: bool = _bool("LLM_LOG_ENABLED", False)
    llm_log_full_content: bool = _bool("LLM_LOG_FULL_CONTENT", False)
    llm_log_max_chars: int = _int("LLM_LOG_MAX_CHARS", 16000)
    app_port: int = _int("APP_PORT", 8000)
    input_dir: str = os.getenv("INPUT_DIR", str(Path(__file__).resolve().parents[2] / "input"))

    # Guardrails are calibrated against the active corpus.  The vector score
    # is intentionally optional because vector, RRF, and reranker scores do
    # not share a scale.
    guard_max_question_chars: int = _int("GUARD_MAX_QUESTION_CHARS", 4000)
    # FlashRank's score scale for this corpus is much lower than the generic
    # calibration example in the lab handout.  Measured valid questions span
    # roughly 0.044–0.998, so 0.03 keeps the ERR-7315 case answerable while
    # still rejecting the lowest-confidence database-destruction trap.
    guard_min_rerank_score: float | None = _optional_float(
        "GUARD_MIN_RERANK_SCORE", 0.03
    )
    guard_min_vector_score: float | None = _optional_float(
        "GUARD_MIN_VECTOR_SCORE", None
    )
    guard_output_action: str = os.getenv("GUARD_OUTPUT_ACTION", "warn").strip().lower()

    cache_enabled: bool = _bool("CACHE_ENABLED", True)
    cache_min_similarity: float = _float("CACHE_MIN_SIMILARITY", 0.97)
    cache_ttl_hours: int = _int("CACHE_TTL_HOURS", 24)

    memory_enabled: bool = _bool("MEMORY_ENABLED", True)
    memory_turns: int = _int("MEMORY_TURNS", 6)

    # Authentication and authorization.  Roles/classifications are resolved
    # from PostgreSQL on every request; they are deliberately not embedded in
    # the JWT so a revoke takes effect immediately.
    jwt_secret: str = os.getenv("JWT_SECRET", "local-rag-development-secret")
    jwt_expires_min: int = _int("JWT_EXPIRES_MIN", 720)
    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@rag.local").strip().lower()
    admin_password: str = os.getenv("ADMIN_PASSWORD", "")
    admin_role: str = os.getenv("ADMIN_ROLE", "admin").strip().lower()
    default_role: str = os.getenv("DEFAULT_ROLE", "").strip().lower()
    default_classification: str = os.getenv("DEFAULT_CLASSIFICATION", "A").strip().upper()
    qa_aware_chunking: bool = _bool("QA_AWARE_CHUNKING", False)

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def embedding_url(self) -> str:
        return f"http://{self.embedding_host}:{self.embedding_port}"

    @property
    def llm_url(self) -> str:
        return f"http://{self.llm_host}:{self.llm_port}"


settings = Settings()
