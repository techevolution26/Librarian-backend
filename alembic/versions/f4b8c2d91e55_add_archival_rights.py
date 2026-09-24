"""add structured archival rights

Revision ID: f4b8c2d91e55
Revises: e7f2a6b91c44
Create Date: 2026-09-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f4b8c2d91e55"
down_revision: Union[str, Sequence[str], None] = "e7f2a6b91c44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "archival_rights",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("archival_object_id", sa.Integer(), nullable=False),
        sa.Column("rights_holder", sa.String(length=255), nullable=True),
        sa.Column("rights_statement", sa.Text(), nullable=True),
        sa.Column("license", sa.String(length=255), nullable=True),
        sa.Column("copyright_status", sa.String(length=40), nullable=True),
        sa.Column("jurisdiction", sa.String(length=120), nullable=True),
        sa.Column("rights_source", sa.String(length=500), nullable=True),
        sa.Column("access_conditions", sa.Text(), nullable=True),
        sa.Column("reproduction_conditions", sa.Text(), nullable=True),
        sa.Column("attribution", sa.Text(), nullable=True),
        sa.Column("view_allowed", sa.Boolean(), nullable=True),
        sa.Column("download_allowed", sa.Boolean(), nullable=True),
        sa.Column("redistribution_allowed", sa.Boolean(), nullable=True),
        sa.Column("commercial_use_allowed", sa.Boolean(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["archival_object_id"], ["archival_objects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("archival_object_id", name="uq_archival_rights_archival_object_id"),
    )
    op.create_index("ix_archival_rights_id", "archival_rights", ["id"])
    op.create_index("ix_archival_rights_archival_object_id", "archival_rights", ["archival_object_id"], unique=True)

    # Preserve the existing Book rights statement without inventing new legal
    # conclusions. The remaining structured fields intentionally stay NULL
    # until an administrator has verified them.
    op.execute(sa.text("""
        INSERT INTO archival_rights (archival_object_id, rights_statement)
        SELECT b.archival_object_id, NULLIF(TRIM(b.rights_statement), '')
        FROM books b
        WHERE b.archival_object_id IS NOT NULL
    """))


def downgrade() -> None:
    op.drop_index("ix_archival_rights_archival_object_id", table_name="archival_rights")
    op.drop_index("ix_archival_rights_id", table_name="archival_rights")
    op.drop_constraint("uq_archival_rights_archival_object_id", "archival_rights", type_="unique")
    op.drop_table("archival_rights")
