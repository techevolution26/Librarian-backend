"""add subscription plan catalogue

Revision ID: b6c7d8e9f0a1
Revises: a5b6c7d8e9f0
"""
from alembic import op
import sqlalchemy as sa

revision = "f5a6b7c8d9e0"
down_revision = "a5b6c7d8e9f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("price_amount_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="usd"),
        sa.Column("billing_interval", sa.String(length=20), nullable=False, server_default="none"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("price_amount_minor >= 0", name="ck_subscription_plan_price_nonnegative"),
        sa.CheckConstraint(
            "billing_interval IN ('none', 'month', 'year')",
            name="ck_subscription_plan_billing_interval",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived')",
            name="ck_subscription_plan_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_subscription_plans_code"),
    )
    op.create_index("ix_subscription_plans_id", "subscription_plans", ["id"], unique=False)
    op.create_index("ix_subscription_plans_status", "subscription_plans", ["status"], unique=False)
    op.create_index("ix_subscription_plans_sort_order", "subscription_plans", ["sort_order"], unique=False)


def downgrade() -> None:
    for name in ("ix_subscription_plans_sort_order", "ix_subscription_plans_status", "ix_subscription_plans_id"):
        op.drop_index(name, table_name="subscription_plans")
    op.drop_table("subscription_plans")
