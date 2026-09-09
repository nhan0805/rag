from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from config.db_connection import get_connection


def _uuid(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def classifications_for_user(user_id: UUID | str) -> list[dict[str, str]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT classification_id, classification_name
            FROM v_user_classifications
            WHERE user_id = %s
            ORDER BY classification_name
            """,
            (_uuid(user_id),),
        ).fetchall()
    return [{"id": str(row[0]), "name": row[1]} for row in rows]


def classification_ids_for_user(user_id: UUID | str) -> list[str]:
    return [item["id"] for item in classifications_for_user(user_id)]


def classification_id_by_name(name: str) -> UUID | None:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM rag_classifications WHERE UPPER(name) = UPPER(%s)",
            (name.strip(),),
        ).fetchone()
    return None if row is None else row[0]


def list_classifications() -> list[dict[str, str]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, COALESCE(description, '') FROM rag_classifications ORDER BY name"
        ).fetchall()
    return [{"id": str(row[0]), "name": row[1], "description": row[2]} for row in rows]


def grant_role(user_id: UUID | str, role_name: str) -> bool:
    user_uuid = _uuid(user_id)
    normalized = role_name.strip().lower()
    with get_connection() as conn:
        role = conn.execute(
            "SELECT id FROM rag_roles WHERE LOWER(name) = %s", (normalized,)
        ).fetchone()
        if role is None:
            raise ValueError(f"Unknown role: {role_name}")
        row = conn.execute(
            """
            INSERT INTO app_user_roles (user_id, role_id)
            SELECT %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM app_user_roles
                WHERE user_id = %s AND role_id = %s AND valid_to IS NULL
            )
            RETURNING id
            """,
            (user_uuid, role[0], user_uuid, role[0]),
        ).fetchone()
    return row is not None


def revoke_role(user_id: UUID | str, role_name: str) -> bool:
    normalized = role_name.strip().lower()
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE app_user_roles ur
               SET valid_to = NOW()
              FROM rag_roles r
             WHERE ur.role_id = r.id
               AND ur.user_id = %s
               AND LOWER(r.name) = %s
               AND ur.valid_to IS NULL
            """,
            (_uuid(user_id), normalized),
        )
    return cursor.rowcount > 0


def roles_for_user(user_id: UUID | str) -> list[str]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT r.name
            FROM app_user_roles ur
            JOIN rag_roles r ON r.id = ur.role_id
            WHERE ur.user_id = %s
              AND NOW() >= ur.valid_from
              AND (ur.valid_to IS NULL OR ur.valid_to > NOW())
            ORDER BY r.name
            """,
            (_uuid(user_id),),
        ).fetchall()
    return [row[0] for row in rows]


def has_classification(user_id: UUID | str, classification_id: UUID | str) -> bool:
    return str(classification_id) in set(classification_ids_for_user(user_id))
