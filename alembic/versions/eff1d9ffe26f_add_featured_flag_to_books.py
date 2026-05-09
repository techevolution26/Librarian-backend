"""add featured flag to books

Revision ID: eff1d9ffe26f
Revises: 78c00f2d79d5
Create Date: 2026-05-09 16:50:28.980896

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eff1d9ffe26f'
down_revision: Union[str, Sequence[str], None] = '78c00f2d79d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "books",
        sa.Column(
            "is_featured",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("books", "is_featured")
