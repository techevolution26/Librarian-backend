"""add role to users

Revision ID: a00fd2752cfc
Revises: 0f801e29e3ae
Create Date: 2026-05-09 01:45:06.876125

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a00fd2752cfc'
down_revision: Union[str, Sequence[str], None] = '0f801e29e3ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="USER",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
