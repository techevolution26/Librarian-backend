"""add formal quote references

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
"""
from alembic import op
import sqlalchemy as sa

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quote_references",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("highlight_id", sa.Integer(), nullable=True),
        sa.Column("note_id", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("locator", sa.Text(), nullable=True),
        sa.Column("quote_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["highlight_id"], ["highlights.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_quote_references_id"), "quote_references", ["id"], unique=False)
    op.create_index(op.f("ix_quote_references_user_id"), "quote_references", ["user_id"], unique=False)
    op.create_index(op.f("ix_quote_references_book_id"), "quote_references", ["book_id"], unique=False)
    op.create_index(op.f("ix_quote_references_highlight_id"), "quote_references", ["highlight_id"], unique=False)
    op.create_index(op.f("ix_quote_references_note_id"), "quote_references", ["note_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_quote_references_note_id"), table_name="quote_references")
    op.drop_index(op.f("ix_quote_references_highlight_id"), table_name="quote_references")
    op.drop_index(op.f("ix_quote_references_book_id"), table_name="quote_references")
    op.drop_index(op.f("ix_quote_references_user_id"), table_name="quote_references")
    op.drop_index(op.f("ix_quote_references_id"), table_name="quote_references")
    op.drop_table("quote_references")
