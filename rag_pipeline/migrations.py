from __future__ import annotations

import hashlib
from pathlib import Path

from config.db_connection import get_connection
from config.env_config import settings


SQL_PATH = Path(__file__).resolve().parent / "sql" / "init_rag_db.sql"
HYBRID_SQL_PATH = Path(__file__).resolve().parent / "sql" / "03_hybrid_search.sql"
MIGRATION_DIR = Path(__file__).resolve().parent / "sql"


def rendered_schema() -> str:
    sql = SQL_PATH.read_text(encoding="utf-8")
    hybrid_sql = HYBRID_SQL_PATH.read_text(encoding="utf-8")
    follow_up = "\n\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(MIGRATION_DIR.glob("[0-9][0-9]_*.sql"))
        if path.name not in {SQL_PATH.name, HYBRID_SQL_PATH.name}
    )
    return (
        sql.replace("{{EMBEDDING_DIM}}", str(settings.embedding_dim))
        + "\n\n"
        + hybrid_sql
        + "\n\n"
        + follow_up
    )


def run_migrations() -> bool:
    """Apply the schema when its rendered SHA-256 changes.

    The schema itself is idempotent, so rerunning after a change is safe for
    this teaching project. Returns True when SQL was executed.
    """
    sql = rendered_schema()
    checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rag_schema_migrations (
                id SMALLINT PRIMARY KEY CHECK (id = 1),
                checksum TEXT NOT NULL,
                applied_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
            """
        )
        row = conn.execute(
            "SELECT checksum FROM rag_schema_migrations WHERE id = 1"
        ).fetchone()
        if row and row[0] == checksum:
            return False

        conn.execute(sql)
        conn.execute(
            """
            INSERT INTO rag_schema_migrations (id, checksum)
            VALUES (1, %s)
            ON CONFLICT (id) DO UPDATE
            SET checksum = EXCLUDED.checksum, applied_at = NOW()
            """,
            (checksum,),
        )
    return True
