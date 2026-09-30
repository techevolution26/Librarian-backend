"""add institutional plans and organization access

Revision ID: c8d9e0f1a2b3
Revises: b7c8d9e0f1a2
"""
from alembic import op
import sqlalchemy as sa

revision = "d1e2f3a4b5c6"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("subscription_plans", sa.Column("plan_type", sa.String(length=20), nullable=False, server_default="individual"))
    op.add_column("subscription_plans", sa.Column("seat_limit", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_subscription_plan_type",
        "subscription_plans",
        "plan_type IN ('individual', 'institutional')",
    )
    op.create_check_constraint(
        "ck_subscription_plan_seat_limit_positive",
        "subscription_plans",
        "seat_limit IS NULL OR seat_limit > 0",
    )

    op.create_table(
        "institutions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("slug", name="uq_institutions_slug"),
    )
    op.create_index("ix_institutions_id", "institutions", ["id"])
    op.create_index("ix_institutions_status", "institutions", ["status"])
    op.create_index("ix_institutions_owner_user_id", "institutions", ["owner_user_id"])

    op.create_table(
        "institution_memberships",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False, server_default="member"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("institution_id", "user_id", name="uq_institution_membership"),
    )
    op.create_index("ix_institution_memberships_id", "institution_memberships", ["id"])
    op.create_index("ix_institution_memberships_user_status", "institution_memberships", ["user_id", "status"])
    op.create_index("ix_institution_memberships_institution_status", "institution_memberships", ["institution_id", "status"])

    op.create_table(
        "institution_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("institution_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_institution_subscriptions_id", "institution_subscriptions", ["id"])
    op.create_index("ix_institution_subscriptions_institution_status", "institution_subscriptions", ["institution_id", "status"])
    op.create_index("ix_institution_subscriptions_plan_id", "institution_subscriptions", ["plan_id"])


def downgrade() -> None:
    op.drop_index("ix_institution_subscriptions_plan_id", table_name="institution_subscriptions")
    op.drop_index("ix_institution_subscriptions_institution_status", table_name="institution_subscriptions")
    op.drop_index("ix_institution_subscriptions_id", table_name="institution_subscriptions")
    op.drop_table("institution_subscriptions")
    op.drop_index("ix_institution_memberships_institution_status", table_name="institution_memberships")
    op.drop_index("ix_institution_memberships_user_status", table_name="institution_memberships")
    op.drop_index("ix_institution_memberships_id", table_name="institution_memberships")
    op.drop_table("institution_memberships")
    op.drop_index("ix_institutions_owner_user_id", table_name="institutions")
    op.drop_index("ix_institutions_status", table_name="institutions")
    op.drop_index("ix_institutions_id", table_name="institutions")
    op.drop_table("institutions")
    op.drop_constraint("ck_subscription_plan_seat_limit_positive", "subscription_plans", type_="check")
    op.drop_constraint("ck_subscription_plan_type", "subscription_plans", type_="check")
    op.drop_column("subscription_plans", "seat_limit")
    op.drop_column("subscription_plans", "plan_type")
