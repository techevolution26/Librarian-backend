"""add source-native immutable Reader anchors

Revision ID: e4b7c9d2a601
Revises: d1e2f3a4b5c6
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e4b7c9d2a601"
down_revision: Union[str, Sequence[str], None] = "d1e2f3a4b5c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reader_source_anchors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("archival_object_id", sa.Integer(), nullable=True),
        sa.Column("source_asset_id", sa.Integer(), nullable=True),
        sa.Column("canvas_id", sa.Integer(), nullable=True),
        sa.Column("ocr_page_id", sa.Integer(), nullable=True),
        sa.Column("locator_type", sa.String(length=30), nullable=False),
        sa.Column("locator_data", sa.JSON(), nullable=False),
        sa.Column("source_persistent_identifier", sa.String(length=120), nullable=True),
        sa.Column("source_accession_number", sa.String(length=40), nullable=True),
        sa.Column("source_canvas_identifier", sa.String(length=120), nullable=True),
        sa.Column("source_asset_version", sa.Integer(), nullable=True),
        sa.Column("source_asset_checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("source_text_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "locator_type IN ('pdf_page', 'pdf_text', 'iiif_canvas', 'image_region', 'text_span', 'ocr_span', 'media_time')",
            name="ck_reader_source_anchor_locator_type",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["archival_object_id"], ["archival_objects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_asset_id"], ["book_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["canvas_id"], ["archival_canvases.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ocr_page_id"], ["archival_ocr_pages.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_reader_source_anchors_id", "reader_source_anchors", ["id"])
    op.create_index("ix_reader_source_anchors_user_id", "reader_source_anchors", ["user_id"])
    op.create_index("ix_reader_source_anchors_book_id", "reader_source_anchors", ["book_id"])
    op.create_index("ix_reader_source_anchors_archival_object_id", "reader_source_anchors", ["archival_object_id"])
    op.create_index("ix_reader_source_anchors_source_asset_id", "reader_source_anchors", ["source_asset_id"])
    op.create_index("ix_reader_source_anchors_canvas_id", "reader_source_anchors", ["canvas_id"])
    op.create_index("ix_reader_source_anchors_ocr_page_id", "reader_source_anchors", ["ocr_page_id"])
    op.create_index("ix_reader_source_anchors_user_book", "reader_source_anchors", ["user_id", "book_id"])

    for table in ("bookmarks", "highlights", "notes", "quote_references"):
        op.add_column(table, sa.Column("source_anchor_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{table}_source_anchor_id", table, ["source_anchor_id"])
        op.create_foreign_key(
            f"fk_{table}_source_anchor_id_reader_source_anchors",
            table,
            "reader_source_anchors",
            ["source_anchor_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # A highlight can now be anchored to a non-paginated source (canvas, image
    # region, text span, or media time). Existing page-based rows remain intact.
    op.alter_column("highlights", "page_number", existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    has_non_page_highlights = bind.execute(
        sa.text("SELECT 1 FROM highlights WHERE page_number IS NULL LIMIT 1")
    ).first()
    if has_non_page_highlights:
        raise RuntimeError(
            "Cannot downgrade source anchors while non-page highlights exist; "
            "preserve them or migrate them to a page locator first."
        )

    op.alter_column("highlights", "page_number", existing_type=sa.Integer(), nullable=False)
    for table in ("bookmarks", "highlights", "notes", "quote_references"):
        op.drop_constraint(f"fk_{table}_source_anchor_id_reader_source_anchors", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_source_anchor_id", table_name=table)
        op.drop_column(table, "source_anchor_id")

    for index_name in (
        "ix_reader_source_anchors_user_book",
        "ix_reader_source_anchors_ocr_page_id",
        "ix_reader_source_anchors_canvas_id",
        "ix_reader_source_anchors_source_asset_id",
        "ix_reader_source_anchors_archival_object_id",
        "ix_reader_source_anchors_book_id",
        "ix_reader_source_anchors_user_id",
        "ix_reader_source_anchors_id",
    ):
        op.drop_index(index_name, table_name="reader_source_anchors")
    op.drop_table("reader_source_anchors")
