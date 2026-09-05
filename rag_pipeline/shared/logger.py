import os
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("session4-rag")


def _logging_enabled() -> bool:
    return os.getenv("LLM_LOG_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _make_llm_file_logger() -> logging.Logger:
    file_logger = logging.getLogger("session4-rag.llm")
    file_logger.setLevel(logging.INFO)
    file_logger.propagate = False

    if not _logging_enabled():
        return file_logger

    log_path = Path(os.getenv("LLM_LOG_FILE", "logs/llm.log"))
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


llm_file_logger = _make_llm_file_logger()
