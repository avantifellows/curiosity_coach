"""merge multi heads

Revision ID: f1922075fb72
Revises: 052454e90e53, ed15dba4e1f6
Create Date: 2025-11-02 13:13:28.872208

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1922075fb72'
down_revision: Union[str, None] = ('052454e90e53', 'ed15dba4e1f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
