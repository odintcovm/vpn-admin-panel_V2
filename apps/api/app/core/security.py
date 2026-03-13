import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import FrozenSet

from fastapi import Depends, Header, HTTPException, status
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


@dataclass(frozen=True)
class SecurityPrincipal:
    subject_id: str
    role: str
    permissions: FrozenSet[str]
    token_fingerprint: str
    auth_mode: str
    user_id: int | None


@dataclass(frozen=True)
class LoginResult:
    session_subject: str
    user_id: int
    role: str



def _error(status_code: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"error": {"code": code, "message": message}})


def _token_fingerprint(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()[:16]


def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)


def verify_password(raw_password: str, stored_hash: str) -> bool:
    try:
        return pwd_context.verify(raw_password, stored_hash)
    except Exception:
        return False


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


def _principal_from_session(db: Session, session_subject: str) -> SecurityPrincipal | None:
    record = db.query(AuthSession).filter(AuthSession.subject == session_subject).first()
    if not record:
        return None
    if record.revoked_at is not None:
        return None
    if record.expires_at and record.expires_at < datetime.utcnow():
        return None

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user or not user.is_active:
        return None

    user.last_seen_at = datetime.utcnow()
    db.commit()

    role = user.role_key if user.role_key in VALID_ROLES else "readonly"
    return SecurityPrincipal(
        subject_id=record.subject,
        role=role,
        permissions=frozenset(ROLE_PERMISSION_MAP.get(role, ROLE_PERMISSION_MAP["readonly"])),
        token_fingerprint="",
        auth_mode="session",
        user_id=user.id,
    )


def _cookie_value(raw_cookie: str | None, cookie_name: str) -> str | None:
    if not raw_cookie:
        return None
    for part in raw_cookie.split(';'):
        part = part.strip()
        if part.startswith(f"{cookie_name}="):
            return part.split('=', 1)[1]
    return None


def get_current_principal(
    x_api_token: str = Header(default=None, alias="x-api-token"),
    x_role: str | None = Header(default=None, alias="x-role"),
    cookie_header: str | None = Header(default=None, alias="cookie"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> SecurityPrincipal:
    session_cookie = _cookie_value(cookie_header, settings.auth_cookie_name)
    if settings.auth_enabled and session_cookie:
        principal = _principal_from_session(db, session_cookie)
        if principal:
            return principal

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

    raise _error(status.HTTP_401_UNAUTHORIZED, "AUTH_REQUIRED", "Login or API token is required")


def require_permission(permission_key: str):
    def dependency(principal: SecurityPrincipal = Depends(get_current_principal)) -> SecurityPrincipal:
        if permission_key not in principal.permissions:
            raise _error(status.HTTP_403_FORBIDDEN, "PERMISSION_DENIED", f"Missing permission: {permission_key}")
        return principal

    return dependency


def authenticate_admin(db: Session, username: str, password: str, settings: Settings) -> LoginResult:
    if username != settings.admin_username:
        raise _error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Неверный логин или пароль")

    if settings.admin_password_hash:
        if not verify_password(password, settings.admin_password_hash):
            raise _error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Неверный логин или пароль")
    else:
        if password != settings.admin_password:
            raise _error(status.HTTP_401_UNAUTHORIZED, "INVALID_CREDENTIALS", "Неверный логин или пароль")

    user = db.query(User).filter(User.username == settings.admin_username, User.auth_source == "local").first()
    if not user:
        user = User(
            username=settings.admin_username,
            role_key="owner",
            auth_source="local",
            token_fingerprint=None,
            is_active=True,
            created_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()

    subject = f"session:{secrets.token_urlsafe(24)}"
    ttl = timedelta(hours=max(1, settings.auth_session_ttl_hours))
    session = AuthSession(
        user_id=user.id,
        subject=subject,
        session_type="cookie",
        issued_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + ttl,
        revoked_at=None,
    )
    db.add(session)
    user.last_seen_at = datetime.utcnow()
    db.commit()
    return LoginResult(session_subject=subject, user_id=user.id, role=user.role_key)


def revoke_session(db: Session, session_subject: str | None) -> None:
    if not session_subject:
        return
    session = db.query(AuthSession).filter(AuthSession.subject == session_subject).first()
    if not session or session.revoked_at:
        return
    session.revoked_at = datetime.utcnow()
    db.commit()


def get_optional_principal(
    x_api_token: str = Header(default=None, alias="x-api-token"),
    x_role: str | None = Header(default=None, alias="x-role"),
    cookie_header: str | None = Header(default=None, alias="cookie"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> SecurityPrincipal | None:
    try:
        return get_current_principal(
            x_api_token=x_api_token,
            x_role=x_role,
            cookie_header=cookie_header,
            settings=settings,
            db=db,
        )
    except HTTPException:
        return None
