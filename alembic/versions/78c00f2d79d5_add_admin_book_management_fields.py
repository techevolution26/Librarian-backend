"""add admin book management fields

Revision ID: 78c00f2d79d5
Revises: a00fd2752cfc
Create Date: 2026-05-09 11:32:49.658383

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = '78c00f2d79d5'
down_revision: Union[str, Sequence[str], None] = 'a00fd2752cfc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def has_table(table_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)

    if table_name not in inspector.get_table_names():
        return False

    columns = inspector.get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def upgrade() -> None:
    if not has_column("books", "visibility"):
        op.add_column(
            "books",
            sa.Column(
                "visibility",
                sa.String(length=20),
                nullable=False,
                server_default="published",
            ),
        )

    if not has_column("books", "archived_at"):
        op.add_column(
            "books",
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        )

    if not has_column("books", "cover_path"):
        op.add_column(
            "books",
            sa.Column("cover_path", sa.String(length=500), nullable=True),
        )

    if not has_table("admin_activity_logs"):
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
    if has_table("admin_activity_logs"):
        op.drop_table("admin_activity_logs")

    if has_column("books", "cover_path"):
        op.drop_column("books", "cover_path")

    if has_column("books", "archived_at"):
        op.drop_column("books", "archived_at")

    if has_column("books", "visibility"):
        op.drop_column("books", "visibility")