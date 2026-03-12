import json
import itertools
import time
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_security_context, require_permission
from app.db.database import get_db
from app.models.entities import AdminActionLog, Notification, ServerStatus, SessionRecord, SystemEvent, UserLink
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
from app.services.services import ClientService, LinkService, LogService, ProviderFactory, StatsService

router = APIRouter(prefix="/api")


def to_link_out(item: dict) -> LinkOut:
    return LinkOut(**item)


@router.get("/auth/me", response_model=AuthMeOut)
def auth_me(context: dict = Depends(get_security_context)):
    return context


@router.get("/dashboard/overview", response_model=DashboardOverview)
def get_overview(db: Session = Depends(get_db), _: dict = Depends(require_permission("dashboard.read"))):
    adapter = ProviderFactory.get(settings.app_provider)
    return StatsService(db, adapter).overview()


@router.get("/links", response_model=list[LinkOut])
def list_links(db: Session = Depends(get_db), _: dict = Depends(require_permission("links.read"))):
    return [to_link_out(i) for i in LinkService(db).list_links()]


@router.post("/links", response_model=LinkOut)
def create_link(payload: LinkCreate, db: Session = Depends(get_db), _: dict = Depends(require_permission("links.write"))):
    link = LinkService(db).create(payload.model_dump())
    fresh = next((x for x in LinkService(db).list_links() if x["id"] == link.id), None)
    if not fresh:
        raise HTTPException(500, "Created link not found")
    return to_link_out(fresh)


@router.patch("/links/{link_id}", response_model=LinkOut)
def patch_link(link_id: int, payload: LinkUpdate, db: Session = Depends(get_db), _: dict = Depends(require_permission("links.write"))):
    link = db.query(UserLink).filter(UserLink.id == link_id).first()
    if not link:
        raise HTTPException(404, "Link not found")
    LinkService(db).patch(link, payload.model_dump(exclude_unset=True))
    fresh = next((x for x in LinkService(db).list_links() if x["id"] == link_id), None)
    return to_link_out(fresh)


@router.delete("/links/{link_id}")
def delete_link(link_id: int, db: Session = Depends(get_db), _: dict = Depends(require_permission("links.delete"))):
    link = db.query(UserLink).filter(UserLink.id == link_id).first()
    if not link:
        raise HTTPException(404, "Link not found")
    LinkService(db).delete(link)
    return {"ok": True}


@router.post("/links/{link_id}/regenerate", response_model=LinkOut)
def regenerate_link(link_id: int, db: Session = Depends(get_db), _: dict = Depends(require_permission("links.regenerate"))):
    link = db.query(UserLink).filter(UserLink.id == link_id).first()
    if not link:
        raise HTTPException(404, "Link not found")
    LinkService(db).regenerate(link)
    fresh = next((x for x in LinkService(db).list_links() if x["id"] == link_id), None)
    return to_link_out(fresh)


@router.get("/links/{link_id}/qr")
def get_qr(link_id: int, db: Session = Depends(get_db), _: dict = Depends(require_permission("links.read"))):
    data = next((x for x in LinkService(db).list_links() if x["id"] == link_id), None)
    if not data:
        raise HTTPException(404, "Link not found")
    return {"qr_payload": data["vless_url"], "hint": "Use this string in a QR generator", "link_name": data["name"]}


@router.get("/clients", response_model=list[ClientOut])
def clients(db: Session = Depends(get_db), _: dict = Depends(require_permission("clients.read"))):
    return ClientService(db).list_clients()


@router.get("/clients/active", response_model=list[ClientOut])
def clients_active(db: Session = Depends(get_db), _: dict = Depends(require_permission("clients.read"))):
    return ClientService(db).list_clients(active_only=True)


@router.get("/clients/{client_id}", response_model=ClientOut)
def client_detail(client_id: int, db: Session = Depends(get_db), _: dict = Depends(require_permission("clients.read"))):
    clients_data = ClientService(db).list_clients()
    item = next((x for x in clients_data if x["id"] == client_id), None)
    if not item:
        raise HTTPException(404, "Client not found")
    return item


