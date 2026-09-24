"""add archival collections

Revision ID: b7d3e8a91c20
Revises: 9a4c9d33807b
Create Date: 2026-09-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7d3e8a91c20"
down_revision: Union[str, Sequence[str], None] = "9a4c9d33807b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("identifier", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("curator", sa.String(length=255), nullable=True),
        sa.Column("institution", sa.String(length=255), nullable=True),
        sa.Column("geographic_scope", sa.String(length=255), nullable=True),
        sa.Column("date_start", sa.String(length=40), nullable=True),
        sa.Column("date_end", sa.String(length=40), nullable=True),
        sa.Column("subjects_csv", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("rights_statement", sa.String(length=500), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("identifier", name="uq_collections_identifier"),
    )
    op.create_index("ix_collections_id", "collections", ["id"])
    op.create_index("ix_collections_identifier", "collections", ["identifier"])
    op.create_index("ix_collections_title", "collections", ["title"])
    op.create_index("ix_collections_visibility", "collections", ["visibility"])


def downgrade() -> None:
    op.drop_index("ix_collections_visibility", table_name="collections")
    op.drop_index("ix_collections_title", table_name="collections")
    op.drop_index("ix_collections_identifier", table_name="collections")
    op.drop_index("ix_collections_id", table_name="collections")
    op.drop_constraint("uq_collections_identifier", "collections", type_="unique")
    op.drop_table("collections")
