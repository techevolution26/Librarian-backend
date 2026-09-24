"""add persistent archival identifiers

Revision ID: 7a1b2c3d4e55
Revises: 6d7e8f9a2b10
Create Date: 2026-09-24
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "7a1b2c3d4e55"
down_revision = "6d7e8f9a2b10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "archival_objects",
        sa.Column("persistent_identifier", sa.String(length=120), nullable=True),
    )

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id FROM archival_objects ORDER BY id")).fetchall()
    for (object_id,) in rows:
        bind.execute(
            sa.text(
                "UPDATE archival_objects "
                "SET persistent_identifier = :pid "
                "WHERE id = :object_id"
            ),
            {"pid": f"tl:ao:{uuid4().hex}", "object_id": object_id},
        )

    op.alter_column("archival_objects", "persistent_identifier", nullable=False)
    op.create_unique_constraint(
        "uq_archival_objects_persistent_identifier",
        "archival_objects",
        ["persistent_identifier"],
    )
    op.create_index(
        "ix_archival_objects_persistent_identifier",
        "archival_objects",
        ["persistent_identifier"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_archival_objects_persistent_identifier", table_name="archival_objects"
    )
    op.drop_constraint(
        "uq_archival_objects_persistent_identifier",
        "archival_objects",
        type_="unique",
    )
    op.drop_column("archival_objects", "persistent_identifier")
