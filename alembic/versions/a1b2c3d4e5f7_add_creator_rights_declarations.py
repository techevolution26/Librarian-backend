"""add creator rights declarations

Revision ID: a1b2c3d4e5f7
Revises: f1a2b3c4d5e6
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f7"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creator_rights_declarations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("creator_account_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("rights_basis", sa.String(length=40), nullable=False),
        sa.Column("rights_holder_name", sa.String(length=255), nullable=False),
        sa.Column("rights_statement", sa.Text(), nullable=False),
        sa.Column("territory", sa.String(length=255), nullable=True),
        sa.Column("license_name", sa.String(length=255), nullable=True),
        sa.Column("license_url", sa.String(length=500), nullable=True),
        sa.Column("hosting_allowed", sa.Boolean(), nullable=False),
        sa.Column("public_display_allowed", sa.Boolean(), nullable=False),
        sa.Column("download_allowed", sa.Boolean(), nullable=False),
        sa.Column("redistribution_allowed", sa.Boolean(), nullable=False),
        sa.Column("commercial_use_allowed", sa.Boolean(), nullable=False),
        sa.Column("derivative_use_allowed", sa.Boolean(), nullable=False),
        sa.Column("declaration_note", sa.Text(), nullable=True),
        sa.Column("attestation_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("declared_by_user_id", sa.Integer(), nullable=False),
        sa.Column("declared_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["creator_book_submissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["creator_account_id"], ["creator_accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["declared_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("submission_id", "version", name="uq_creator_rights_declaration_submission_version"),
    )
    op.create_index(
        "ix_creator_rights_declarations_submission_id",
        "creator_rights_declarations",
        ["submission_id"],
    )
    op.create_index(
        "ix_creator_rights_declarations_status",
        "creator_rights_declarations",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_creator_rights_declarations_status", table_name="creator_rights_declarations")
    op.drop_index("ix_creator_rights_declarations_submission_id", table_name="creator_rights_declarations")
    op.drop_table("creator_rights_declarations")
