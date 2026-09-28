"""add creator revenue ledger

Revision ID: e2f3a4b5c6d7
Revises: d9e0f1a2b3c4
"""
from alembic import op
import sqlalchemy as sa

revision = "e2f3a4b5c6d7"
down_revision = "d9e0f1a2b3c4"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "creator_revenue_ledger_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_account_id", sa.Integer(), nullable=False),
        sa.Column("hosted_book_id", sa.Integer(), nullable=False),
        sa.Column("paid_offer_id", sa.Integer(), nullable=False),
        sa.Column("buyer_user_id", sa.Integer(), nullable=True),
        sa.Column("entry_type", sa.String(length=20), nullable=False, server_default="sale"),
        sa.Column("gross_amount_minor", sa.Integer(), nullable=False),
        sa.Column("creator_share_minor", sa.Integer(), nullable=False),
        sa.Column("platform_share_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("provider_reference", sa.String(length=255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("gross_amount_minor > 0", name="ck_creator_revenue_gross_positive"),
        sa.CheckConstraint("creator_share_minor >= 0", name="ck_creator_revenue_creator_share_nonnegative"),
        sa.CheckConstraint("platform_share_minor >= 0", name="ck_creator_revenue_platform_share_nonnegative"),
        sa.CheckConstraint("creator_share_minor + platform_share_minor = gross_amount_minor", name="ck_creator_revenue_shares_balance"),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_creator_revenue_currency_length"),
        sa.ForeignKeyConstraint(["creator_account_id"], ["creator_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["hosted_book_id"], ["creator_hosted_books.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["paid_offer_id"], ["creator_paid_books.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["buyer_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_creator_revenue_provider_event"),
    )
    op.create_index("ix_creator_revenue_ledger_entries_id", "creator_revenue_ledger_entries", ["id"], unique=False)
    op.create_index("ix_creator_revenue_creator_account_id", "creator_revenue_ledger_entries", ["creator_account_id"], unique=False)
    op.create_index("ix_creator_revenue_hosted_book_id", "creator_revenue_ledger_entries", ["hosted_book_id"], unique=False)
    op.create_index("ix_creator_revenue_paid_offer_id", "creator_revenue_ledger_entries", ["paid_offer_id"], unique=False)
    op.create_index("ix_creator_revenue_buyer_user_id", "creator_revenue_ledger_entries", ["buyer_user_id"], unique=False)
    op.create_index("ix_creator_revenue_occurred_at", "creator_revenue_ledger_entries", ["occurred_at"], unique=False)

def downgrade() -> None:
    for name in ("ix_creator_revenue_occurred_at", "ix_creator_revenue_buyer_user_id", "ix_creator_revenue_paid_offer_id", "ix_creator_revenue_hosted_book_id", "ix_creator_revenue_creator_account_id", "ix_creator_revenue_ledger_entries_id"):
        op.drop_index(name, table_name="creator_revenue_ledger_entries")
    op.drop_constraint("uq_creator_revenue_provider_event", "creator_revenue_ledger_entries", type_="unique")
    op.drop_table("creator_revenue_ledger_entries")