@router.get("/sessions", response_model=list[SessionOut])
def sessions(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    sort: str = Query(default="-started_at"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: dict = Depends(require_permission("sessions.read")),
):
    q = db.query(SessionRecord)
    if status:
        q = q.filter(SessionRecord.status == status)
    q = q.order_by(SessionRecord.started_at.desc() if sort.startswith("-") else SessionRecord.started_at.asc())
    return q.offset(offset).limit(limit).all()


@router.get("/sessions/active", response_model=list[SessionOut])
def sessions_active(db: Session = Depends(get_db), _: dict = Depends(require_permission("sessions.read"))):
    return db.query(SessionRecord).filter(SessionRecord.status == "active").order_by(SessionRecord.started_at.desc()).all()


@router.get("/sessions/{session_id}", response_model=SessionOut)
def session_detail(session_id: int, db: Session = Depends(get_db), _: dict = Depends(require_permission("sessions.read"))):
    session = db.query(SessionRecord).filter(SessionRecord.id == session_id).first()
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@router.get("/server/status", response_model=ServerStatusOut)
def server_status(db: Session = Depends(get_db), _: dict = Depends(require_permission("server.read"))):
    row = db.query(ServerStatus).first()
    if not row:
        raise HTTPException(404, "status not found")
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
def server_logs(_: dict = Depends(require_permission("server.read"))):
    adapter = ProviderFactory.get(settings.app_provider)
    return {"lines": LogService(adapter).logs()}


@router.post("/server/restart")
def restart_server(db: Session = Depends(get_db), _: dict = Depends(require_permission("server.restart"))):
    adapter = ProviderFactory.get(settings.app_provider)
    db.add(AdminActionLog(action="Restart Xray", status="success", meta="{}"))
    db.commit()
    return {"message": adapter.restart(), "at": datetime.utcnow()}


@router.post("/server/reload")
def reload_server(db: Session = Depends(get_db), _: dict = Depends(require_permission("server.reload"))):
    adapter = ProviderFactory.get(settings.app_provider)
    db.add(AdminActionLog(action="Reload Xray config", status="success", meta="{}"))
    db.commit()
    return {"message": adapter.reload(), "at": datetime.utcnow()}


@router.get("/events", response_model=list[EventOut])
def events(db: Session = Depends(get_db), _: dict = Depends(require_permission("dashboard.read"))):
    return db.query(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(20).all()


@router.get("/activity-log", response_model=list[ActionLogOut])
def activity(db: Session = Depends(get_db), _: dict = Depends(require_permission("audit.read"))):
    logs = db.query(AdminActionLog).order_by(AdminActionLog.created_at.desc()).limit(50).all()
    return [
        {"id": l.id, "action": l.action, "status": l.status, "created_at": l.created_at, "meta": json.loads(l.meta)}
        for l in logs
    ]


@router.get("/notifications", response_model=list[NotificationOut])
def list_notifications(db: Session = Depends(get_db), _: dict = Depends(require_permission("notifications.read"))):
    return db.query(Notification).order_by(Notification.created_at.desc()).limit(100).all()


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db), _: dict = Depends(require_permission("notifications.read"))):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(404, "Notification not found")
    notification.is_read = True
    db.commit()
    return {"ok": True}


@router.post("/notifications/read-all")
def mark_all_notifications_read(db: Session = Depends(get_db), _: dict = Depends(require_permission("notifications.read"))):
    db.query(Notification).filter(Notification.is_read.is_(False)).update({"is_read": True})
    db.commit()
    return {"ok": True}


@router.get("/events/stream")
def event_stream():
    def generate():
        notifications = itertools.cycle([
            {"type": "info", "title": "Система активна", "message": "Мониторинг Xray работает в штатном режиме.", "entity_type": "server", "entity_id": "main"},
            {"type": "warning", "title": "Частые переподключения", "message": "Обнаружены повторные reconnect-события у одного клиента.", "entity_type": "client", "entity_id": "1"},
            {"type": "warning", "title": "Лимит трафика", "message": "Один из линков приближается к лимиту 80%.", "entity_type": "link", "entity_id": "2"},
            {"type": "info", "title": "Новая активная сессия", "message": "Подключено новое устройство через VLESS.", "entity_type": "session", "entity_id": "1"},
        ])
        while True:
            payload = {"kind": "notification", **next(notifications), "ts": datetime.utcnow().isoformat()}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            time.sleep(8)

    return StreamingResponse(generate(), media_type="text/event-stream")
