import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.entities import AdminActionLog, ClientSession, ServerStatus, SystemEvent, TrafficSnapshot, UserLink
from app.providers.base import MockXrayAdapter, XrayAdapter, XrayProviderAdapter


class StatsService:
    def __init__(self, db: Session, adapter: XrayAdapter):
        self.db = db
        self.adapter = adapter

    def overview(self) -> dict:
        total_links = self.db.query(UserLink).count()
        active_connections = self.db.query(ClientSession).filter(ClientSession.status == "active").count()
        traffic_24h = sum(t.traffic_gb for t in self.db.query(TrafficSnapshot).filter(TrafficSnapshot.period == "24h").all())
        server = self.db.query(ServerStatus).first()
        chart_24h = [
            {"label": t.timestamp.strftime("%H:%M"), "value": t.traffic_gb}
            for t in self.db.query(TrafficSnapshot).filter(TrafficSnapshot.period == "24h").order_by(TrafficSnapshot.timestamp.asc()).all()
        ]
        chart_7d = [
            {"label": t.timestamp.strftime("%a"), "value": t.traffic_gb}
            for t in self.db.query(TrafficSnapshot).filter(TrafficSnapshot.period == "7d").order_by(TrafficSnapshot.timestamp.asc()).all()
        ]
        return {
            "total_links": total_links,
            "active_connections": active_connections,
            "traffic_24h_gb": round(traffic_24h, 2),
            "server_status": server.service_status if server else "unknown",
            "chart_24h": chart_24h,
            "chart_7d": chart_7d,
        }


class LinkService:
    def __init__(self, db: Session):
        self.db = db

    def list_links(self) -> list[dict]:
        links = self.db.query(UserLink).order_by(UserLink.created_at.desc()).all()
        items = []
        for link in links:
            status = "disabled" if not link.enabled else ("active" if link.last_activity_at and link.last_activity_at > datetime.utcnow() - timedelta(hours=2) else "idle")
            items.append({
                "id": link.id,
                "name": link.name,
                "uuid": link.uuid,
                "note": link.note,
                "tag": link.tag,
                "status": status,
                "enabled": link.enabled,
                "last_ip": link.last_ip,
                "last_activity_at": link.last_activity_at,
                "total_traffic_gb": link.total_traffic_gb,
                "traffic_limit_gb": link.traffic_limit_gb,
                "expires_at": link.expires_at,
                "vless_url": f"vless://{link.uuid}@vpn.example.com:443?security=tls&type=tcp#{link.name}",
            })
        return items

    def create(self, payload: dict):
        link = UserLink(uuid=str(uuid.uuid4()), **payload)
        self.db.add(link)
        self.db.flush()
        self.log_action(f"Создан VLESS линк: {link.name}")
        self.db.commit()
        self.db.refresh(link)
        return link

    def patch(self, link: UserLink, payload: dict):
        for key, value in payload.items():
            setattr(link, key, value)
        self.log_action(f"Обновлен VLESS линк: {link.name}")
        self.db.commit()
        self.db.refresh(link)
        return link

    def delete(self, link: UserLink):
        self.log_action(f"Удален VLESS линк: {link.name}")
        self.db.delete(link)
        self.db.commit()

    def regenerate(self, link: UserLink):
        link.uuid = str(uuid.uuid4())
        self.log_action(f"Регенерация UUID: {link.name}")
        self.db.commit()
        self.db.refresh(link)
        return link

    def log_action(self, action: str):
        self.db.add(AdminActionLog(action=action, status="success", meta=json.dumps({"by": "admin"})))


class ClientService:
    def __init__(self, db: Session):
        self.db = db

    def list_clients(self, active_only: bool = False):
        query = self.db.query(ClientSession)
        if active_only:
            query = query.filter(ClientSession.status == "active")
        clients = query.order_by(ClientSession.last_activity_at.desc()).all()
        out = []
        for c in clients:
            out.append({
                "id": c.id,
                "client_name": c.client_name,
                "link_name": c.link.name,
                "link_id": c.link_id,
                "status": c.status,
                "current_ip": c.current_ip,
                "ip_history": json.loads(c.ip_history),
                "active_sessions": c.active_sessions,
                "total_traffic_gb": c.total_traffic_gb,
                "traffic_24h_gb": c.traffic_24h_gb,
                "traffic_7d_gb": c.traffic_7d_gb,
                "last_activity_at": c.last_activity_at,
                "note": c.link.note,
                "tag": c.link.tag,
                "events": json.loads(c.events_json),
            })
        return out


