"""add reader highlights

Revision ID: a1b2c3d4e5f6
Revises: 9c3d4e5f6a77
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "9c3d4e5f6a77"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "highlights",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("note_id", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("selected_text", sa.Text(), nullable=False),
        sa.Column("position", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_highlights_id"), "highlights", ["id"], unique=False)
    op.create_index(op.f("ix_highlights_user_id"), "highlights", ["user_id"], unique=False)
    op.create_index(op.f("ix_highlights_book_id"), "highlights", ["book_id"], unique=False)
    op.create_index(op.f("ix_highlights_note_id"), "highlights", ["note_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_highlights_note_id"), table_name="highlights")
    op.drop_index(op.f("ix_highlights_book_id"), table_name="highlights")
    op.drop_index(op.f("ix_highlights_user_id"), table_name="highlights")
    op.drop_index(op.f("ix_highlights_id"), table_name="highlights")
    op.drop_table("highlights")
