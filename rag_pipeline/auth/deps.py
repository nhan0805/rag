from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.permissions import classifications_for_user, roles_for_user
from auth.security import decode_access_token
from config.db_connection import get_connection


bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    email: str
    display_name: str | None
    roles: tuple[str, ...]
    classifications: tuple[dict[str, str], ...]
    classification_ids: tuple[str, ...]

    @property
    def user_id(self) -> str:
        return str(self.id)

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cần đăng nhập")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(str(payload["sub"]))
    except (ValueError, KeyError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc đã hết hạn",
        ) from exc

    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, display_name FROM app_users WHERE id = %s AND is_active",
            (user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tài khoản không hoạt động")

    classifications = classifications_for_user(user_id)
    roles = tuple(roles_for_user(user_id))
    return CurrentUser(
        id=row[0],
        email=row[1],
        display_name=row[2],
        roles=roles,
        classifications=tuple(classifications),
        classification_ids=tuple(item["id"] for item in classifications),
    )


def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cần quyền admin")
    return user
