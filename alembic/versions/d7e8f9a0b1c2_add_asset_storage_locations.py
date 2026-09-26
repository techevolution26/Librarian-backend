"""add physical storage locations for book assets

Revision ID: d7e8f9a0b1c2
Revises: c6d7e8f9a0b1
"""

from alembic import op
import sqlalchemy as sa

revision = "d7e8f9a0b1c2"
down_revision = "c6d7e8f9a0b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_storage_locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "asset_id",
            sa.Integer(),
            sa.ForeignKey("book_assets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider", sa.String(length=30), nullable=False, server_default="local"
        ),
        sa.Column("bucket", sa.String(length=255), nullable=True),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("public_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "status", sa.String(length=20), nullable=False, server_default="active"
        ),
        sa.Column(
            "is_primary", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "asset_id",
            "provider",
            "bucket",
            "storage_key",
            name="uq_asset_storage_location",
        ),
    )
    op.create_index(
        "ix_asset_storage_locations_asset_id", "asset_storage_locations", ["asset_id"]
    )
    op.create_index(
        "ix_asset_storage_locations_provider", "asset_storage_locations", ["provider"]
    )
    op.create_index(
        "ix_asset_storage_locations_status", "asset_storage_locations", ["status"]
    )
    op.create_index(
        "ix_asset_storage_locations_is_primary",
        "asset_storage_locations",
        ["is_primary"],
    )

    op.execute(sa.text("""
            INSERT INTO asset_storage_locations
                (asset_id, provider, bucket, storage_key, public_url, status, is_primary,
                 checksum_sha256, size_bytes, created_at)
            SELECT
                id,
                'local',
                NULL,
                storage_key,
                public_url,
                'active',
                true,
                checksum_sha256,
                size_bytes,
                created_at
            FROM book_assets
            """))


def downgrade() -> None:
    op.drop_index(
        "ix_asset_storage_locations_is_primary", table_name="asset_storage_locations"
    )
    op.drop_index(
        "ix_asset_storage_locations_status", table_name="asset_storage_locations"
    )
    op.drop_index(
        "ix_asset_storage_locations_provider", table_name="asset_storage_locations"
    )
    op.drop_index(
        "ix_asset_storage_locations_asset_id", table_name="asset_storage_locations"
    )
    op.drop_table("asset_storage_locations")
