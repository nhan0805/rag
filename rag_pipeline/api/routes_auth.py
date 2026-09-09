from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator

from auth.deps import CurrentUser, get_current_user, require_admin
from auth.permissions import grant_role, revoke_role
from auth.security import create_access_token, hash_password, verify_password
from config.db_connection import get_connection
from config.env_config import settings


router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("Email không hợp lệ")
        return normalized


class RegisterRequest(Credentials):
    display_name: str | None = Field(default=None, max_length=120)


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    roles: list[str]
    classifications: list[dict[str, str]]


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class AdminUserResponse(BaseModel):
    id: str
    email: str
    display_name: str | None
    is_active: bool
    roles: list[str]


class SetRoleRequest(BaseModel):
    role: str = Field(min_length=1, max_length=32)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"staff", "manager"}:
            raise ValueError("Role được phép đặt từ UI: staff hoặc manager")
        return normalized


def _response(user: CurrentUser) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        roles=list(user.roles),
        classifications=list(user.classifications),
    )


def _load_user(user_id: UUID) -> CurrentUser:
    # Reuse the same dependency behavior after registration/login without
    # manufacturing a token or putting permissions into one.
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, display_name FROM app_users WHERE id = %s AND is_active",
            (user_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Tài khoản không hoạt động")
    from auth.permissions import classifications_for_user, roles_for_user

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


@router.post("/register", response_model=AuthResponse)
def register(request: RegisterRequest) -> AuthResponse:
    email = str(request.email).strip().lower()
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM app_users WHERE LOWER(email) = %s", (email,)
        ).fetchone()
        if exists is not None:
            raise HTTPException(status_code=409, detail="Email đã được đăng ký")
        user_id = conn.execute(
            """
            INSERT INTO app_users (email, password_hash, display_name)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (email, hash_password(request.password), request.display_name),
        ).fetchone()[0]
    if settings.default_role:
        try:
            grant_role(user_id, settings.default_role)
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
    user = _load_user(user_id)
    return AuthResponse(access_token=create_access_token(user.id, user.email), user=_response(user))


@router.post("/login", response_model=AuthResponse)
def login(request: Credentials) -> AuthResponse:
    email = str(request.email).strip().lower()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, password_hash FROM app_users WHERE LOWER(email) = %s AND is_active",
            (email,),
        ).fetchone()
    if row is None or not verify_password(request.password, row[1]):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    user = _load_user(row[0])
    return AuthResponse(access_token=create_access_token(user.id, user.email), user=_response(user))


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser = Depends(get_current_user)) -> UserResponse:
    return _response(user)


@router.get("/users", response_model=list[AdminUserResponse])
def list_users(_: CurrentUser = Depends(require_admin)) -> list[AdminUserResponse]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                u.id,
                u.email,
                u.display_name,
                u.is_active,
                COALESCE(
                    array_agg(r.name ORDER BY r.name)
                    FILTER (WHERE r.name IS NOT NULL),
                    ARRAY[]::text[]
                ) AS roles
            FROM app_users u
            LEFT JOIN app_user_roles ur
              ON ur.user_id = u.id
             AND NOW() >= ur.valid_from
             AND (ur.valid_to IS NULL OR ur.valid_to > NOW())
            LEFT JOIN rag_roles r ON r.id = ur.role_id
            GROUP BY u.id, u.email, u.display_name, u.is_active
            ORDER BY LOWER(u.email)
            """
        ).fetchall()
    return [
        AdminUserResponse(
            id=str(row[0]),
            email=row[1],
            display_name=row[2],
            is_active=row[3],
            roles=list(row[4] or []),
        )
        for row in rows
    ]


@router.put("/users/{user_id}/role")
def set_role(
    user_id: UUID,
    request: SetRoleRequest,
    _: CurrentUser = Depends(require_admin),
) -> dict[str, object]:
    with get_connection() as conn:
        exists = conn.execute(
            "SELECT 1 FROM app_users WHERE id = %s",
            (user_id,),
        ).fetchone()
    if exists is None:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")

    # The admin page exposes staff/manager as a mutually exclusive choice.
    # Existing admin access is intentionally preserved.
    revoke_role(user_id, "staff")
    revoke_role(user_id, "manager")
    try:
        changed = grant_role(user_id, request.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user_id": str(user_id), "role": request.role, "changed": changed}


@router.post("/users/{user_id}/roles/{role_name}")
def add_role(
    user_id: UUID,
    role_name: str,
    _: CurrentUser = Depends(require_admin),
) -> dict[str, object]:
    try:
        changed = grant_role(user_id, role_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"user_id": str(user_id), "role": role_name, "granted": changed}


@router.delete("/users/{user_id}/roles/{role_name}")
def remove_role(
    user_id: UUID,
    role_name: str,
    _: CurrentUser = Depends(require_admin),
) -> dict[str, object]:
    return {"user_id": str(user_id), "role": role_name, "revoked": revoke_role(user_id, role_name)}
