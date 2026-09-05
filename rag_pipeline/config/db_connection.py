from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Iterator

import psycopg

from config.env_config import settings
from shared.logger import logger


@contextmanager
def get_connection() -> Iterator[psycopg.Connection]:
    conn = psycopg.connect(settings.database_url)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def wait_for_database(retries: int = 30, delay_seconds: float = 2.0) -> None:
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            with get_connection():
                pass
            return
        except psycopg.Error as exc:
            last_error = exc
            logger.info("Waiting for PostgreSQL (%s/%s)", attempt, retries)
            if attempt < retries:
                time.sleep(delay_seconds)
    raise RuntimeError("PostgreSQL did not become ready") from last_error

