"""add circles and connections

Revision ID: 69e27d982aa9
Revises:
Create Date: 2026-04-22 20:48:43.398480

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '69e27d982aa9'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # ----------------------
    # USER CONNECTIONS
    # ----------------------
    op.create_table(
        "user_connections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("requester_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("addressee_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("relationship_type", sa.String(length=20), nullable=False, server_default="friend"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("requester_id", "addressee_id", name="uq_user_connection_pair"),
    )

    # ----------------------
    # CIRCLES
    # ----------------------
    op.create_table(
        "circles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("slug", sa.String(160), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="private"),
        sa.Column("avatar_url", sa.String(500), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ----------------------
    # CIRCLE MEMBERS
    # ----------------------
    op.create_table(
        "circle_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("invited_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("joined_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("circle_id", "user_id", name="uq_circle_member_pair"),
    )

    # ----------------------
    # CIRCLE BOOKS
    # ----------------------
    op.create_table(
        "circle_books",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title_override", sa.String(255)),
        sa.Column("description", sa.Text()),
        sa.Column("start_date", sa.Date()),
        sa.Column("target_end_date", sa.Date()),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("circle_id", "book_id", name="uq_circle_book_pair"),
    )

    # ----------------------
    # PROGRESS UPDATES
    # ----------------------
    op.create_table(
        "circle_progress_updates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("circle_book_id", sa.Integer(), sa.ForeignKey("circle_books.id", ondelete="CASCADE")),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("library_item_id", sa.Integer(), sa.ForeignKey("library_items.id", ondelete="SET NULL")),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_page", sa.Integer()),
        sa.Column("bookmark_page", sa.Integer()),
        sa.Column("note", sa.Text()),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="circle"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("circle_progress_updates")
    op.drop_table("circle_books")
    op.drop_table("circle_members")
    op.drop_table("circles")
    op.drop_table("user_connections")