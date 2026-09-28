"""add creator accounts

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
"""
from alembic import op
import sqlalchemy as sa

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creator_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("profile_image_url", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_creator_accounts_user_id"),
        sa.UniqueConstraint("slug", name="uq_creator_accounts_slug"),
    )
    op.create_index("ix_creator_accounts_id", "creator_accounts", ["id"])
    op.create_index("ix_creator_accounts_status", "creator_accounts", ["status"])
    op.create_index("ix_creator_accounts_public", "creator_accounts", ["is_public"])


def downgrade() -> None:
    op.drop_index("ix_creator_accounts_public", table_name="creator_accounts")
    op.drop_index("ix_creator_accounts_status", table_name="creator_accounts")
    op.drop_index("ix_creator_accounts_id", table_name="creator_accounts")
    op.drop_table("creator_accounts")
