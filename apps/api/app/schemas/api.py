from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class LinkCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    note: str = ""
    tag: str = ""
    traffic_limit_gb: float | None = Field(default=None, ge=0)
    expires_at: datetime | None = None
    enabled: bool = True


class LinkUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    note: str | None = None
    tag: str | None = None
    traffic_limit_gb: float | None = Field(default=None, ge=0)
    expires_at: datetime | None = None
    enabled: bool | None = None


class LinkOut(BaseModel):
    id: int
    name: str
    uuid: str
    note: str
    tag: str
    status: str
    enabled: bool
    last_ip: str | None
    last_activity_at: datetime | None
    total_traffic_gb: float
    traffic_limit_gb: float | None
    expires_at: datetime | None
    vless_url: str


class DashboardOverview(BaseModel):
    total_links: int
    active_connections: int
    traffic_24h_gb: float
    server_status: str
    chart_24h: list[dict[str, Any]]
    chart_7d: list[dict[str, Any]]


class ClientOut(BaseModel):
    id: int
    client_name: str
    link_name: str
    link_id: int
    status: str
    current_ip: str
    ip_history: list[str]
    active_sessions: int
    total_traffic_gb: float
    traffic_24h_gb: float
    traffic_7d_gb: float
    last_activity_at: datetime | None
    note: str
    tag: str
    events: list[dict[str, Any]]


class SessionOut(BaseModel):
    id: int
    client_name: str
    link_name: str
    source_ip: str
    status: str
    started_at: datetime
    duration_sec: int
    inbound_gb: float
    outbound_gb: float


class SessionDrilldownOut(SessionOut):
    reconnect_summary: str
    related_events: list[dict[str, Any]]


class TimelineEventOut(BaseModel):
    at: datetime
    kind: str
    title: str
    message: str


class NotificationOut(BaseModel):
    id: int
    severity: str
    title: str
    message: str
    entity_type: str | None
    entity_id: str | None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class ServerStatusOut(BaseModel):
    service_status: str
    xray_version: str
    uptime_hours: int
    hostname: str
    domain: str
    port: int
    config_summary: dict[str, Any]


class HealthFreshnessOut(BaseModel):
    provider_status: Literal["healthy", "degraded", "disconnected"]
    backend_status: Literal["ok", "degraded", "error"]
    server_status: str
    last_success_refresh_at: datetime
    data_freshness_sec: int


class EventOut(BaseModel):
    id: int
    level: str
    title: str
    message: str
    created_at: datetime


class ActionLogOut(BaseModel):
    id: int
    action: str
    status: str
    created_at: datetime
    meta: dict[str, Any]


class AuthMeOut(BaseModel):
    subject_id: str
    role: str
    permissions: list[str]
    auth_mode: str
    user_id: int | None = None
    dev_role_emulation_enabled: bool


class ActionExecuteIn(BaseModel):
    action: Literal["restart", "reload", "regenerate_uuid", "set_link_enabled", "mark_suspicious"]
    target_type: Literal["server", "link", "client"]
    target_id: int | None = None
    reason: str | None = Field(default=None, max_length=240)
    enabled: bool | None = None


class ActionExecuteOut(BaseModel):
    ok: bool
    action: str
    result: str
    at: datetime
