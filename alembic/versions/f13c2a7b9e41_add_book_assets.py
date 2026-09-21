"""add versioned book assets

Revision ID: f13c2a7b9e41
Revises: a92f1d7c44be
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f13c2a7b9e41"
down_revision: Union[str, Sequence[str], None] = "a92f1d7c44be"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "book_assets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", sa.String(length=20), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("public_url", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_book_assets_book_id", "book_assets", ["book_id"])
    op.create_index("ix_book_assets_asset_type", "book_assets", ["asset_type"])
    op.create_index("ix_book_assets_uploaded_by", "book_assets", ["uploaded_by"])
    op.create_index("ix_book_assets_is_current", "book_assets", ["is_current"])
    op.create_unique_constraint("uq_book_asset_version", "book_assets", ["book_id", "asset_type", "version"])
    op.create_index("uq_book_asset_current", "book_assets", ["book_id", "asset_type"], unique=True, postgresql_where=sa.text("is_current = true"))


def downgrade() -> None:
    op.drop_index("uq_book_asset_current", table_name="book_assets")
    op.drop_constraint("uq_book_asset_version", "book_assets", type_="unique")
    op.drop_index("ix_book_assets_is_current", table_name="book_assets")
    op.drop_index("ix_book_assets_uploaded_by", table_name="book_assets")
    op.drop_index("ix_book_assets_asset_type", table_name="book_assets")
    op.drop_index("ix_book_assets_book_id", table_name="book_assets")
    op.drop_table("book_assets")
