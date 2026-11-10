"""add private community resource contribution review workflow

Revision ID: f6d7e8a9b0c1
Revises: f5c8d1a2b3c4
"""
from alembic import op
import sqlalchemy as sa

revision = "f6d7e8a9b0c1"
down_revision = "f5c8d1a2b3c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resource_contributions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contributor_user_id", sa.Integer(), nullable=False),
        sa.Column("material_type", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="submitted"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=40), nullable=False, server_default="en"),
        sa.Column("genre_csv", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("subjects_csv", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("original_format", sa.String(length=30), nullable=False, server_default="born-digital"),
        sa.Column("archival_object_type", sa.String(length=30), nullable=False, server_default="document"),
        sa.Column("origin", sa.String(length=255), nullable=True),
        sa.Column("era", sa.String(length=120), nullable=True),
        sa.Column("condition_notes", sa.Text(), nullable=True),
        sa.Column("source_institution", sa.String(length=255), nullable=True),
        sa.Column("source_collection", sa.String(length=255), nullable=True),
        sa.Column("shelfmark", sa.String(length=255), nullable=True),
        sa.Column("provenance_accession_number", sa.String(length=100), nullable=True),
        sa.Column("digitized_by", sa.String(length=255), nullable=True),
        sa.Column("digitization_method", sa.String(length=255), nullable=True),
        sa.Column("scanner_device", sa.String(length=255), nullable=True),
        sa.Column("preservation_master_format", sa.String(length=100), nullable=True),
        sa.Column("derivative_format", sa.String(length=100), nullable=True),
        sa.Column("software", sa.String(length=255), nullable=True),
        sa.Column("rights_statement", sa.String(length=30), nullable=False, server_default="all-rights-reserved"),
        sa.Column("rights_holder", sa.String(length=255), nullable=True),
        sa.Column("rights_basis", sa.String(length=40), nullable=False, server_default="unknown"),
        sa.Column("rights_evidence", sa.String(length=1000), nullable=True),
        sa.Column("accuracy_attested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("contributor_note", sa.Text(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("imported_book_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["contributor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["imported_book_id"], ["books.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("imported_book_id", name="uq_resource_contribution_imported_book"),
    )
    op.create_index("ix_resource_contributions_id", "resource_contributions", ["id"])
    op.create_index("ix_resource_contributions_contributor_user_id", "resource_contributions", ["contributor_user_id"])
    op.create_index("ix_resource_contributions_status", "resource_contributions", ["status"])
    op.create_index("ix_resource_contributions_status_submitted", "resource_contributions", ["status", "submitted_at"])
    op.create_index("ix_resource_contributions_contributor_status", "resource_contributions", ["contributor_user_id", "status"])

    op.create_table(
        "resource_contribution_assets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("contribution_id", sa.Integer(), nullable=False),
        sa.Column("asset_role", sa.String(length=20), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("imported_asset_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["contribution_id"], ["resource_contributions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["imported_asset_id"], ["book_assets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_resource_contribution_assets_id", "resource_contribution_assets", ["id"])
    op.create_index("ix_resource_contribution_assets_contribution_id", "resource_contribution_assets", ["contribution_id"])
    op.create_index("ix_resource_contribution_assets_contribution_sequence", "resource_contribution_assets", ["contribution_id", "sequence"])


def downgrade() -> None:
    op.drop_index("ix_resource_contribution_assets_contribution_sequence", table_name="resource_contribution_assets")
    op.drop_index("ix_resource_contribution_assets_contribution_id", table_name="resource_contribution_assets")
    op.drop_index("ix_resource_contribution_assets_id", table_name="resource_contribution_assets")
    op.drop_table("resource_contribution_assets")
    op.drop_index("ix_resource_contributions_contributor_status", table_name="resource_contributions")
    op.drop_index("ix_resource_contributions_status_submitted", table_name="resource_contributions")
    op.drop_index("ix_resource_contributions_status", table_name="resource_contributions")
    op.drop_index("ix_resource_contributions_contributor_user_id", table_name="resource_contributions")
    op.drop_index("ix_resource_contributions_id", table_name="resource_contributions")
    op.drop_table("resource_contributions")
