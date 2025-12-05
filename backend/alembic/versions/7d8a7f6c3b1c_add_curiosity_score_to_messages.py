"""add curiosity score to messages

Revision ID: 7d8a7f6c3b1c
Revises: 052454e90e53
Create Date: 2025-11-18 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7d8a7f6c3b1c'
down_revision: Union[str, None] = 'f1922075fb72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add curiosity_score column to messages."""
    op.add_column('messages', sa.Column('curiosity_score', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove curiosity_score column from messages."""
    op.drop_column('messages', 'curiosity_score')
