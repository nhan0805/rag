from __future__ import annotations

import time

import uvicorn

from api.main import app
from config.db_connection import wait_for_database
from config.env_config import settings
from auth.bootstrap import bootstrap_admin
from migrations import run_migrations
from shared.logger import logger


def bootstrap() -> None:
    """Wait for PostgreSQL and apply the idempotent schema before serving HTTP."""
    wait_for_database()
    changed = run_migrations()
    bootstrap_admin()
    logger.info("Database ready; migrations_changed=%s", changed)


if __name__ == "__main__":
    bootstrap()
    uvicorn.run(app, host="0.0.0.0", port=settings.app_port, log_level="info")
