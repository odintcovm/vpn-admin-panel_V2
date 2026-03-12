"""core mvp tables and auth foundation

Revision ID: 0003_core_tables_and_auth_foundation
Revises: 0002_notification_reads_and_rbac_hardening
Create Date: 2026-03-12 00:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_core_tables_and_auth_foundation"
down_revision = "0002_notification_reads_and_rbac_hardening"
branch_labels = None
depends_on = None


def _has_table(inspector, name: str) -> bool:
    return name in inspector.get_table_names()


def _has_index(inspector, table: str, idx: str) -> bool:
    return any(i.get("name") == idx for i in inspector.get_indexes(table))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("username", sa.String(length=120), nullable=False),
            sa.Column("role_key", sa.String(length=32), nullable=False, server_default="owner"),
            sa.Column("auth_source", sa.String(length=32), nullable=False, server_default="token"),
            sa.Column("token_fingerprint", sa.String(length=64), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_seen_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("username"),
            sa.UniqueConstraint("token_fingerprint"),
        )

    if not _has_table(inspector, "auth_sessions"):
        op.create_table(
            "auth_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("subject", sa.String(length=255), nullable=False),
            sa.Column("session_type", sa.String(length=32), nullable=False, server_default="token"),
            sa.Column("issued_at", sa.DateTime(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("subject"),
        )

    if not _has_table(inspector, "user_links"):
        op.create_table(
            "user_links",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("uuid", sa.String(length=64), nullable=False),
            sa.Column("note", sa.String(length=255), nullable=False, server_default=""),
            sa.Column("tag", sa.String(length=120), nullable=False, server_default=""),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("total_traffic_gb", sa.Float(), nullable=False, server_default="0"),
            sa.Column("traffic_limit_gb", sa.Float(), nullable=True),
            sa.Column("last_ip", sa.String(length=64), nullable=True),
            sa.Column("last_activity_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("uuid"),
        )

    if not _has_table(inspector, "client_sessions"):
        op.create_table(
            "client_sessions",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("link_id", sa.Integer(), nullable=False),
            sa.Column("client_name", sa.String(length=120), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="idle"),
            sa.Column("current_ip", sa.String(length=64), nullable=False),
            sa.Column("ip_history", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("active_sessions", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("total_traffic_gb", sa.Float(), nullable=False, server_default="0"),
            sa.Column("traffic_24h_gb", sa.Float(), nullable=False, server_default="0"),
            sa.Column("traffic_7d_gb", sa.Float(), nullable=False, server_default="0"),
            sa.Column("last_activity_at", sa.DateTime(), nullable=True),
            sa.Column("events_json", sa.Text(), nullable=False, server_default="[]"),
            sa.ForeignKeyConstraint(["link_id"], ["user_links.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "traffic_snapshots"):
        op.create_table(
            "traffic_snapshots",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("period", sa.String(length=16), nullable=False, server_default="24h"),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column("traffic_gb", sa.Float(), nullable=False, server_default="0"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "server_status"):
        op.create_table(
            "server_status",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("service_status", sa.String(length=32), nullable=False, server_default="running"),
            sa.Column("xray_version", sa.String(length=32), nullable=False, server_default="1.8.13"),
            sa.Column("uptime_hours", sa.Integer(), nullable=False, server_default="24"),
            sa.Column("hostname", sa.String(length=120), nullable=False, server_default="vpn.example.com"),
            sa.Column("domain", sa.String(length=120), nullable=False, server_default="vpn.example.com"),
            sa.Column("port", sa.Integer(), nullable=False, server_default="443"),
            sa.Column("config_summary", sa.Text(), nullable=False, server_default="{}"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "admin_action_logs"):
        op.create_table(
            "admin_action_logs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(length=255), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="success"),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("meta", sa.Text(), nullable=False, server_default="{}"),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "system_events"):
        op.create_table(
            "system_events",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("level", sa.String(length=32), nullable=False, server_default="info"),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_table(inspector, "app_settings"):
        op.create_table(
            "app_settings",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("key", sa.String(length=120), nullable=False),
            sa.Column("value", sa.Text(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("key"),
        )

    inspector = sa.inspect(bind)
    if _has_table(inspector, "user_links") and not _has_index(inspector, "user_links", "ix_user_links_id"):
        op.create_index("ix_user_links_id", "user_links", ["id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_table(inspector, "user_links") and _has_index(inspector, "user_links", "ix_user_links_id"):
        op.drop_index("ix_user_links_id", table_name="user_links")

    for table in [
        "app_settings",
        "system_events",
        "admin_action_logs",
        "server_status",
        "traffic_snapshots",
        "client_sessions",
        "user_links",
        "auth_sessions",
        "users",
    ]:
        inspector = sa.inspect(bind)
        if _has_table(inspector, table):
            op.drop_table(table)
