"""add admin book management fields

Revision ID: 78c00f2d79d5
Revises: a00fd2752cfc
Create Date: 2026-05-09 11:32:49.658383

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '78c00f2d79d5'
down_revision: Union[str, Sequence[str], None] = 'a00fd2752cfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "books",
        sa.Column(
            "visibility",
            sa.String(length=20),
            nullable=False,
            server_default="published",
        ),
    )
    op.add_column(
        "books",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "books",
        sa.Column("cover_path", sa.String(length=500), nullable=True),
    )

    op.create_table(
        "admin_activity_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["admin_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
    )


def downgrade() -> None:
    op.drop_table("admin_activity_logs")
    op.drop_column("books", "cover_path")
    op.drop_column("books", "archived_at")
    op.drop_column("books", "visibility")