"""add logical keys for independently versioned archival components

Revision ID: f5c8d1a2b3c4
Revises: e4b7c9d2a601
"""
from alembic import op
import sqlalchemy as sa

revision = "f5c8d1a2b3c4"
down_revision = "e4b7c9d2a601"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("book_assets", sa.Column("logical_key", sa.String(length=120), nullable=True))
    op.drop_index("uq_book_asset_current", table_name="book_assets")
    op.drop_constraint("uq_book_asset_version", "book_assets", type_="unique")

    op.create_index(
        "uq_book_asset_version_singleton",
        "book_assets",
        ["book_id", "asset_type", "asset_role", "version"],
        unique=True,
        postgresql_where=sa.text("logical_key IS NULL"),
        sqlite_where=sa.text("logical_key IS NULL"),
    )
    op.create_index(
        "uq_book_asset_version_logical",
        "book_assets",
        ["book_id", "asset_type", "asset_role", "logical_key", "version"],
        unique=True,
        postgresql_where=sa.text("logical_key IS NOT NULL"),
        sqlite_where=sa.text("logical_key IS NOT NULL"),
    )
    op.create_index(
        "uq_book_asset_current_singleton",
        "book_assets",
        ["book_id", "asset_type", "asset_role"],
        unique=True,
        postgresql_where=sa.text("is_current = true AND logical_key IS NULL"),
        sqlite_where=sa.text("is_current = 1 AND logical_key IS NULL"),
    )
    op.create_index(
        "uq_book_asset_current_logical",
        "book_assets",
        ["book_id", "asset_type", "asset_role", "logical_key"],
        unique=True,
        postgresql_where=sa.text("is_current = true AND logical_key IS NOT NULL"),
        sqlite_where=sa.text("is_current = 1 AND logical_key IS NOT NULL"),
    )
    op.create_index("ix_book_assets_logical_key", "book_assets", ["logical_key"])


def downgrade() -> None:
    bind = op.get_bind()
    duplicate_versions = bind.execute(sa.text("""
        SELECT count(*) FROM (
            SELECT book_id, asset_type, asset_role, version
            FROM book_assets
            GROUP BY book_id, asset_type, asset_role, version
            HAVING count(*) > 1
        ) AS duplicate_versions
    """)).scalar_one()
    duplicate_current = bind.execute(sa.text("""
        SELECT count(*) FROM (
            SELECT book_id, asset_type, asset_role
            FROM book_assets
            WHERE is_current = true
            GROUP BY book_id, asset_type, asset_role
            HAVING count(*) > 1
        ) AS duplicate_current
    """)).scalar_one()
    if duplicate_versions or duplicate_current:
        raise RuntimeError(
            "Cannot downgrade logical asset keys while multiple versioned/current "
            "assets exist for the same book/type/role. Consolidate those assets first."
        )

    op.drop_index("ix_book_assets_logical_key", table_name="book_assets")
    op.drop_index("uq_book_asset_current_logical", table_name="book_assets")
    op.drop_index("uq_book_asset_current_singleton", table_name="book_assets")
    op.drop_index("uq_book_asset_version_logical", table_name="book_assets")
    op.drop_index("uq_book_asset_version_singleton", table_name="book_assets")
    op.create_unique_constraint(
        "uq_book_asset_version", "book_assets",
        ["book_id", "asset_type", "asset_role", "version"],
    )
    op.create_index(
        "uq_book_asset_current", "book_assets",
        ["book_id", "asset_type", "asset_role"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
        sqlite_where=sa.text("is_current = 1"),
    )
    op.drop_column("book_assets", "logical_key")
