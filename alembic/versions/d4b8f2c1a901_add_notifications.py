"""add notifications

Revision ID: d4b8f2c1a901
Revises: a92f1d7c44be
Create Date: 2026-09-20 23:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d4b8f2c1a901"
down_revision: Union[str, Sequence[str], None] = "a92f1d7c44be"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data_json", sa.JSON(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"], unique=False)
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"], unique=False)
    op.create_index("ix_notifications_type", "notifications", ["type"], unique=False)
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"], unique=False)
    op.create_index("ix_notifications_created_at", "notifications", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notifications_created_at", table_name="notifications")
    op.drop_index("ix_notifications_read_at", table_name="notifications")
    op.drop_index("ix_notifications_type", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_index("ix_notifications_id", table_name="notifications")
    op.drop_table("notifications")
