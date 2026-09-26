"""add circle community annotations

Revision ID: a4b5c6d7e8f9
Revises: f2a3b4c5d6e7
"""

from alembic import op
import sqlalchemy as sa

revision = "a4b5c6d7e8f9"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "circle_annotations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("circle_book_id", sa.Integer(), sa.ForeignKey("circle_books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("selected_text", sa.Text(), nullable=True),
        sa.Column("position", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(length=20), nullable=False, server_default="circle"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_circle_annotations_circle_id", "circle_annotations", ["circle_id"])
    op.create_index("ix_circle_annotations_circle_book_id", "circle_annotations", ["circle_book_id"])
    op.create_index("ix_circle_annotations_book_id", "circle_annotations", ["book_id"])
    op.create_index("ix_circle_annotations_user_id", "circle_annotations", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_circle_annotations_user_id", table_name="circle_annotations")
    op.drop_index("ix_circle_annotations_book_id", table_name="circle_annotations")
    op.drop_index("ix_circle_annotations_circle_book_id", table_name="circle_annotations")
    op.drop_index("ix_circle_annotations_circle_id", table_name="circle_annotations")
    op.drop_table("circle_annotations")
