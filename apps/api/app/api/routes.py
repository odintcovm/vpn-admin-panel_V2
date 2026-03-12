import itertools
import json
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import SecurityPrincipal, get_current_principal, require_permission
from app.db.database import get_db
from app.models.entities import AdminActionLog, ServerStatus, SessionRecord, SystemEvent, UserLink
from app.schemas.api import (
    ActionLogOut,
    AuthMeOut,
    ClientOut,
    DashboardOverview,
    EventOut,
    LinkCreate,
    LinkOut,
    LinkUpdate,
    NotificationOut,
    ServerStatusOut,
    SessionOut,
)
from app.services import services
from app.services.services import ClientService, LinkService, LogService, ProviderFactory, StatsService

router = APIRouter(prefix="/api")


def _not_found(code: str, message: str):
    raise HTTPException(status_code=404, detail={"error": {"code": code, "message": message}})


def to_link_out(item: dict) -> LinkOut:
    return LinkOut(**item)


@router.get("/auth/me", response_model=AuthMeOut)
def auth_me(principal: SecurityPrincipal = Depends(get_current_principal)):
    settings = get_settings()
    return AuthMeOut(
        subject_id=principal.subject_id,
        role=principal.role,
        permissions=sorted(principal.permissions),
        auth_mode=principal.auth_mode,
        user_id=principal.user_id,
        dev_role_emulation_enabled=settings.dev_role_emulation and settings.is_dev_like,
    )


@router.get("/dashboard/overview", response_model=DashboardOverview)
def get_overview(db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("dashboard.read"))):
    adapter = ProviderFactory.get(get_settings().app_provider)
    return StatsService(db, adapter).overview()


@router.get("/links", response_model=list[LinkOut])
def list_links(db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("links.read"))):
    return [to_link_out(i) for i in LinkService(db).list_links()]


@router.post("/links", response_model=LinkOut)
def create_link(payload: LinkCreate, db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("links.write"))):
    link = LinkService(db).create(payload.model_dump())
    fresh = next((x for x in LinkService(db).list_links() if x["id"] == link.id), None)
    if not fresh:
        raise HTTPException(status_code=500, detail={"error": {"code": "LINK_CREATE_FAILED", "message": "Created link not found"}})
    return to_link_out(fresh)


@router.patch("/links/{link_id}", response_model=LinkOut)
def patch_link(link_id: int, payload: LinkUpdate, db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("links.write"))):
    link = db.query(UserLink).filter(UserLink.id == link_id).first()
    if not link:
        _not_found("LINK_NOT_FOUND", "Link not found")
    LinkService(db).patch(link, payload.model_dump(exclude_unset=True))
    fresh = next((x for x in LinkService(db).list_links() if x["id"] == link_id), None)
    return to_link_out(fresh)


@router.delete("/links/{link_id}")
def delete_link(link_id: int, db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("links.delete"))):
    link = db.query(UserLink).filter(UserLink.id == link_id).first()
    if not link:
        _not_found("LINK_NOT_FOUND", "Link not found")
    LinkService(db).delete(link)
    return {"ok": True}


@router.post("/links/{link_id}/regenerate", response_model=LinkOut)
def regenerate_link(link_id: int, db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("links.regenerate"))):
    link = db.query(UserLink).filter(UserLink.id == link_id).first()
    if not link:
        _not_found("LINK_NOT_FOUND", "Link not found")
    LinkService(db).regenerate(link)
    fresh = next((x for x in LinkService(db).list_links() if x["id"] == link_id), None)
    return to_link_out(fresh)


@router.get("/links/{link_id}/qr")
def get_qr(link_id: int, db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("links.read"))):
    data = next((x for x in LinkService(db).list_links() if x["id"] == link_id), None)
    if not data:
        _not_found("LINK_NOT_FOUND", "Link not found")
    return {"qr_payload": data["vless_url"], "hint": "Use this string in a QR generator", "link_name": data["name"]}


@router.get("/clients", response_model=list[ClientOut])
def clients(db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("clients.read"))):
    return ClientService(db).list_clients()


@router.get("/clients/active", response_model=list[ClientOut])
def clients_active(db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("clients.read"))):
    return ClientService(db).list_clients(active_only=True)


@router.get("/clients/{client_id}", response_model=ClientOut)
def client_detail(client_id: int, db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("clients.read"))):
    clients_data = ClientService(db).list_clients()
    item = next((x for x in clients_data if x["id"] == client_id), None)
    if not item:
        _not_found("CLIENT_NOT_FOUND", "Client not found")
    return item