class LogService:
    def __init__(self, adapter: XrayAdapter):
        self.adapter = adapter

    def logs(self) -> list[str]:
        return self.adapter.read_logs()


class ProviderFactory:
    @staticmethod
    def get(provider_name: str) -> XrayAdapter:
        return XrayProviderAdapter() if provider_name == "xray" else MockXrayAdapter()


def seed_if_empty(db: Session):
    if db.query(UserLink).count() > 0:
        return
    now = datetime.utcnow()
    tags = ["iPhone main", "Windows PC", "MacBook Air", "Test device", "Work phone", "Home TV"]
    base_ips = ["95.179.146.12", "185.246.65.201", "176.9.44.170", "77.88.55.12", "46.17.104.1", "5.255.253.1"]
    links = []
    for i in range(6):
        links.append(
            UserLink(
                name=f"Клиент {i+1}",
                uuid=str(uuid.uuid4()),
                note="Основное устройство" if i < 3 else "Резерв",
                tag=tags[i],
                enabled=False if i == 4 else True,
                total_traffic_gb=round(15 + i * 8.2, 2),
                traffic_limit_gb=80 if i in (0, 1, 2) else 40,
                last_ip=base_ips[i],
                last_activity_at=now - timedelta(minutes=20 * i),
                expires_at=now + timedelta(days=45 + i * 10),
            )
        )
    links[5].last_activity_at = now - timedelta(days=2)
    db.add_all(links)
    db.flush()

    sessions = [
        ClientSession(link_id=links[0].id, client_name="Иван / iPhone", status="active", current_ip=base_ips[0], ip_history=json.dumps([base_ips[0], "95.179.146.11"]), active_sessions=1, total_traffic_gb=54.2, traffic_24h_gb=3.1, traffic_7d_gb=14.7, last_activity_at=now - timedelta(minutes=3), events_json=json.dumps([{"type": "reconnect", "label": "Переподключение", "time": "2 мин назад"}])),
        ClientSession(link_id=links[1].id, client_name="Office Windows", status="active", current_ip=base_ips[1], ip_history=json.dumps([base_ips[1], "185.246.65.45"]), active_sessions=1, total_traffic_gb=32.3, traffic_24h_gb=1.8, traffic_7d_gb=8.4, last_activity_at=now - timedelta(minutes=9), events_json=json.dumps([{"type": "suspicious", "label": "Новый IP", "time": "9 мин назад"}])),
        ClientSession(link_id=links[2].id, client_name="MacBook", status="idle", current_ip=base_ips[2], ip_history=json.dumps([base_ips[2]]), active_sessions=0, total_traffic_gb=10.1, traffic_24h_gb=0.2, traffic_7d_gb=1.1, last_activity_at=now - timedelta(hours=11), events_json="[]"),
    ]
    db.add_all(sessions)

    for h in range(24):
        db.add(TrafficSnapshot(period="24h", timestamp=now - timedelta(hours=23 - h), traffic_gb=round(0.2 + (h % 6) * 0.18, 2)))
    for d in range(7):
        db.add(TrafficSnapshot(period="7d", timestamp=now - timedelta(days=6 - d), traffic_gb=round(2.5 + d * 0.8, 2)))

    db.add(ServerStatus(service_status="running", xray_version="1.8.13", uptime_hours=138, hostname="vps-01", domain="vpn.example.com", port=443, config_summary=json.dumps({"provider": "mock", "transport": "tcp+tls"})))
    db.add_all([
        SystemEvent(level="info", title="Новая активная сессия", message="Клиент Иван / iPhone подключился"),
        SystemEvent(level="warning", title="Подозрительная активность", message="Частые переподключения Office Windows"),
        SystemEvent(level="info", title="Лимит 80%", message="Клиент 2 приближается к лимиту трафика"),
    ])
    db.add_all([
        AdminActionLog(action="Вход в панель", status="success", meta=json.dumps({"ip": "10.0.0.2"})),
        AdminActionLog(action="Экспорт конфигурации", status="success", meta=json.dumps({"format": "json"})),
    ])
    db.commit()
