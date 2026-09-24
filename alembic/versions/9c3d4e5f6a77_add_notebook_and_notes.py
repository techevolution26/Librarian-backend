"""add notebook and notes

Revision ID: 9c3d4e5f6a77
Revises: 8b2c3d4e5f66
"""
from alembic import op
import sqlalchemy as sa

revision = "9c3d4e5f6a77"
down_revision = "8b2c3d4e5f66"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notebooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_notebooks_id", "notebooks", ["id"])
    op.create_index("ix_notebooks_user_id", "notebooks", ["user_id"], unique=True)

    op.create_table(
        "notes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("notebook_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=True),
        sa.Column("bookmark_id", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["notebook_id"], ["notebooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bookmark_id"], ["bookmarks.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_notes_id", "notes", ["id"])
    op.create_index("ix_notes_notebook_id", "notes", ["notebook_id"])
    op.create_index("ix_notes_book_id", "notes", ["book_id"])
    op.create_index("ix_notes_bookmark_id", "notes", ["bookmark_id"])


def downgrade() -> None:
    op.drop_index("ix_notes_bookmark_id", table_name="notes")
    op.drop_index("ix_notes_book_id", table_name="notes")
    op.drop_index("ix_notes_notebook_id", table_name="notes")
    op.drop_index("ix_notes_id", table_name="notes")
    op.drop_table("notes")
    op.drop_index("ix_notebooks_user_id", table_name="notebooks")
    op.drop_index("ix_notebooks_id", table_name="notebooks")
    op.drop_table("notebooks")
