"""add creator paid book offers

Revision ID: c8d9e0f1a2b3
Revises: a2b3c4d5e6f8
"""
from alembic import op
import sqlalchemy as sa

revision = "c8d9e0f1a2b3"
down_revision = "a2b3c4d5e6f8"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "creator_paid_books",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hosted_book_id", sa.Integer(), nullable=False),
        sa.Column("creator_account_id", sa.Integer(), nullable=False),
        sa.Column("price_amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("price_amount_minor > 0", name="ck_creator_paid_books_price_positive"),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_creator_paid_books_currency_length"),
        sa.ForeignKeyConstraint(["creator_account_id"], ["creator_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hosted_book_id"], ["creator_hosted_books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hosted_book_id", name="uq_creator_paid_books_hosted_book_id"),
    )
    op.create_index("ix_creator_paid_books_id", "creator_paid_books", ["id"], unique=False)
    op.create_index("ix_creator_paid_books_creator_account_id", "creator_paid_books", ["creator_account_id"], unique=False)
    op.create_index("ix_creator_paid_books_status", "creator_paid_books", ["status"], unique=False)

def downgrade() -> None:
    op.drop_index("ix_creator_paid_books_status", table_name="creator_paid_books")
    op.drop_index("ix_creator_paid_books_creator_account_id", table_name="creator_paid_books")
    op.drop_index("ix_creator_paid_books_id", table_name="creator_paid_books")
    op.drop_table("creator_paid_books")
