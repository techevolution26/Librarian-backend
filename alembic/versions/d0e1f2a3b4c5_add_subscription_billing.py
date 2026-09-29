"""add subscription billing state

Revision ID: c9d0e1f2a3b4
Revises: f5a6b7c8d9e0
"""
from alembic import op
import sqlalchemy as sa

revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subscription_plans", sa.Column("stripe_product_id", sa.String(length=255), nullable=True))
    op.add_column("subscription_plans", sa.Column("stripe_price_id", sa.String(length=255), nullable=True))
    op.create_unique_constraint("uq_subscription_plans_stripe_price_id", "subscription_plans", ["stripe_price_id"])

    op.create_table(
        "billing_customers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False, server_default="stripe"),
        sa.Column("provider_customer_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider", name="uq_billing_customer_user_provider"),
        sa.UniqueConstraint("provider", "provider_customer_id", name="uq_billing_customer_provider_id"),
    )
    op.create_index("ix_billing_customers_id", "billing_customers", ["id"], unique=False)
    op.create_index("ix_billing_customers_user_id", "billing_customers", ["user_id"], unique=False)

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("billing_customer_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False, server_default="stripe"),
        sa.Column("provider_subscription_id", sa.String(length=255), nullable=False),
        sa.Column("provider_price_id", sa.String(length=255), nullable=False),
        sa.Column("provider_product_id", sa.String(length=255), nullable=True),
        sa.Column("checkout_session_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_invoice_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("quantity > 0", name="ck_subscription_quantity_positive"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["billing_customer_id"], ["billing_customers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_subscription_id", name="uq_subscription_provider_id"),
    )
    op.create_index("ix_subscriptions_id", "subscriptions", ["id"], unique=False)
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"], unique=False)
    op.create_index("ix_subscriptions_user_status", "subscriptions", ["user_id", "status"], unique=False)
    op.create_index("ix_subscriptions_customer_id", "subscriptions", ["billing_customer_id"], unique=False)
    op.create_index("ix_subscriptions_checkout_session_id", "subscriptions", ["checkout_session_id"], unique=False)

    op.create_table(
        "billing_webhook_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False, server_default="stripe"),
        sa.Column("provider_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=120), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_event_id", name="uq_billing_webhook_provider_event"),
    )
    op.create_index("ix_billing_webhook_events_id", "billing_webhook_events", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_billing_webhook_events_id", table_name="billing_webhook_events")
    op.drop_table("billing_webhook_events")
    for name in (
        "ix_subscriptions_checkout_session_id",
        "ix_subscriptions_customer_id",
        "ix_subscriptions_user_status",
        "ix_subscriptions_user_id",
        "ix_subscriptions_id",
    ):
        op.drop_index(name, table_name="subscriptions")
    op.drop_table("subscriptions")
    op.drop_index("ix_billing_customers_user_id", table_name="billing_customers")
    op.drop_index("ix_billing_customers_id", table_name="billing_customers")
    op.drop_table("billing_customers")
    op.drop_constraint("uq_subscription_plans_stripe_price_id", "subscription_plans", type_="unique")
    op.drop_column("subscription_plans", "stripe_price_id")
    op.drop_column("subscription_plans", "stripe_product_id")
