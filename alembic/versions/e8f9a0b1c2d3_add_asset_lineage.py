"""add asset lineage for preservation masters and derivatives

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
"""
from alembic import op
import sqlalchemy as sa

revision = "e8f9a0b1c2d3"
down_revision = "d7e8f9a0b1c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("book_assets", sa.Column("source_asset_id", sa.Integer(), nullable=True))
    op.add_column("book_assets", sa.Column("derivation_type", sa.String(length=40), nullable=True))
    op.create_index("ix_book_assets_source_asset_id", "book_assets", ["source_asset_id"])
    op.create_foreign_key(
        "fk_book_assets_source_asset_id",
        "book_assets",
        "book_assets",
        ["source_asset_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_book_assets_source_asset_id", "book_assets", type_="foreignkey")
    op.drop_index("ix_book_assets_source_asset_id", table_name="book_assets")
    op.drop_column("book_assets", "derivation_type")
    op.drop_column("book_assets", "source_asset_id")
