"""allow private storage-backed BookAssets without public URLs

Revision ID: f7a8b9c0d1e2
Revises: f6d7e8a9b0c1
"""
from alembic import op
import sqlalchemy as sa

revision = "f7a8b9c0d1e2"
down_revision = "f6d7e8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Private storage-backed assets are served through authenticated routes and
    # intentionally have no public URL. The ORM already models this as nullable.
    op.alter_column(
        "book_assets",
        "public_url",
        existing_type=sa.String(length=500),
        nullable=True,
    )


def downgrade() -> None:
    bind = op.get_bind()
    null_count = bind.execute(
        sa.text("SELECT count(*) FROM book_assets WHERE public_url IS NULL")
    ).scalar_one()
    if null_count:
        raise RuntimeError(
            "Cannot restore book_assets.public_url NOT NULL while private storage-backed assets exist. "
            "Migrate or remove those assets explicitly before downgrading."
        )
    op.alter_column(
        "book_assets",
        "public_url",
        existing_type=sa.String(length=500),
        nullable=False,
    )
