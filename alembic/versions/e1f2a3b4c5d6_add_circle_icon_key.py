"""add circle icon key

Revision ID: e1f2a3b4c5d6
Revises: d8e9f0a1b2c3
"""
from alembic import op
import sqlalchemy as sa

revision = "e1f2a3b4c5d6"
down_revision = "d8e9f0a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("circles", sa.Column("icon_key", sa.String(length=40), nullable=True))
    op.execute("UPDATE circles SET icon_key = 'book-open' WHERE icon_key IS NULL")
    op.alter_column("circles", "icon_key", nullable=False, server_default="book-open")


def downgrade() -> None:
    op.drop_column("circles", "icon_key")
