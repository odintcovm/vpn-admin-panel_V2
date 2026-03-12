"""rbac notifications sessions baseline"""

from alembic import op
import sqlalchemy as sa

revision = "0001_rbac_notifications_sessions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=32), nullable=False, unique=True),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=64), nullable=False, unique=True),
        sa.Column("description", sa.String(length=255), nullable=False, server_default=""),
    )
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role_key", sa.String(length=32), nullable=False),
        sa.Column("permission_key", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "session_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_name", sa.String(length=120), nullable=False),
        sa.Column("link_name", sa.String(length=120), nullable=False),
        sa.Column("source_ip", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("duration_sec", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("inbound_gb", sa.Float(), nullable=False, server_default="0"),
        sa.Column("outbound_gb", sa.Float(), nullable=False, server_default="0"),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("severity", sa.String(length=16), nullable=False, server_default="info"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("entity_type", sa.String(length=32), nullable=True),
        sa.Column("entity_id", sa.String(length=64), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("session_records")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("roles")
