"""add subscription plan feature limits

Revision ID: c9d0e1f2a3b4
Revises: f5a6b7c8d9e0
"""
from alembic import op
import sqlalchemy as sa

revision = "c9d0e1f2a3b4"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_plan_feature_limits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("feature_key", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("limit_value", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "limit_value IS NULL OR limit_value >= 0",
            name="ck_subscription_plan_feature_limit_nonnegative",
        ),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_id", "feature_key", name="uq_subscription_plan_feature_limit"),
    )
    op.create_index(
        "ix_subscription_plan_feature_limits_id",
        "subscription_plan_feature_limits",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_plan_feature_limits_plan_id",
        "subscription_plan_feature_limits",
        ["plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_plan_feature_limits_feature_key",
        "subscription_plan_feature_limits",
        ["feature_key"],
        unique=False,
    )


def downgrade() -> None:
    for name in (
        "ix_subscription_plan_feature_limits_feature_key",
        "ix_subscription_plan_feature_limits_plan_id",
        "ix_subscription_plan_feature_limits_id",
    ):
        op.drop_index(name, table_name="subscription_plan_feature_limits")
    op.drop_table("subscription_plan_feature_limits")
