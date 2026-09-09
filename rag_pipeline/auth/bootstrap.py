from __future__ import annotations

from auth.permissions import grant_role
from auth.security import hash_password, verify_password
from config.db_connection import get_connection
from config.env_config import settings


def bootstrap_admin() -> None:
    """Create/update the env-provided admin without storing credentials in SQL."""
    if not settings.admin_password:
        return

    password_hash: str | None = None
    user_id = None
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM app_users WHERE LOWER(email) = %s FOR UPDATE",
            (settings.admin_email,),
        ).fetchone()
        if row is None:
            password_hash = hash_password(settings.admin_password)
            user_id = conn.execute(
                """
                INSERT INTO app_users (email, password_hash, display_name)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (settings.admin_email, password_hash, "Administrator"),
            ).fetchone()[0]
        else:
            user_id = row[0]
            if not verify_password(settings.admin_password, row[1]):
                password_hash = hash_password(settings.admin_password)
                conn.execute(
                    "UPDATE app_users SET password_hash = %s, updated_at = NOW() WHERE id = %s",
                    (password_hash, user_id),
                )
            conn.execute(
                "UPDATE app_users SET is_active = TRUE, updated_at = NOW() WHERE id = %s",
                (user_id,),
            )

    if settings.admin_role:
        grant_role(user_id, settings.admin_role)
