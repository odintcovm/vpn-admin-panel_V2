import json
from datetime import datetime
import itertools
import time

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.models.entities import AdminActionLog, ServerStatus, SystemEvent, UserLink
from app.schemas.api import ActionLogOut, ClientOut, DashboardOverview, EventOut, LinkCreate, LinkOut, LinkUpdate, ServerStatusOut
from app.services.services import ClientService, LinkService, LogService, ProviderFactory, StatsService

router = APIRouter(prefix="/api")


def to_link_out(item: dict) -> LinkOut:
    return LinkOut(**item)


@router.get("/dashboard/overview", response_model=DashboardOverview)
def get_overview(db: Session = Depends(get_db)):
    adapter = ProviderFactory.get(settings.app_provider)
    return StatsService(db, adapter).overview()


@router.get("/links", response_model=list[LinkOut])
def list_links(db: Session = Depends(get_db)):
    return [to_link_out(i) for i in LinkService(db).list_links()]


@router.post("/links", response_model=LinkOut)
def create_link(payload: LinkCreate, db: Session = Depends(get_db)):
    link = LinkService(db).create(payload.model_dump())
    fresh = next((x for x in LinkService(db).list_links() if x["id"] == link.id), None)
    if not fresh:
        raise HTTPException(500, "Created link not found")
    return to_link_out(fresh)


@router.patch("/links/{link_id}", response_model=LinkOut)
def patch_link(link_id: int, payload: LinkUpdate, db: Session = Depends(get_db)):
    link = db.query(UserLink).filter(UserLink.id == link_id).first()
    if not link:
        raise HTTPException(404, "Link not found")
    LinkService(db).patch(link, payload.model_dump(exclude_unset=True))
    fresh = next((x for x in LinkService(db).list_links() if x["id"] == link_id), None)
    return to_link_out(fresh)


@router.delete("/links/{link_id}")
def delete_link(link_id: int, db: Session = Depends(get_db)):
    link = db.query(UserLink).filter(UserLink.id == link_id).first()
    if not link:
        raise HTTPException(404, "Link not found")
    LinkService(db).delete(link)
    return {"ok": True}


@router.post("/links/{link_id}/regenerate", response_model=LinkOut)
def regenerate_link(link_id: int, db: Session = Depends(get_db)):
    link = db.query(UserLink).filter(UserLink.id == link_id).first()
    if not link:
        raise HTTPException(404, "Link not found")
    LinkService(db).regenerate(link)
    fresh = next((x for x in LinkService(db).list_links() if x["id"] == link_id), None)
    return to_link_out(fresh)


@router.get("/links/{link_id}/qr")
def get_qr(link_id: int, db: Session = Depends(get_db)):
    data = next((x for x in LinkService(db).list_links() if x["id"] == link_id), None)
    if not data:
        raise HTTPException(404, "Link not found")
    return {"qr_payload": data["vless_url"], "hint": "Use this string in a QR generator", "link_name": data["name"]}


@router.get("/clients", response_model=list[ClientOut])
def clients(db: Session = Depends(get_db)):
    return ClientService(db).list_clients()


@router.get("/clients/active", response_model=list[ClientOut])
def clients_active(db: Session = Depends(get_db)):
    return ClientService(db).list_clients(active_only=True)


@router.get("/clients/{client_id}", response_model=ClientOut)
def client_detail(client_id: int, db: Session = Depends(get_db)):
    clients_data = ClientService(db).list_clients()
    item = next((x for x in clients_data if x["id"] == client_id), None)
    if not item:
        raise HTTPException(404, "Client not found")
    return item


@router.get("/server/status", response_model=ServerStatusOut)
def server_status(db: Session = Depends(get_db)):
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
def server_logs():
    adapter = ProviderFactory.get(settings.app_provider)
    return {"lines": LogService(adapter).logs()}


@router.post("/server/restart")
def restart_server(db: Session = Depends(get_db)):
    adapter = ProviderFactory.get(settings.app_provider)
    db.add(AdminActionLog(action="Restart Xray", status="success", meta="{}"))
    db.commit()
    return {"message": adapter.restart(), "at": datetime.utcnow()}


@router.post("/server/reload")
def reload_server(db: Session = Depends(get_db)):
    adapter = ProviderFactory.get(settings.app_provider)
    db.add(AdminActionLog(action="Reload Xray config", status="success", meta="{}"))
    db.commit()
    return {"message": adapter.reload(), "at": datetime.utcnow()}


@router.get("/events", response_model=list[EventOut])
def events(db: Session = Depends(get_db)):
    return db.query(SystemEvent).order_by(SystemEvent.created_at.desc()).limit(20).all()


@router.get("/activity-log", response_model=list[ActionLogOut])
def activity(db: Session = Depends(get_db)):
    logs = db.query(AdminActionLog).order_by(AdminActionLog.created_at.desc()).limit(50).all()
    return [
        {"id": l.id, "action": l.action, "status": l.status, "created_at": l.created_at, "meta": json.loads(l.meta)}
        for l in logs
    ]


@router.get("/events/stream")
def event_stream():
    def generate():
        notifications = itertools.cycle([
            {"type": "info", "title": "Система активна", "message": "Мониторинг Xray работает в штатном режиме."},
            {"type": "warning", "title": "Частые переподключения", "message": "Обнаружены повторные reconnect-события у одного клиента."},
            {"type": "warning", "title": "Лимит трафика", "message": "Один из линков приближается к лимиту 80%."},
            {"type": "info", "title": "Новая активная сессия", "message": "Подключено новое устройство через VLESS."},
        ])
        while True:
            payload = {"kind": "notification", **next(notifications), "ts": datetime.utcnow().isoformat()}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            time.sleep(8)

    return StreamingResponse(generate(), media_type="text/event-stream")
