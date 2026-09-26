"""add explicit storage replication tracking

Revision ID: f0a1b2c3d4e5
Revises: e8f9a0b1c2d3
"""
from alembic import op
import sqlalchemy as sa


revision = "f0a1b2c3d4e5"
down_revision = "e8f9a0b1c2d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "asset_storage_locations",
        sa.Column("replicated_from_location_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "asset_storage_locations",
        sa.Column("replication_status", sa.String(length=20), nullable=False, server_default="none"),
    )
    op.add_column(
        "asset_storage_locations",
        sa.Column("replication_error", sa.String(length=1000), nullable=True),
    )
    op.create_index(
        "ix_asset_storage_locations_replicated_from_location_id",
        "asset_storage_locations",
        ["replicated_from_location_id"],
    )
    op.create_index(
        "ix_asset_storage_locations_replication_status",
        "asset_storage_locations",
        ["replication_status"],
    )
    op.create_foreign_key(
        "fk_asset_storage_locations_replicated_from",
        "asset_storage_locations",
        "asset_storage_locations",
        ["replicated_from_location_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_asset_storage_locations_replicated_from",
        "asset_storage_locations",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_asset_storage_locations_replication_status",
        table_name="asset_storage_locations",
    )
    op.drop_index(
        "ix_asset_storage_locations_replicated_from_location_id",
        table_name="asset_storage_locations",
    )
    op.drop_column("asset_storage_locations", "replication_error")
    op.drop_column("asset_storage_locations", "replication_status")
    op.drop_column("asset_storage_locations", "replicated_from_location_id")
