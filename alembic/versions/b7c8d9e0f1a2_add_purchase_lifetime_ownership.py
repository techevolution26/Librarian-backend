"""link verified purchases to durable lifetime ownership

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
"""

from alembic import op
import sqlalchemy as sa

revision = "b7c8d9e0f1a2"
down_revision = "a6b7c8d9e0f1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "creator_lifetime_access",
        sa.Column("purchase_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_creator_lifetime_access_purchase_id",
        "creator_lifetime_access",
        "purchases",
        ["purchase_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_creator_lifetime_access_purchase_id",
        "creator_lifetime_access",
        ["purchase_id"],
    )
    op.create_index(
        "ix_creator_lifetime_access_purchase_id",
        "creator_lifetime_access",
        ["purchase_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_creator_lifetime_access_purchase_id", table_name="creator_lifetime_access")
    op.drop_constraint("uq_creator_lifetime_access_purchase_id", "creator_lifetime_access", type_="unique")
    op.drop_constraint("fk_creator_lifetime_access_purchase_id", "creator_lifetime_access", type_="foreignkey")
    op.drop_column("creator_lifetime_access", "purchase_id")
