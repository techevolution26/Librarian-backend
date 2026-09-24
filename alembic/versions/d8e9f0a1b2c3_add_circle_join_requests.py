"""add circle join requests

Revision ID: d8e9f0a1b2c3
Revises: c7d8e9f0a1b2
"""
from alembic import op
import sqlalchemy as sa

revision = "d8e9f0a1b2c3"
down_revision = "c7d8e9f0a1b2"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "circle_join_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("circle_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("answers", sa.JSON(), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["circle_id"], ["circles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_circle_join_requests_circle_id", "circle_join_requests", ["circle_id"], unique=False)
    op.create_index("ix_circle_join_requests_user_id", "circle_join_requests", ["user_id"], unique=False)
    op.create_index("ix_circle_join_requests_status", "circle_join_requests", ["status"], unique=False)

def downgrade() -> None:
    op.drop_index("ix_circle_join_requests_status", table_name="circle_join_requests")
    op.drop_index("ix_circle_join_requests_user_id", table_name="circle_join_requests")
    op.drop_index("ix_circle_join_requests_circle_id", table_name="circle_join_requests")
    op.drop_table("circle_join_requests")