@router.get("/sessions", response_model=list[SessionOut])
def sessions(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    sort: str = Query(default="-started_at"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: SecurityPrincipal = Depends(require_permission("sessions.read")),
):
    query = db.query(SessionRecord)
    if status:
        query = query.filter(SessionRecord.status == status)
    query = query.order_by(SessionRecord.started_at.desc() if sort.startswith("-") else SessionRecord.started_at.asc())
    return query.offset(offset).limit(limit).all()


@router.get("/sessions/active", response_model=list[SessionOut])
def sessions_active(db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("sessions.read"))):
    return db.query(SessionRecord).filter(SessionRecord.status == "active").order_by(SessionRecord.started_at.desc()).all()


@router.get("/sessions/{session_id}", response_model=SessionOut)
def session_detail(session_id: int, db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("sessions.read"))):
    session = db.query(SessionRecord).filter(SessionRecord.id == session_id).first()
    if not session:
        _not_found("SESSION_NOT_FOUND", "Session not found")
    return session


@router.get("/server/status", response_model=ServerStatusOut)
def server_status(db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("server.read"))):
    row = db.query(ServerStatus).first()
    if not row:
        _not_found("SERVER_STATUS_NOT_FOUND", "status not found")
    return {
        "service_status": row.service_status,
        "xray_version": row.xray_version,
        "uptime_hours": row.uptime_hours,
        "hostname": row.hostname,
        "domain": row.domain,
        "port": row.port,
        "config_summary": json.loads(row.config_summary),
    }


@router.get("/server/logs")
def server_logs(_: SecurityPrincipal = Depends(require_permission("server.read"))):
    adapter = ProviderFactory.get(get_settings().app_provider)
    return {"lines": LogService(adapter).logs()}


@router.post("/server/restart")
def restart_server(db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("server.restart"))):
    adapter = ProviderFactory.get(get_settings().app_provider)
    db.add(AdminActionLog(action="Restart Xray", status="success", meta="{}"))
    db.commit()
    return {"message": adapter.restart(), "at": datetime.utcnow()}


@router.post("/server/reload")
def reload_server(db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("server.reload"))):
    adapter = ProviderFactory.get(get_settings().app_provider)
    db.add(AdminActionLog(action="Reload Xray config", status="success", meta="{}"))
    db.commit()
    return {"message": adapter.reload(), "at": datetime.utcnow()}


@router.get("/events", response_model=list[EventOut])
def events(db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("dashboard.read"))):
    return db.query(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(20).all()


@router.get("/activity-log", response_model=list[ActionLogOut])
def activity(db: Session = Depends(get_db), _: SecurityPrincipal = Depends(require_permission("audit.read"))):
    logs = db.query(AdminActionLog).order_by(AdminActionLog.created_at.desc()).limit(50).all()
    return [{"id": l.id, "action": l.action, "status": l.status, "created_at": l.created_at, "meta": json.loads(l.meta)} for l in logs]


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    principal: SecurityPrincipal = Depends(require_permission("notifications.read")),
):
    return services.list_notifications(db=db, principal_id=principal.subject_id, unread_only=unread_only, limit=limit, offset=offset)


@router.post("/notifications/{notification_id}/read")
def read_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    principal: SecurityPrincipal = Depends(require_permission("notifications.read")),
):
    ok = services.mark_notification_read(db=db, notification_id=notification_id, principal_id=principal.subject_id)
    if not ok:
        _not_found("NOTIFICATION_NOT_FOUND", "Notification not found")
    return {"ok": True}


@router.post("/notifications/read-all")
def read_all_notifications(
    db: Session = Depends(get_db),
    principal: SecurityPrincipal = Depends(require_permission("notifications.read")),
):
    updated = services.mark_all_notifications_read(db=db, principal_id=principal.subject_id)
    return {"ok": True, "updated": updated}


@router.get("/events/stream")
def event_stream():
    def generate():
        notifications = itertools.cycle(
            [
                {"type": "info", "title": "Система активна", "message": "Мониторинг Xray работает в штатном режиме.", "entity_type": "server", "entity_id": "main"},
                {"type": "warning", "title": "Частые переподключения", "message": "Обнаружены повторные reconnect-события у одного клиента.", "entity_type": "client", "entity_id": "1"},
                {"type": "warning", "title": "Лимит трафика", "message": "Один из линков приближается к лимиту 80%.", "entity_type": "link", "entity_id": "2"},
                {"type": "info", "title": "Новая активная сессия", "message": "Подключено новое устройство через VLESS.", "entity_type": "session", "entity_id": "1"},
            ]
        )
        while True:
            payload = {"kind": "notification", **next(notifications), "ts": datetime.utcnow().isoformat()}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            time.sleep(8)

    return StreamingResponse(generate(), media_type="text/event-stream")
