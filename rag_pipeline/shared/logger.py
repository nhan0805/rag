import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("session4-rag")


def _logging_enabled(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default).lower()).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _make_file_logger(
    logger_name: str,
    enabled_env: str,
    path_env: str,
    default_path: str,
    default_enabled: bool = False,
) -> logging.Logger:
    file_logger = logging.getLogger(logger_name)
    file_logger.setLevel(logging.INFO)
    file_logger.propagate = False

    if not _logging_enabled(enabled_env, default_enabled):
        return file_logger

    log_path = Path(os.getenv(path_env, default_path))
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s — %(message)s")
        )
        file_logger.addHandler(handler)
    except OSError as exc:
        logger.warning("Không thể mở LLM log file %s: %s", log_path, exc)
    return file_logger


llm_file_logger = _make_file_logger(
    "session4-rag.llm",
    "LLM_LOG_ENABLED",
    "LLM_LOG_FILE",
    "logs/llm.log",
)
guardrail_file_logger = _make_file_logger(
    "session4-rag.guardrail",
    "GUARDRAIL_LOG_ENABLED",
    "GUARDRAIL_LOG_FILE",
    "logs/guardrail.log",
    default_enabled=True,
)
