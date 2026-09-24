"""add stable archival objects and map existing books

Revision ID: c2e4f7a91b33
Revises: b7d3e8a91c20
Create Date: 2026-09-24
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c2e4f7a91b33"
down_revision: Union[str, Sequence[str], None] = "b7d3e8a91c20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "archival_objects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("identifier", sa.String(length=100), nullable=False),
        sa.Column("object_type", sa.String(length=30), nullable=False, server_default="other"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("collection_id", sa.Integer(), nullable=True),
        sa.Column("visibility", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["collection_id"], ["collections.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("identifier", name="uq_archival_objects_identifier"),
    )
    op.create_index("ix_archival_objects_id", "archival_objects", ["id"])
    op.create_index("ix_archival_objects_identifier", "archival_objects", ["identifier"])
    op.create_index("ix_archival_objects_object_type", "archival_objects", ["object_type"])
    op.create_index("ix_archival_objects_title", "archival_objects", ["title"])
    op.create_index("ix_archival_objects_collection_id", "archival_objects", ["collection_id"])
    op.create_index("ix_archival_objects_visibility", "archival_objects", ["visibility"])

    op.add_column("books", sa.Column("archival_object_id", sa.Integer(), nullable=True))
    op.create_index("ix_books_archival_object_id", "books", ["archival_object_id"], unique=True)
    op.create_foreign_key(
        "fk_books_archival_object_id",
        "books",
        "archival_objects",
        ["archival_object_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Give every existing Book a stable archival identity without changing its
    # public catalogue behavior. Existing visibility is retained.
    op.execute(sa.text("""
        INSERT INTO archival_objects
            (identifier, object_type, title, description, visibility, archived_at)
        SELECT
            'BOOK-' || CAST(id AS VARCHAR(40)),
            'book',
            title,
            description,
            visibility,
            archived_at
        FROM books
    """))

    op.execute(sa.text("""
        UPDATE books b
        SET archival_object_id = ao.id
        FROM archival_objects ao
        WHERE ao.identifier = 'BOOK-' || CAST(b.id AS VARCHAR(40))
    """))


def downgrade() -> None:
    op.drop_constraint("fk_books_archival_object_id", "books", type_="foreignkey")
    op.drop_index("ix_books_archival_object_id", table_name="books")
    op.drop_column("books", "archival_object_id")

    op.drop_index("ix_archival_objects_visibility", table_name="archival_objects")
    op.drop_index("ix_archival_objects_collection_id", table_name="archival_objects")
    op.drop_index("ix_archival_objects_title", table_name="archival_objects")
    op.drop_index("ix_archival_objects_object_type", table_name="archival_objects")
    op.drop_index("ix_archival_objects_identifier", table_name="archival_objects")
    op.drop_index("ix_archival_objects_id", table_name="archival_objects")
    op.drop_constraint("uq_archival_objects_identifier", "archival_objects", type_="unique")
    op.drop_table("archival_objects")
