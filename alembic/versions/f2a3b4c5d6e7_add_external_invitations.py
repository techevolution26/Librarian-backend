"""add external invitation domain

Revision ID: f2a3b4c5d6e7
Revises: e1f2a3b4c5d6
"""

from alembic import op
import sqlalchemy as sa

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invitations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invitation_type", sa.String(length=20), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("circle_id", sa.Integer(), sa.ForeignKey("circles.id", ondelete="CASCADE"), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("uses", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("token_hash", name="uq_invitations_token_hash"),
    )
    op.create_index("ix_invitations_invitation_type", "invitations", ["invitation_type"])
    op.create_index("ix_invitations_circle_id", "invitations", ["circle_id"])
    op.create_index("ix_invitations_created_by_user_id", "invitations", ["created_by_user_id"])
    op.create_index("ix_invitations_expires_at", "invitations", ["expires_at"])
    op.create_index("ix_invitations_status", "invitations", ["status"])

    op.create_table(
        "invitation_uses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invitation_id", sa.Integer(), sa.ForeignKey("invitations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_invitation_uses_invitation_id", "invitation_uses", ["invitation_id"])
    op.create_index("ix_invitation_uses_user_id", "invitation_uses", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_invitation_uses_user_id", table_name="invitation_uses")
    op.drop_index("ix_invitation_uses_invitation_id", table_name="invitation_uses")
    op.drop_table("invitation_uses")
    op.drop_index("ix_invitations_status", table_name="invitations")
    op.drop_index("ix_invitations_expires_at", table_name="invitations")
    op.drop_index("ix_invitations_created_by_user_id", table_name="invitations")
    op.drop_index("ix_invitations_circle_id", table_name="invitations")
    op.drop_index("ix_invitations_invitation_type", table_name="invitations")
    op.drop_table("invitations")
