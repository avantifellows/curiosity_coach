"""merge analysis cache

Revision ID: c9819cf4d257
Revises: 3c0b0a0dcb5d, 7d8a7f6c3b1c
Create Date: 2025-12-10 17:16:33.020417

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9819cf4d257'
down_revision: Union[str, None] = ('3c0b0a0dcb5d', '7d8a7f6c3b1c')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
