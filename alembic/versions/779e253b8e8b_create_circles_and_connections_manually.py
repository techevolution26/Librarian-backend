"""create circles and connections manually"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "779e253b8e8b"
down_revision: Union[str, Sequence[str], None] = "69e27d982aa9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    op.create_index("ix_user_connections_requester_id", "user_connections", ["requester_id"])
    op.create_index("ix_user_connections_addressee_id", "user_connections", ["addressee_id"])
    op.create_index("ix_user_connections_status", "user_connections", ["status"])

    op.create_table(
        "circles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False, server_default="private"),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("slug", name="uq_circles_slug"),
    )
    op.create_index("ix_circles_name", "circles", ["name"])
    op.create_index("ix_circles_slug", "circles", ["slug"])
    op.create_index("ix_circles_owner_id", "circles", ["owner_id"])

    op.create_table(
        "circle_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("invited_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("circle_id", "user_id", name="uq_circle_member_pair"),
    )
    op.create_index("ix_circle_members_circle_id", "circle_members", ["circle_id"])
    op.create_index("ix_circle_members_user_id", "circle_members", ["user_id"])

    op.create_table(
        "circle_books",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title_override", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("target_end_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("circle_id", "book_id", name="uq_circle_book_pair"),
    )
    op.create_index("ix_circle_books_circle_id", "circle_books", ["circle_id"])
    op.create_index("ix_circle_books_book_id", "circle_books", ["book_id"])
    op.create_index("ix_circle_books_status", "circle_books", ["status"])

    op.create_table(
        "circle_progress_updates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("circle_book_id", sa.Integer(), sa.ForeignKey("circle_books.id", ondelete="CASCADE"), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("library_item_id", sa.Integer(), sa.ForeignKey("library_items.id", ondelete="SET NULL"), nullable=True),
        sa.Column("progress_percent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_page", sa.Integer(), nullable=True),
        sa.Column("bookmark_page", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False, server_default="circle"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_circle_progress_updates_circle_id", "circle_progress_updates", ["circle_id"])
    op.create_index("ix_circle_progress_updates_circle_book_id", "circle_progress_updates", ["circle_book_id"])
    op.create_index("ix_circle_progress_updates_user_id", "circle_progress_updates", ["user_id"])
    op.create_index("ix_circle_progress_updates_created_at", "circle_progress_updates", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_circle_progress_updates_created_at", table_name="circle_progress_updates")
    op.drop_index("ix_circle_progress_updates_user_id", table_name="circle_progress_updates")
    op.drop_index("ix_circle_progress_updates_circle_book_id", table_name="circle_progress_updates")
    op.drop_index("ix_circle_progress_updates_circle_id", table_name="circle_progress_updates")
    op.drop_table("circle_progress_updates")

    op.drop_index("ix_circle_books_status", table_name="circle_books")
    op.drop_index("ix_circle_books_book_id", table_name="circle_books")
    op.drop_index("ix_circle_books_circle_id", table_name="circle_books")
    op.drop_table("circle_books")

    op.drop_index("ix_circle_members_user_id", table_name="circle_members")
    op.drop_index("ix_circle_members_circle_id", table_name="circle_members")
    op.drop_table("circle_members")

    op.drop_index("ix_circles_owner_id", table_name="circles")
    op.drop_index("ix_circles_slug", table_name="circles")
    op.drop_index("ix_circles_name", table_name="circles")
    op.drop_table("circles")

    op.drop_index("ix_user_connections_status", table_name="user_connections")
    op.drop_index("ix_user_connections_addressee_id", table_name="user_connections")
    op.drop_index("ix_user_connections_requester_id", table_name="user_connections")
    op.drop_table("user_connections")