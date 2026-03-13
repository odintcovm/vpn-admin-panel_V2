"""add provider field to user_links

Revision ID: 0004_user_links_provider
Revises: 0003_core_tables_and_auth_foundation
Create Date: 2026-03-13 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_user_links_provider"
down_revision = "0003_core_tables_and_auth_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "user_links" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("user_links")}
        if "provider" not in columns:
            op.add_column("user_links", sa.Column("provider", sa.String(length=16), nullable=False, server_default="xray"))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "user_links" in inspector.get_table_names():
        columns = {c["name"] for c in inspector.get_columns("user_links")}
        if "provider" in columns:
            op.drop_column("user_links", "provider")
