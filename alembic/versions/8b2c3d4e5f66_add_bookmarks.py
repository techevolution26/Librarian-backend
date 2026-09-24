"""add multiple reader bookmarks

Revision ID: 8b2c3d4e5f66
Revises: 7a1b2c3d4e55
Create Date: 2026-09-24
"""

from alembic import op
import sqlalchemy as sa

revision = "8b2c3d4e5f66"
down_revision = "7a1b2c3d4e55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bookmarks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("position", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bookmarks_id", "bookmarks", ["id"], unique=False)
    op.create_index("ix_bookmarks_user_id", "bookmarks", ["user_id"], unique=False)
    op.create_index("ix_bookmarks_book_id", "bookmarks", ["book_id"], unique=False)
    op.create_index("ix_bookmarks_user_book_page", "bookmarks", ["user_id", "book_id", "page_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_bookmarks_user_book_page", table_name="bookmarks")
    op.drop_index("ix_bookmarks_book_id", table_name="bookmarks")
    op.drop_index("ix_bookmarks_user_id", table_name="bookmarks")
    op.drop_index("ix_bookmarks_id", table_name="bookmarks")
    op.drop_table("bookmarks")
