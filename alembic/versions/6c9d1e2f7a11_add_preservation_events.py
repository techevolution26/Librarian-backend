"""add append-only preservation events

Revision ID: 6c9d1e2f7a11
Revises: f4b8c2d91e55
Create Date: 2026-09-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "6c9d1e2f7a11"
down_revision: Union[str, Sequence[str], None] = "f4b8c2d91e55"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preservation_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("archival_object_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "outcome", sa.String(length=20), nullable=False, server_default="unknown"
        ),
        sa.Column("agent", sa.String(length=255), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("source_storage_key", sa.String(length=500), nullable=True),
        sa.Column("target_storage_key", sa.String(length=500), nullable=True),
        sa.Column("checksum", sa.String(length=128), nullable=True),
        sa.Column("checksum_algorithm", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["archival_object_id"], ["archival_objects.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["book_assets.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_preservation_events_id", "preservation_events", ["id"])
    op.create_index(
        "ix_preservation_events_archival_object_id",
        "preservation_events",
        ["archival_object_id"],
    )
    op.create_index(
        "ix_preservation_events_asset_id", "preservation_events", ["asset_id"]
    )
    op.create_index(
        "ix_preservation_events_event_type", "preservation_events", ["event_type"]
    )
    op.create_index(
        "ix_preservation_events_event_date", "preservation_events", ["event_date"]
    )
    op.create_index(
        "ix_preservation_events_object_date",
        "preservation_events",
        ["archival_object_id", "event_date"],
    )
    op.create_index(
        "ix_preservation_events_asset_date",
        "preservation_events",
        ["asset_id", "event_date"],
    )
    op.create_index(
        "ix_preservation_events_type_date",
        "preservation_events",
        ["event_type", "event_date"],
    )

    # Seed an initial, factual preservation history for assets that already
    # existed before this event log was introduced. No historical operation
    # is inferred beyond the asset's recorded creation/checksum.
    op.execute(sa.text("""
        INSERT INTO preservation_events (
            archival_object_id,
            asset_id,
            event_type,
            event_date,
            outcome,
            agent,
            detail,
            checksum,
            checksum_algorithm
        )
        SELECT
            b.archival_object_id,
            a.id,
            'ingestion',
            a.created_at,
            'success',
            'system migration',
            'Initial preservation history recorded when the preservation event log was introduced.',
            a.checksum_sha256,
            'SHA-256'
        FROM book_assets a
        JOIN books b ON b.id = a.book_id
        WHERE b.archival_object_id IS NOT NULL
    """))


def downgrade() -> None:
    op.drop_index("ix_preservation_events_type_date", table_name="preservation_events")
    op.drop_index("ix_preservation_events_asset_date", table_name="preservation_events")
    op.drop_index(
        "ix_preservation_events_object_date", table_name="preservation_events"
    )
    op.drop_index("ix_preservation_events_event_date", table_name="preservation_events")
    op.drop_index("ix_preservation_events_event_type", table_name="preservation_events")
    op.drop_index("ix_preservation_events_asset_id", table_name="preservation_events")
    op.drop_index(
        "ix_preservation_events_archival_object_id", table_name="preservation_events"
    )
    op.drop_index("ix_preservation_events_id", table_name="preservation_events")
    op.drop_table("preservation_events")
