"""add_is_production_to_prompt_versions

Revision ID: 22b3966adbac
Revises: add_user_to_prompt_versions
Create Date: 2025-01-21 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '22b3966adbac'
down_revision: Union[str, None] = 'add_user_to_prompt_versions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # No-op: is_production column was already added in the previous migration
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # No-op: is_production column will be removed by the previous migration's downgrade
    pass
