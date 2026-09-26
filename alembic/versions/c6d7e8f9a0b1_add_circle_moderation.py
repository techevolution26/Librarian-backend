"""add circle moderation reports

Revision ID: c6d7e8f9a0b1
Revises: b6c7d8e9f0a1
"""
from alembic import op
import sqlalchemy as sa

revision = "c6d7e8f9a0b1"
down_revision = "b6c7d8e9f0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "circle_moderation_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reporter_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_type", sa.String(length=30), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=40), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("action", sa.String(length=30), nullable=True),
        sa.Column("action_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_circle_moderation_reports_circle_id", "circle_moderation_reports", ["circle_id"])
    op.create_index("ix_circle_moderation_reports_reporter_user_id", "circle_moderation_reports", ["reporter_user_id"])
    op.create_index("ix_circle_moderation_reports_target_type", "circle_moderation_reports", ["target_type"])
    op.create_index("ix_circle_moderation_reports_target_id", "circle_moderation_reports", ["target_id"])
    op.create_index("ix_circle_moderation_reports_status", "circle_moderation_reports", ["status"])


def downgrade() -> None:
    op.drop_index("ix_circle_moderation_reports_status", table_name="circle_moderation_reports")
    op.drop_index("ix_circle_moderation_reports_target_id", table_name="circle_moderation_reports")
    op.drop_index("ix_circle_moderation_reports_target_type", table_name="circle_moderation_reports")
    op.drop_index("ix_circle_moderation_reports_reporter_user_id", table_name="circle_moderation_reports")
    op.drop_index("ix_circle_moderation_reports_circle_id", table_name="circle_moderation_reports")
    op.drop_table("circle_moderation_reports")
