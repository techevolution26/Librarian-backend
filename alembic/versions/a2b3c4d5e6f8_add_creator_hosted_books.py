"""add creator hosted books

Revision ID: a2b3c4d5e6f8
Revises: a1b2c3d4e5f7
"""
from alembic import op
import sqlalchemy as sa

revision = "a2b3c4d5e6f8"
down_revision = "a1b2c3d4e5f7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creator_hosted_books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("creator_account_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["creator_book_submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_account_id"], ["creator_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id", name="uq_creator_hosted_books_submission_id"),
        sa.UniqueConstraint("book_id", name="uq_creator_hosted_books_book_id"),
    )
    op.create_index("ix_creator_hosted_books_id", "creator_hosted_books", ["id"])
    op.create_index("ix_creator_hosted_books_creator_account_id", "creator_hosted_books", ["creator_account_id"])
    op.create_index("ix_creator_hosted_books_status", "creator_hosted_books", ["status"])


def downgrade() -> None:
    op.drop_index("ix_creator_hosted_books_status", table_name="creator_hosted_books")
    op.drop_index("ix_creator_hosted_books_creator_account_id", table_name="creator_hosted_books")
    op.drop_index("ix_creator_hosted_books_id", table_name="creator_hosted_books")
    op.drop_table("creator_hosted_books")
