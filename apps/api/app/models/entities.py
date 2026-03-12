from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class UserLink(Base):
    __tablename__ = "user_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    uuid: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    note: Mapped[str] = mapped_column(String(255), default="")
    tag: Mapped[str] = mapped_column(String(120), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    total_traffic_gb: Mapped[float] = mapped_column(Float, default=0)
    traffic_limit_gb: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions = relationship("ClientSession", back_populates="link", cascade="all, delete-orphan")


class ClientSession(Base):
    __tablename__ = "client_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    link_id: Mapped[int] = mapped_column(ForeignKey("user_links.id"), nullable=False)
    client_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="idle")
    current_ip: Mapped[str] = mapped_column(String(64))
    ip_history: Mapped[str] = mapped_column(Text, default="[]")
    active_sessions: Mapped[int] = mapped_column(Integer, default=0)
    total_traffic_gb: Mapped[float] = mapped_column(Float, default=0)
    traffic_24h_gb: Mapped[float] = mapped_column(Float, default=0)
    traffic_7d_gb: Mapped[float] = mapped_column(Float, default=0)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    events_json: Mapped[str] = mapped_column(Text, default="[]")

    link = relationship("UserLink", back_populates="sessions")


class TrafficSnapshot(Base):
    __tablename__ = "traffic_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    period: Mapped[str] = mapped_column(String(16), default="24h")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    traffic_gb: Mapped[float] = mapped_column(Float, default=0)


class ServerStatus(Base):
    __tablename__ = "server_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_status: Mapped[str] = mapped_column(String(32), default="running")
    xray_version: Mapped[str] = mapped_column(String(32), default="1.8.13")
    uptime_hours: Mapped[int] = mapped_column(Integer, default=24)
    hostname: Mapped[str] = mapped_column(String(120), default="vpn.example.com")
    domain: Mapped[str] = mapped_column(String(120), default="vpn.example.com")
    port: Mapped[int] = mapped_column(Integer, default=443)
    config_summary: Mapped[str] = mapped_column(Text, default="{}")


class AdminActionLog(Base):
    __tablename__ = "admin_action_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    action: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(32), default="success")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    meta: Mapped[str] = mapped_column(Text, default="{}")


class SystemEvent(Base):
    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    level: Mapped[str] = mapped_column(String(32), default="info")
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True)
    value: Mapped[str] = mapped_column(Text)
