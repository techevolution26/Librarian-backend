"""add preservation master and access asset roles

Revision ID: 6d7e8f9a2b10
Revises: 6c9d1e2f7a11
"""

from alembic import op
import sqlalchemy as sa

revision = "6d7e8f9a2b10"
down_revision = "6c9d1e2f7a11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "book_assets", sa.Column("asset_role", sa.String(length=30), nullable=True)
    )
    op.execute("UPDATE book_assets SET asset_role = 'access' WHERE asset_role IS NULL")
    op.alter_column(
        "book_assets", "asset_role", nullable=False, server_default="access"
    )

    op.drop_index("uq_book_asset_current", table_name="book_assets")
    op.drop_constraint("uq_book_asset_version", "book_assets", type_="unique")

    op.create_unique_constraint(
        "uq_book_asset_version",
        "book_assets",
        ["book_id", "asset_type", "asset_role", "version"],
    )
    op.create_index(
        "uq_book_asset_current",
        "book_assets",
        ["book_id", "asset_type", "asset_role"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index(
        "ix_book_assets_asset_role", "book_assets", ["asset_role"], unique=False
    )


def downgrade() -> None:
    # A downgrade is only safe when no preservation-master assets exist and
    # no two roles share a version number for the same book/type.
    bind = op.get_bind()
    master_count = bind.execute(
        sa.text("SELECT count(*) FROM book_assets WHERE asset_role <> 'access'")
    ).scalar_one()
    if master_count:
        raise RuntimeError(
            "Cannot downgrade asset roles while preservation-master assets exist"
        )

    duplicate_count = bind.execute(sa.text("""
        SELECT count(*) FROM (
            SELECT book_id, asset_type, version
            FROM book_assets
            GROUP BY book_id, asset_type, version
            HAVING count(*) > 1
        ) duplicates
    """)).scalar_one()
    if duplicate_count:
        raise RuntimeError(
            "Cannot downgrade asset roles because asset versions would collide"
        )

    op.drop_index("ix_book_assets_asset_role", table_name="book_assets")
    op.drop_constraint("ck_book_asset_role", "book_assets", type_="check")
    op.drop_index("uq_book_asset_current", table_name="book_assets")
    op.drop_constraint("uq_book_asset_version", "book_assets", type_="unique")
    op.create_check_constraint(
        "ck_book_asset_role",
        "book_assets",
        "asset_role IN ('preservation_master', 'access')",
    )
    op.create_unique_constraint(
        "uq_book_asset_version",
        "book_assets",
        ["book_id", "asset_type", "version"],
    )
    op.create_index(
        "uq_book_asset_current",
        "book_assets",
        ["book_id", "asset_type"],
        unique=True,
        postgresql_where=sa.text("is_current = true"),
    )
    op.drop_column("book_assets", "asset_role")
