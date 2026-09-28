"""add creator payout settlement records

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
"""
from alembic import op
import sqlalchemy as sa

revision = "f3a4b5c6d7e8"
down_revision = "e2f3a4b5c6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creator_payouts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_account_id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("requested_amount_minor", sa.Integer(), nullable=False),
        sa.Column("eligible_amount_minor", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="requested"),
        sa.Column("provider", sa.String(length=40), nullable=True),
        sa.Column("provider_payout_id", sa.String(length=255), nullable=True),
        sa.Column("provider_reference", sa.String(length=255), nullable=True),
        sa.Column("provider_idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("failure_code", sa.String(length=80), nullable=True),
        sa.Column("failure_message", sa.String(length=500), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processing_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("requested_amount_minor > 0", name="ck_creator_payout_requested_positive"),
        sa.CheckConstraint("eligible_amount_minor > 0", name="ck_creator_payout_eligible_positive"),
        sa.CheckConstraint("requested_amount_minor <= eligible_amount_minor", name="ck_creator_payout_request_within_eligibility"),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_creator_payout_currency_length"),
        sa.CheckConstraint("attempt_count >= 0", name="ck_creator_payout_attempt_nonnegative"),
        sa.ForeignKeyConstraint(["creator_account_id"], ["creator_accounts.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("creator_account_id", "idempotency_key", name="uq_creator_payout_creator_idempotency"),
        sa.UniqueConstraint("provider_idempotency_key", name="uq_creator_payout_provider_idempotency"),
    )
    op.create_index("ix_creator_payouts_id", "creator_payouts", ["id"], unique=False)
    op.create_index("ix_creator_payout_creator_account_id", "creator_payouts", ["creator_account_id"], unique=False)
    op.create_index("ix_creator_payout_status", "creator_payouts", ["status"], unique=False)
    op.create_index("ix_creator_payout_currency", "creator_payouts", ["currency"], unique=False)

    op.create_table(
        "creator_payout_allocations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("payout_id", sa.Integer(), nullable=False),
        sa.Column("ledger_entry_id", sa.Integer(), nullable=False),
        sa.Column("allocated_amount_minor", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("allocated_amount_minor > 0", name="ck_creator_payout_allocation_positive"),
        sa.ForeignKeyConstraint(["payout_id"], ["creator_payouts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ledger_entry_id"], ["creator_revenue_ledger_entries.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payout_id", "ledger_entry_id", name="uq_creator_payout_allocation_entry"),
    )
    op.create_index("ix_creator_payout_allocations_id", "creator_payout_allocations", ["id"], unique=False)
    op.create_index("ix_creator_payout_allocation_payout_id", "creator_payout_allocations", ["payout_id"], unique=False)
    op.create_index("ix_creator_payout_allocation_ledger_entry_id", "creator_payout_allocations", ["ledger_entry_id"], unique=False)


def downgrade() -> None:
    for name in ("ix_creator_payout_allocation_ledger_entry_id", "ix_creator_payout_allocation_payout_id", "ix_creator_payout_allocations_id"):
        op.drop_index(name, table_name="creator_payout_allocations")
    op.drop_table("creator_payout_allocations")
    for name in ("ix_creator_payout_currency", "ix_creator_payout_status", "ix_creator_payout_creator_account_id", "ix_creator_payouts_id"):
        op.drop_index(name, table_name="creator_payouts")
    op.drop_constraint("uq_creator_payout_provider_idempotency", "creator_payouts", type_="unique")
    op.drop_constraint("uq_creator_payout_creator_idempotency", "creator_payouts", type_="unique")
    op.drop_table("creator_payouts")
