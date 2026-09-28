"""add creator book submissions

Revision ID: f1a2b3c4d5e6
Revises: e3f4a5b6c7d8
"""
from alembic import op
import sqlalchemy as sa

revision = "f1a2b3c4d5e6"
down_revision = "e3f4a5b6c7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creator_book_submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_account_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=40), nullable=False),
        sa.Column("genre_csv", sa.String(length=255), nullable=False),
        sa.Column("creator_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["creator_account_id"], ["creator_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_creator_book_submissions_id", "creator_book_submissions", ["id"])
    op.create_index("ix_creator_book_submissions_creator_account_id", "creator_book_submissions", ["creator_account_id"])
    op.create_index("ix_creator_book_submissions_status", "creator_book_submissions", ["status"])
    op.create_index("ix_creator_book_submissions_submitted_at", "creator_book_submissions", ["submitted_at"])


def downgrade() -> None:
    op.drop_index("ix_creator_book_submissions_submitted_at", table_name="creator_book_submissions")
    op.drop_index("ix_creator_book_submissions_status", table_name="creator_book_submissions")
    op.drop_index("ix_creator_book_submissions_creator_account_id", table_name="creator_book_submissions")
    op.drop_index("ix_creator_book_submissions_id", table_name="creator_book_submissions")
    op.drop_table("creator_book_submissions")
