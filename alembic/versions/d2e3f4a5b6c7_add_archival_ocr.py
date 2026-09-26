"""add archival OCR page records

Revision ID: d2e3f4a5b6c7
Revises: c1d2e3f4a5b6
"""
from alembic import op
import sqlalchemy as sa

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "archival_ocr_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("archival_object_id", sa.Integer(), nullable=False),
        sa.Column("canvas_id", sa.Integer(), nullable=False),
        sa.Column("source_asset_id", sa.Integer(), nullable=False),
        sa.Column("source_checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=32), nullable=False),
        sa.Column("engine", sa.String(length=80), nullable=False),
        sa.Column("engine_version", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("length(trim(text)) > 0", name="ck_archival_ocr_text_nonempty"),
        sa.ForeignKeyConstraint(["archival_object_id"], ["archival_objects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["canvas_id"], ["archival_canvases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_asset_id"], ["book_assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canvas_id", "language", "engine", "engine_version", name="uq_archival_ocr_variant"),
    )
    op.create_index("ix_archival_ocr_pages_id", "archival_ocr_pages", ["id"])
    op.create_index("ix_archival_ocr_pages_object_id", "archival_ocr_pages", ["archival_object_id"])
    op.create_index("ix_archival_ocr_pages_canvas_id", "archival_ocr_pages", ["canvas_id"])
    op.create_index("ix_archival_ocr_pages_asset_id", "archival_ocr_pages", ["source_asset_id"])
    op.create_index("ix_archival_ocr_pages_status", "archival_ocr_pages", ["status"])


def downgrade() -> None:
    op.drop_index("ix_archival_ocr_pages_status", table_name="archival_ocr_pages")
    op.drop_index("ix_archival_ocr_pages_asset_id", table_name="archival_ocr_pages")
    op.drop_index("ix_archival_ocr_pages_canvas_id", table_name="archival_ocr_pages")
    op.drop_index("ix_archival_ocr_pages_object_id", table_name="archival_ocr_pages")
    op.drop_index("ix_archival_ocr_pages_id", table_name="archival_ocr_pages")
    op.drop_table("archival_ocr_pages")
