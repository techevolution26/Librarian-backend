"""add one-time purchase records

Revision ID: a6b7c8d9e0f1
Revises: d0e1f2a3b4c5
"""
from alembic import op
import sqlalchemy as sa

revision = "a6b7c8d9e0f1"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "purchases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("paid_offer_id", sa.Integer(), nullable=False),
        sa.Column("hosted_book_id", sa.Integer(), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False, server_default="stripe"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.String(length=255), nullable=False),
        sa.Column("provider_checkout_session_id", sa.String(length=255), nullable=True),
        sa.Column("provider_payment_intent_id", sa.String(length=255), nullable=True),
        sa.Column("provider_customer_id", sa.String(length=255), nullable=True),
        sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("refunded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("amount_minor > 0", name="ck_purchase_amount_positive"),
        sa.CheckConstraint("char_length(currency) = 3", name="ck_purchase_currency_length"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["paid_offer_id"], ["creator_paid_books.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["hosted_book_id"], ["creator_hosted_books.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_checkout_session_id", name="uq_purchase_provider_checkout_session"),
        sa.UniqueConstraint("provider", "provider_payment_intent_id", name="uq_purchase_provider_payment_intent"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_purchase_user_idempotency"),
    )
    op.create_index("ix_purchases_id", "purchases", ["id"], unique=False)
    op.create_index("ix_purchases_user_id", "purchases", ["user_id"], unique=False)
    op.create_index("ix_purchases_paid_offer_id", "purchases", ["paid_offer_id"], unique=False)
    op.create_index("ix_purchases_status", "purchases", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_purchases_status", table_name="purchases")
    op.drop_index("ix_purchases_paid_offer_id", table_name="purchases")
    op.drop_index("ix_purchases_user_id", table_name="purchases")
    op.drop_index("ix_purchases_id", table_name="purchases")
    op.drop_table("purchases")
