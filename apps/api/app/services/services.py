import hashlib
import json
import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_
from sqlalchemy.orm import Session, aliased

from app.core.security import ROLE_PERMISSION_MAP
from app.models.entities import (
    AdminActionLog,
    ClientSession,
    AuthSession,
    Notification,
    NotificationRead,
    Permission,
    Role,
    RolePermission,
    User,
    ServerStatus,
    SessionRecord,
    SystemEvent,
    TrafficSnapshot,
    UserLink,
)
from app.providers.base import AvgProviderAdapter, MockXrayAdapter, ProviderAdapter, WireGuardProviderAdapter, XrayProviderAdapter


class StatsService:
    def __init__(self, db: Session, adapter: ProviderAdapter):
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
        provider_stats = self.adapter.get_stats()
        return {
            "total_links": total_links,
            "active_connections": active_connections,
            "traffic_24h_gb": round(traffic_24h, 2),
            "server_status": server.service_status if server else "unknown",
            "chart_24h": chart_24h,
            "chart_7d": chart_7d,
            "provider": provider_stats.get("provider", "mock"),
            "provider_capabilities": provider_stats.get("capabilities", {}),
        }


class LinkService:
    def __init__(self, db: Session):
        self.db = db

    def list_links(self) -> list[dict]:
        links = self.db.query(UserLink).order_by(UserLink.created_at.desc()).all()
        items = []
        for link in links:
            status = "disabled" if not link.enabled else ("active" if link.last_activity_at and link.last_activity_at > datetime.utcnow() - timedelta(hours=2) else "idle")
            items.append(
                {
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
                }
            )
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
            out.append(
                {
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
                }
            )
        return out


class LogService:
    def __init__(self, adapter: ProviderAdapter):
        self.adapter = adapter

    def logs(self) -> list[str]:
        return self.adapter.read_logs()


class ProviderFactory:
    _registry = {
        "xray": XrayProviderAdapter,
        "wg": WireGuardProviderAdapter,
        "avg": AvgProviderAdapter,
        "mock": MockXrayAdapter,
    }

    @classmethod
    def get(cls, provider_name: str) -> ProviderAdapter:
        adapter_cls = cls._registry.get(provider_name, MockXrayAdapter)
        return adapter_cls()

    @classmethod
    def list_providers(cls) -> list[dict]:
        items = []
        for key, adapter_cls in cls._registry.items():
            adapter = adapter_cls()
            items.append(
                {
                    "code": key,
                    "name": adapter.display_name,
                    "capabilities": adapter.capabilities,
                }
            )
        return items


def list_notifications(db: Session, principal_id: str, unread_only: bool = False, limit: int = 100, offset: int = 0) -> list[dict]:
    notification_read = aliased(NotificationRead)

    query = (
        db.query(Notification, notification_read.read_at.label("read_at"))
        .outerjoin(
            notification_read,
            and_(
                notification_read.notification_id == Notification.id,
                notification_read.principal_id == principal_id,
            ),
        )
        .order_by(Notification.created_at.desc())
    )

    if unread_only:
        query = query.filter(notification_read.id.is_(None))

    rows = query.offset(offset).limit(limit).all()

    items = []
    for notification, read_at in rows:
        items.append(
            {
                "id": notification.id,
                "severity": notification.severity,
                "title": notification.title,
                "message": notification.message,
                "entity_type": notification.entity_type,
                "entity_id": notification.entity_id,
                "is_read": bool(read_at),
                "read_at": read_at,
                "created_at": notification.created_at,
            }
        )
    return items


def mark_notification_read(db: Session, notification_id: int, principal_id: str) -> bool:
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        return False

    existing = (
        db.query(NotificationRead)
        .filter(NotificationRead.notification_id == notification_id, NotificationRead.principal_id == principal_id)
        .first()
    )

    if not existing:
        db.add(
            NotificationRead(
                notification_id=notification_id,
                principal_id=principal_id,
                read_at=datetime.utcnow(),
            )
        )
        db.commit()
    return True


