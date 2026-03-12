from collections.abc import Callable

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.entities import RolePermission

ROLE_PERMISSIONS: dict[str, set[str]] = {
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


def get_security_context(
    x_role: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    role = (x_role or "owner").lower()
    if role not in ROLE_PERMISSIONS:
        role = "owner"

    db_permissions = {
        rp.permission_key
        for rp in db.query(RolePermission).filter(RolePermission.role_key == role).all()
    }
    permissions = db_permissions or ROLE_PERMISSIONS[role]

    return {"role": role, "permissions": sorted(permissions)}


def require_permission(permission: str) -> Callable:
    def dependency(context: dict = Depends(get_security_context)):
        if permission not in context["permissions"]:
            raise HTTPException(status_code=403, detail=f"Missing permission: {permission}")
        return context

    return dependency
