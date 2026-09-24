"""add circle visibility and join rules

Revision ID: c7d8e9f0a1b2
Revises: b2c3d4e5f6a7
"""
from alembic import op
import sqlalchemy as sa

revision = "c7d8e9f0a1b2"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("circles", sa.Column("join_policy", sa.String(length=20), nullable=False, server_default="invite_only"))
    op.add_column("circles", sa.Column("join_conditions", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    op.alter_column("circles", "visibility", server_default="private")

def downgrade() -> None:
    op.drop_column("circles", "join_conditions")
    op.drop_column("circles", "join_policy")
