import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import FrozenSet

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.database import get_db
from app.models.entities import User

ROLE_PERMISSION_MAP = {
    "owner": {
        "dashboard.read",
        "links.read",
        "links.write",
        "links.delete",
        "links.regenerate",
        "clients.read",
        "clients.mark_suspicious",
        "sessions.read",
        "server.read",
        "server.reload",
        "server.restart",
        "server.validate",
        "audit.read",
        "audit.export",
        "notifications.read",
        "alerts.read",
        "alerts.write",
        "settings.read",
        "settings.write",
        "roles.manage",
    },
    "admin": {
        "dashboard.read",
        "links.read",
        "links.write",
        "links.delete",
        "links.regenerate",
        "clients.read",
        "clients.mark_suspicious",
        "sessions.read",
        "server.read",
        "server.reload",
        "server.restart",
        "server.validate",
        "audit.read",
        "audit.export",
        "notifications.read",
        "alerts.read",
        "alerts.write",
        "settings.read",
        "settings.write",
    },
    "operator": {
        "dashboard.read",
        "links.read",
        "links.write",
        "links.regenerate",
        "clients.read",
        "clients.mark_suspicious",
        "sessions.read",
        "server.read",
        "audit.read",
        "notifications.read",
        "alerts.read",
        "settings.read",
    },
    "readonly": {
        "dashboard.read",
        "links.read",
        "clients.read",
        "sessions.read",
        "server.read",
        "audit.read",
        "notifications.read",
        "alerts.read",
        "settings.read",
    },
}

VALID_ROLES = set(ROLE_PERMISSION_MAP.keys())


@dataclass(frozen=True)
class SecurityPrincipal:
    subject_id: str
    role: str
    permissions: FrozenSet[str]
    token_fingerprint: str
    auth_mode: str
    user_id: int | None


def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": {"code": code, "message": message}})


def _token_fingerprint(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()[:16]


def _resolve_role(settings: Settings, x_role: str | None) -> str:
    default_role = "owner"
    if not x_role:
        return default_role

    if x_role not in VALID_ROLES:
        raise _error(status.HTTP_400_BAD_REQUEST, "INVALID_ROLE", f"Unsupported role override: {x_role}")

    if not settings.dev_role_emulation or not settings.is_dev_like:
        raise _error(
            status.HTTP_403_FORBIDDEN,
            "DEV_ROLE_EMULATION_DISABLED",
            "x-role override is disabled outside explicit development/test mode",
        )
    return x_role


def _resolve_or_create_token_user(db: Session, token_fingerprint: str, role: str) -> User | None:
    user = db.query(User).filter(User.token_fingerprint == token_fingerprint).first()
    if user:
        if user.role_key != role:
            user.role_key = role
        user.last_seen_at = datetime.utcnow()
        db.commit()
        return user

    user = User(
        username=f"token-admin-{token_fingerprint}",
        role_key=role,
        auth_source="token",
        token_fingerprint=token_fingerprint,
        is_active=True,
        created_at=datetime.utcnow(),
        last_seen_at=datetime.utcnow(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_principal(
    x_api_token: str = Header(default=None, alias="x-api-token"),
    x_role: str | None = Header(default=None, alias="x-role"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> SecurityPrincipal:
    if not x_api_token or x_api_token != settings.api_token:
        raise _error(status.HTTP_401_UNAUTHORIZED, "INVALID_API_TOKEN", "Missing or invalid x-api-token")

    role = _resolve_role(settings, x_role)
    fingerprint = _token_fingerprint(x_api_token)
    user = _resolve_or_create_token_user(db, fingerprint, role)

    subject_id = f"token:{fingerprint}:{role}"
    return SecurityPrincipal(
        subject_id=subject_id,
        role=role,
        permissions=frozenset(ROLE_PERMISSION_MAP[role]),
        token_fingerprint=fingerprint,
        auth_mode="token",
        user_id=user.id if user else None,
    )


def require_permission(permission_key: str):
    def dependency(principal: SecurityPrincipal = Depends(get_current_principal)) -> SecurityPrincipal:
        if permission_key not in principal.permissions:
            raise _error(status.HTTP_403_FORBIDDEN, "PERMISSION_DENIED", f"Missing permission: {permission_key}")
        return principal

    return dependency
