"""merge book asset migration heads

Revision ID: 9a4c9d33807b
Revises: d4b8f2c1a901, f13c2a7b9e41
Create Date: 2026-09-21 11:25:32.145857

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9a4c9d33807b'
down_revision: Union[str, Sequence[str], None] = ('d4b8f2c1a901', 'f13c2a7b9e41')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
