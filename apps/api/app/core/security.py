import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import FrozenSet

from fastapi import Cookie, Depends, Header, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.database import get_db
from app.models.entities import AuthSession, User

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
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SESSION_COOKIE = "vpn_admin_session"


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


def _resolve_role(settings: Settings, x_role: str | None, default_role: str = "owner") -> str:
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


def verify_admin_password(settings: Settings, username: str, password: str) -> bool:
    if username != settings.admin_username:
        return False
    if settings.admin_password_hash:
        return pwd_context.verify(password, settings.admin_password_hash)
    # fallback for local/bootstrap usage
    return secrets.compare_digest(password, settings.admin_password)


def create_password_session(db: Session, settings: Settings, username: str) -> tuple[str, User]:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            username=username,
            role_key="owner",
            auth_source="password",
            token_fingerprint=None,
            is_active=True,
            created_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()

    user.last_seen_at = datetime.utcnow()
    session_secret = secrets.token_urlsafe(32)
    subject = f"session:{hashlib.sha256(session_secret.encode()).hexdigest()[:24]}:{user.role_key}"
    db.add(
        AuthSession(
            user_id=user.id,
            subject=subject,
            session_type="password",
            issued_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=settings.auth_session_ttl_hours),
            revoked_at=None,
        )
    )
    db.commit()
    return session_secret, user


def revoke_password_session(db: Session, session_secret: str | None) -> None:
    if not session_secret:
        return
    prefix = hashlib.sha256(session_secret.encode()).hexdigest()[:24]
    session = db.query(AuthSession).filter(AuthSession.subject.like(f"session:{prefix}:%"), AuthSession.revoked_at.is_(None)).first()
    if session:
        session.revoked_at = datetime.utcnow()
        db.commit()


def _principal_from_password_session(db: Session, session_secret: str) -> SecurityPrincipal | None:
    prefix = hashlib.sha256(session_secret.encode()).hexdigest()[:24]
    session = (
        db.query(AuthSession)
        .join(User, User.id == AuthSession.user_id)
        .filter(AuthSession.subject.like(f"session:{prefix}:%"), AuthSession.revoked_at.is_(None), User.is_active.is_(True))
        .first()
    )
    if not session:
        return None
    if session.expires_at and session.expires_at < datetime.utcnow():
        session.revoked_at = datetime.utcnow()
        db.commit()
        return None
    role = session.user.role_key if session.user.role_key in VALID_ROLES else "owner"
    session.user.last_seen_at = datetime.utcnow()
    db.commit()
    return SecurityPrincipal(
        subject_id=session.subject,
        role=role,
        permissions=frozenset(ROLE_PERMISSION_MAP[role]),
        token_fingerprint=prefix,
        auth_mode="session",
        user_id=session.user.id,
    )


def get_current_principal(
    x_api_token: str | None = Header(default=None, alias="x-api-token"),
    x_role: str | None = Header(default=None, alias="x-role"),
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> SecurityPrincipal:
    if x_api_token:
        if x_api_token != settings.api_token:
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

    if session_cookie:
        principal = _principal_from_password_session(db, session_cookie)
        if principal:
            return principal

    raise _error(status.HTTP_401_UNAUTHORIZED, "AUTH_REQUIRED", "Authentication is required")


def require_permission(permission_key: str):
    def dependency(principal: SecurityPrincipal = Depends(get_current_principal)) -> SecurityPrincipal:
        if permission_key not in principal.permissions:
            raise _error(status.HTTP_403_FORBIDDEN, "PERMISSION_DENIED", f"Missing permission: {permission_key}")
        return principal

    return dependency