def mark_all_notifications_read(db: Session, principal_id: str) -> int:
    notification_ids = [row.id for row in db.query(Notification.id).all()]
    if not notification_ids:
        return 0

    existing_ids = {
        row.notification_id
        for row in db.query(NotificationRead.notification_id).filter(NotificationRead.principal_id == principal_id).all()
    }

    created = 0
    for notification_id in notification_ids:
        if notification_id not in existing_ids:
            db.add(
                NotificationRead(
                    notification_id=notification_id,
                    principal_id=principal_id,
                    read_at=datetime.utcnow(),
                )
            )
            created += 1

    if created:
        db.commit()
    return created


def ensure_token_user_seed(db: Session) -> None:
    token = "admin-token"
    token_fingerprint = hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]

    user = db.query(User).filter(User.token_fingerprint == token_fingerprint).first()
    if not user:
        user = User(
            username=f"token-admin-{token_fingerprint}",
            role_key="owner",
            auth_source="token",
            token_fingerprint=token_fingerprint,
            is_active=True,
            created_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
        )
        db.add(user)
        db.flush()

    subject = f"token:{token_fingerprint}:owner"
    exists = db.query(AuthSession).filter(AuthSession.subject == subject).first()
    if not exists:
        db.add(AuthSession(user_id=user.id, subject=subject, session_type="token", issued_at=datetime.utcnow(), expires_at=None, revoked_at=None))




def _profile_connection_target(db: Session) -> tuple[str, int, str]:
    status = db.query(ServerStatus).first()
    host = status.domain if status and status.domain else "vpn.example.com"
    port = status.port if status and status.port else 443
    security = "tls" if port == 443 else "none"
    return host, port, security


def get_provider_capabilities(provider_name: str) -> dict[str, bool]:
    adapter = ProviderFactory.get(provider_name)
    return adapter.capabilities

def get_link_profiles(db: Session, link_id: int, provider_name: str = "xray") -> dict | None:
    link = db.query(UserLink).filter(UserLink.id == link_id).first()
    if not link:
        return None

    caps = get_provider_capabilities(provider_name)
    profile_available = caps.get("profiles", False)

    return {
        "link_id": link.id,
        "link_name": link.name,
        "formats": [
            {"key": "vless_uri", "title": "VLESS URI", "available": profile_available, "description": "Универсальный URI для большинства Xray/VLESS клиентов"},
            {"key": "qr_payload", "title": "QR Payload", "available": profile_available, "description": "Строка для генерации QR-кода"},
            {"key": "v2rayn_json", "title": "v2rayN JSON", "available": profile_available, "description": "Импортируемый JSON профиль для v2rayN/v2rayNG"},
            {"key": "singbox_json", "title": "sing-box JSON", "available": profile_available, "description": "Минимальный outbound профиль для совместимых клиентов"},
            {"key": "hiddify_guide", "title": "Hiddify Guide", "available": profile_available, "description": "Человекочитаемая инструкция подключения"},
        ],
    }


