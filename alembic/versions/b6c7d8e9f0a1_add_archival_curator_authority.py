"""add explicit archival curator authority

Revision ID: b6c7d8e9f0a1
Revises: b5c6d7e8f9a0
"""
from alembic import op
import sqlalchemy as sa

revision = "b6c7d8e9f0a1"
down_revision = "b5c6d7e8f9a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "archival_objects",
        sa.Column("curator_user_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_archival_objects_curator_user_id",
        "archival_objects",
        ["curator_user_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_archival_objects_curator_user_id_users",
        "archival_objects",
        "users",
        ["curator_user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_archival_objects_curator_user_id_users",
        "archival_objects",
        type_="foreignkey",
    )
    op.drop_index("ix_archival_objects_curator_user_id", table_name="archival_objects")
    op.drop_column("archival_objects", "curator_user_id")
