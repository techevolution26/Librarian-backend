"""add_book_archival_metadata

Revision ID: a92f1d7c44be
Revises: c5a1b3990228
Create Date: 2026-09-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a92f1d7c44be'
down_revision: Union[str, Sequence[str], None] = 'c5a1b3990228'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('books', sa.Column('accession_no', sa.String(length=40), nullable=True))
    op.add_column('books', sa.Column('language', sa.String(length=40), nullable=False, server_default='en'))
    op.add_column('books', sa.Column('subjects_csv', sa.String(length=255), nullable=False, server_default=''))
    op.add_column('books', sa.Column('origin', sa.String(length=255), nullable=True))
    op.add_column('books', sa.Column('era', sa.String(length=120), nullable=True))
    op.add_column('books', sa.Column('original_format', sa.String(length=30), nullable=False, server_default='born-digital'))
    op.add_column('books', sa.Column('rights_statement', sa.String(length=30), nullable=False, server_default='all-rights-reserved'))
    op.add_column('books', sa.Column('condition_notes', sa.Text(), nullable=True))
    op.add_column('books', sa.Column('curator_note', sa.Text(), nullable=True))
    op.add_column('books', sa.Column('checksum_sha256', sa.String(length=64), nullable=True))
    op.add_column('books', sa.Column('digitized_by', sa.String(length=255), nullable=True))
    op.add_column('books', sa.Column('digitized_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_books_accession_no'), 'books', ['accession_no'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_books_accession_no'), table_name='books')
    op.drop_column('books', 'digitized_at')
    op.drop_column('books', 'digitized_by')
    op.drop_column('books', 'checksum_sha256')
    op.drop_column('books', 'curator_note')
    op.drop_column('books', 'condition_notes')
    op.drop_column('books', 'rights_statement')
    op.drop_column('books', 'original_format')
    op.drop_column('books', 'era')
    op.drop_column('books', 'origin')
    op.drop_column('books', 'subjects_csv')
    op.drop_column('books', 'language')
    op.drop_column('books', 'accession_no')
