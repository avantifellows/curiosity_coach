"""merge username rename and other branch migrations

Revision ID: 95c87a1cdec9
Revises: 1a9335f01f05, f6146a303440
Create Date: 2025-07-11 18:03:32.604237

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '95c87a1cdec9'
down_revision: Union[str, None] = ('1a9335f01f05', 'f6146a303440')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
