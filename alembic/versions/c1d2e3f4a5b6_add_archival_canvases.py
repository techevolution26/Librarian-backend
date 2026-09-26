"""add archival canvas page model

Revision ID: c1d2e3f4a5b6
Revises: f0a1b2c3d4e5
"""
from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4a5b6"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "archival_canvases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("archival_object_id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=True),
        sa.Column("canvas_identifier", sa.String(length=120), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("sequence > 0", name="ck_archival_canvas_sequence_positive"),
        sa.CheckConstraint("page_number IS NULL OR page_number > 0", name="ck_archival_canvas_page_positive"),
        sa.CheckConstraint("width IS NULL OR width > 0", name="ck_archival_canvas_width_positive"),
        sa.CheckConstraint("height IS NULL OR height > 0", name="ck_archival_canvas_height_positive"),
        sa.ForeignKeyConstraint(["archival_object_id"], ["archival_objects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["book_assets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("archival_object_id", "sequence", name="uq_archival_canvas_sequence"),
        sa.UniqueConstraint("archival_object_id", "canvas_identifier", name="uq_archival_canvas_identifier"),
    )
    op.create_index("ix_archival_canvases_id", "archival_canvases", ["id"])
    op.create_index("ix_archival_canvases_archival_object_id", "archival_canvases", ["archival_object_id"])
    op.create_index("ix_archival_canvases_asset_id", "archival_canvases", ["asset_id"])
    op.create_index("ix_archival_canvases_canvas_identifier", "archival_canvases", ["canvas_identifier"])
    op.create_index("ix_archival_canvases_page_number", "archival_canvases", ["page_number"])
    op.create_index("ix_archival_canvases_object_sequence", "archival_canvases", ["archival_object_id", "sequence"])


def downgrade() -> None:
    op.drop_index("ix_archival_canvases_object_sequence", table_name="archival_canvases")
    op.drop_index("ix_archival_canvases_page_number", table_name="archival_canvases")
    op.drop_index("ix_archival_canvases_canvas_identifier", table_name="archival_canvases")
    op.drop_index("ix_archival_canvases_asset_id", table_name="archival_canvases")
    op.drop_index("ix_archival_canvases_archival_object_id", table_name="archival_canvases")
    op.drop_index("ix_archival_canvases_id", table_name="archival_canvases")
    op.drop_table("archival_canvases")
