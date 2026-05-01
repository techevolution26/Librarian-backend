"""create circles and connections manually

Revision ID: 779e253b8e8b
Revises: 69e27d982aa9
Create Date: 2026-04-22 21:10:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "779e253b8e8b"
down_revision: Union[str, Sequence[str], None] = "69e27d982aa9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # No-op.
    #
    # The circles/connections tables are already created by:
    # 69e27d982aa9_add_circles_and_connections.py
    #
    # This migration exists only to preserve Alembic revision history.
    pass


def downgrade() -> None:
    # No-op because this migration did not create anything.
    pass