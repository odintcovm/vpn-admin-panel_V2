"""notification reads table for per-principal state

Revision ID: 0002_notification_reads_and_rbac_hardening
Revises: 0001_rbac_notifications_sessions
Create Date: 2026-03-12 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_notification_reads_and_rbac_hardening"
down_revision = "0001_rbac_notifications_sessions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_reads",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.Integer(), nullable=False),
        sa.Column("principal_id", sa.String(length=128), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["notification_id"], ["notifications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notification_id", "principal_id", name="uq_notification_reads_notification_principal"),
    )
    op.create_index("ix_notification_reads_notification_id", "notification_reads", ["notification_id"], unique=False)
    op.create_index("ix_notification_reads_principal_id", "notification_reads", ["principal_id"], unique=False)
    op.create_index("ix_notification_reads_read_at", "notification_reads", ["read_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notification_reads_read_at", table_name="notification_reads")
    op.drop_index("ix_notification_reads_principal_id", table_name="notification_reads")
    op.drop_index("ix_notification_reads_notification_id", table_name="notification_reads")
    op.drop_table("notification_reads")
