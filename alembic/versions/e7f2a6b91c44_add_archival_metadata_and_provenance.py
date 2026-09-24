"""add structured archival metadata and provenance

Revision ID: e7f2a6b91c44
Revises: c2e4f7a91b33
Create Date: 2026-09-24
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e7f2a6b91c44"
down_revision: Union[str, Sequence[str], None] = "c2e4f7a91b33"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "archival_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("archival_object_id", sa.Integer(), nullable=False),
        sa.Column("alternative_titles", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("contributors", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("language", sa.String(length=40), nullable=True),
        sa.Column("subjects", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("genre", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("publication_date", sa.Date(), nullable=True),
        sa.Column("publisher", sa.String(length=255), nullable=True),
        sa.Column("edition", sa.String(length=255), nullable=True),
        sa.Column("external_identifier", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["archival_object_id"], ["archival_objects.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "archival_object_id", name="uq_archival_metadata_archival_object_id"
        ),
    )
    op.create_index("ix_archival_metadata_id", "archival_metadata", ["id"])
    op.create_index(
        "ix_archival_metadata_archival_object_id",
        "archival_metadata",
        ["archival_object_id"],
        unique=True,
    )

    op.create_table(
        "archival_provenance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("archival_object_id", sa.Integer(), nullable=False),
        sa.Column("source_institution", sa.String(length=255), nullable=True),
        sa.Column("source_collection", sa.String(length=255), nullable=True),
        sa.Column("shelfmark", sa.String(length=255), nullable=True),
        sa.Column("accession_number", sa.String(length=100), nullable=True),
        sa.Column("original_format", sa.String(length=100), nullable=True),
        sa.Column("physical_condition", sa.Text(), nullable=True),
        sa.Column("origin_place", sa.String(length=255), nullable=True),
        sa.Column("origin_date", sa.Date(), nullable=True),
        sa.Column("digitized_by", sa.String(length=255), nullable=True),
        sa.Column("digitized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("digitization_method", sa.String(length=255), nullable=True),
        sa.Column("scanner_device", sa.String(length=255), nullable=True),
        sa.Column("master_format", sa.String(length=100), nullable=True),
        sa.Column("derivative_format", sa.String(length=100), nullable=True),
        sa.Column("software", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["archival_object_id"], ["archival_objects.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "archival_object_id", name="uq_archival_provenance_archival_object_id"
        ),
    )
    op.create_index("ix_archival_provenance_id", "archival_provenance", ["id"])
    op.create_index(
        "ix_archival_provenance_archival_object_id",
        "archival_provenance",
        ["archival_object_id"],
        unique=True,
    )

    # Backfill structured records from the archival fields already present on
    # Book. No public catalogue fields are removed or changed by this migration.
    op.execute(sa.text("""
        INSERT INTO archival_metadata
            (archival_object_id, language, subjects, genre, notes)
        SELECT
            b.archival_object_id,
            NULLIF(TRIM(b.language), ''),
            CASE
                WHEN NULLIF(TRIM(b.subjects_csv), '') IS NULL THEN '[]'::json
                ELSE to_json((string_to_array(b.subjects_csv, ','))::text[])
            END,
            CASE
                WHEN NULLIF(TRIM(b.genre_csv), '') IS NULL THEN '[]'::json
                ELSE to_json((string_to_array(b.genre_csv, ','))::text[])
            END,
            NULLIF(TRIM(b.curator_note), '')
        FROM books b
        WHERE b.archival_object_id IS NOT NULL
    """))

    op.execute(sa.text("""
        INSERT INTO archival_provenance
            (archival_object_id, accession_number, original_format,
             physical_condition, origin_place, digitized_by, digitized_at, notes)
        SELECT
            b.archival_object_id,
            NULLIF(TRIM(b.accession_no), ''),
            NULLIF(TRIM(b.original_format), ''),
            NULLIF(TRIM(b.condition_notes), ''),
            NULLIF(TRIM(b.origin), ''),
            NULLIF(TRIM(b.digitized_by), ''),
            b.digitized_at,
            NULLIF(TRIM(b.era), '')
        FROM books b
        WHERE b.archival_object_id IS NOT NULL
    """))


def downgrade() -> None:
    op.drop_index(
        "ix_archival_provenance_archival_object_id", table_name="archival_provenance"
    )
    op.drop_index("ix_archival_provenance_id", table_name="archival_provenance")
    op.drop_constraint(
        "uq_archival_provenance_archival_object_id",
        "archival_provenance",
        type_="unique",
    )
    op.drop_table("archival_provenance")

    op.drop_index(
        "ix_archival_metadata_archival_object_id", table_name="archival_metadata"
    )
    op.drop_index("ix_archival_metadata_id", table_name="archival_metadata")
    op.drop_constraint(
        "uq_archival_metadata_archival_object_id", "archival_metadata", type_="unique"
    )
    op.drop_table("archival_metadata")
