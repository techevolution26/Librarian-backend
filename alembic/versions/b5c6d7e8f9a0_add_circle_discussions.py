"""add circle object and page discussions

Revision ID: b5c6d7e8f9a0
Revises: a4b5c6d7e8f9
"""

from alembic import op
import sqlalchemy as sa

revision = "b5c6d7e8f9a0"
down_revision = "a4b5c6d7e8f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "circle_discussions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("circle_book_id", sa.Integer(), sa.ForeignKey("circle_books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_circle_discussions_circle_id", "circle_discussions", ["circle_id"])
    op.create_index("ix_circle_discussions_circle_book_id", "circle_discussions", ["circle_book_id"])
    op.create_index("ix_circle_discussions_book_id", "circle_discussions", ["book_id"])
    op.create_index("ix_circle_discussions_user_id", "circle_discussions", ["user_id"])
    op.create_index("ix_circle_discussions_page_number", "circle_discussions", ["page_number"])

    op.create_table(
        "circle_discussion_replies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discussion_id", sa.Integer(), sa.ForeignKey("circle_discussions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_circle_discussion_replies_discussion_id", "circle_discussion_replies", ["discussion_id"])
    op.create_index("ix_circle_discussion_replies_circle_id", "circle_discussion_replies", ["circle_id"])
    op.create_index("ix_circle_discussion_replies_user_id", "circle_discussion_replies", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_circle_discussion_replies_user_id", table_name="circle_discussion_replies")
    op.drop_index("ix_circle_discussion_replies_circle_id", table_name="circle_discussion_replies")
    op.drop_index("ix_circle_discussion_replies_discussion_id", table_name="circle_discussion_replies")
    op.drop_table("circle_discussion_replies")
    op.drop_index("ix_circle_discussions_page_number", table_name="circle_discussions")
    op.drop_index("ix_circle_discussions_user_id", table_name="circle_discussions")
    op.drop_index("ix_circle_discussions_book_id", table_name="circle_discussions")
    op.drop_index("ix_circle_discussions_circle_book_id", table_name="circle_discussions")
    op.drop_index("ix_circle_discussions_circle_id", table_name="circle_discussions")
    op.drop_table("circle_discussions")