def get_link_profile_payload(db: Session, link_id: int, profile_key: str, provider_name: str = "xray") -> dict | None:
    link = db.query(UserLink).filter(UserLink.id == link_id).first()
    if not link:
        return None

    if not get_provider_capabilities(provider_name).get("profiles", False):
        return {
            "key": profile_key,
            "title": "Provider specific",
            "content_type": "text/plain",
            "filename": None,
            "payload": "Формат профиля недоступен для текущего provider.",
            "instruction": "Переключите provider на xray для экспорта VLESS-профилей.",
        }

    host, port, security = _profile_connection_target(db)
    uri = f"vless://{link.uuid}@{host}:{port}?security={security}&type=tcp#{link.name}"

    if profile_key == "vless_uri":
        return {
            "key": "vless_uri",
            "title": "VLESS URI",
            "content_type": "text/plain",
            "filename": f"{link.name}.txt",
            "payload": uri,
            "instruction": "Скопируйте URI и импортируйте в ваш VLESS-клиент.",
        }

    if profile_key == "qr_payload":
        return {
            "key": "qr_payload",
            "title": "QR Payload",
            "content_type": "text/plain",
            "filename": f"{link.name}-qr.txt",
            "payload": uri,
            "instruction": "Передайте строку в любой QR-генератор и сканируйте в клиенте.",
        }

    if profile_key == "v2rayn_json":
        payload = {
            "v": "2",
            "ps": link.name,
            "add": host,
            "port": str(port),
            "id": link.uuid,
            "aid": "0",
            "net": "tcp",
            "type": "none",
            "host": "",
            "path": "",
            "tls": "tls" if security == "tls" else "none",
        }
        return {
            "key": "v2rayn_json",
            "title": "v2rayN/v2rayNG JSON",
            "content_type": "application/json",
            "filename": f"{link.name}-v2rayn.json",
            "payload": json.dumps(payload, ensure_ascii=False, indent=2),
            "instruction": "Импортируйте JSON как пользовательский профиль (custom config).",
        }

    if profile_key == "singbox_json":
        payload = {
            "outbounds": [
                {
                    "type": "vless",
                    "tag": link.name,
                    "server": host,
                    "server_port": port,
                    "uuid": link.uuid,
                    "tls": {"enabled": security == "tls"},
                    "transport": {"type": "tcp"},
                }
            ]
        }
        return {
            "key": "singbox_json",
            "title": "sing-box JSON",
            "content_type": "application/json",
            "filename": f"{link.name}-singbox.json",
            "payload": json.dumps(payload, ensure_ascii=False, indent=2),
            "instruction": "Добавьте outbound в конфиг sing-box и выберите его как активный.",
        }

    if profile_key == "hiddify_guide":
        guide = (
            f"1) Откройте Hiddify и нажмите Add Profile\n"
            f"2) Выберите Import from Clipboard\n"
            f"3) Вставьте URI: {uri}\n"
            f"4) Сохраните и активируйте профиль {link.name}"
        )
        return {
            "key": "hiddify_guide",
            "title": "Hiddify Guide",
            "content_type": "text/plain",
            "filename": f"{link.name}-hiddify.txt",
            "payload": guide,
            "instruction": "Выполните шаги в Hiddify для подключения.",
        }

    return None


def seed_if_empty(db: Session):
    if db.query(UserLink).count() > 0:
        return
    now = datetime.utcnow()

    ensure_token_user_seed(db)

    for role_key in ROLE_PERMISSION_MAP.keys():
        db.add(Role(key=role_key, name=role_key.capitalize(), description="System role"))
    permission_keys = sorted({p for perms in ROLE_PERMISSION_MAP.values() for p in perms})
    for p in permission_keys:
        db.add(Permission(key=p, description=f"Permission {p}"))
    db.flush()
    for role_key, perms in ROLE_PERMISSION_MAP.items():
        for p in perms:
            db.add(RolePermission(role_key=role_key, permission_key=p))

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

    db.add_all([
        SessionRecord(client_name="Иван / iPhone", link_name=links[0].name, source_ip=base_ips[0], status="active", started_at=now - timedelta(minutes=35), duration_sec=2100, inbound_gb=1.2, outbound_gb=2.7),
        SessionRecord(client_name="Office Windows", link_name=links[1].name, source_ip=base_ips[1], status="active", started_at=now - timedelta(minutes=12), duration_sec=720, inbound_gb=0.4, outbound_gb=0.9),
        SessionRecord(client_name="MacBook", link_name=links[2].name, source_ip=base_ips[2], status="closed", started_at=now - timedelta(hours=4), duration_sec=3600, inbound_gb=0.8, outbound_gb=1.0),
    ])

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
        Notification(severity="info", title="Система активна", message="Мониторинг Xray работает стабильно", entity_type="server", entity_id="main"),
        Notification(severity="warning", title="Лимит трафика", message="Один из линков превысил 80% лимита", entity_type="link", entity_id="2"),
    ])
    db.add_all([
        AdminActionLog(action="Вход в панель", status="success", meta=json.dumps({"ip": "10.0.0.2"})),
        AdminActionLog(action="Экспорт конфигурации", status="success", meta=json.dumps({"format": "json"})),
    ])
    db.commit()
