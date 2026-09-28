"""add creator lifetime access

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d9e0f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "creator_lifetime_access",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("hosted_book_id", sa.Integer(), nullable=False),
        sa.Column("paid_offer_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("access_source", sa.String(length=20), nullable=False, server_default="purchase"),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hosted_book_id"], ["creator_hosted_books.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["paid_offer_id"], ["creator_paid_books.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("user_id", "hosted_book_id", name="uq_creator_lifetime_access_user_hosted_book"),
    )
    op.create_index("ix_creator_lifetime_access_id", "creator_lifetime_access", ["id"])
    op.create_index("ix_creator_lifetime_access_user_id", "creator_lifetime_access", ["user_id"])
    op.create_index("ix_creator_lifetime_access_hosted_book_id", "creator_lifetime_access", ["hosted_book_id"])
    op.create_index("ix_creator_lifetime_access_status", "creator_lifetime_access", ["status"])


def downgrade() -> None:
    op.drop_index("ix_creator_lifetime_access_status", table_name="creator_lifetime_access")
    op.drop_index("ix_creator_lifetime_access_hosted_book_id", table_name="creator_lifetime_access")
    op.drop_index("ix_creator_lifetime_access_user_id", table_name="creator_lifetime_access")
    op.drop_index("ix_creator_lifetime_access_id", table_name="creator_lifetime_access")
    op.drop_constraint("uq_creator_lifetime_access_user_hosted_book", "creator_lifetime_access", type_="unique")
    op.drop_table("creator_lifetime_access")
