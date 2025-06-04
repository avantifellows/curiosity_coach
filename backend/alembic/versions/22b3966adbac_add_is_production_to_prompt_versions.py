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
    # Add production flag column as nullable first
    op.add_column('prompt_versions', sa.Column('is_production', sa.Boolean(), nullable=True))
    
    # Update all existing rows to have is_production = False
    op.execute("UPDATE prompt_versions SET is_production = FALSE WHERE is_production IS NULL")
    
    # Now make the column NOT NULL
    op.alter_column('prompt_versions', 'is_production', nullable=False)
    
    # Add index for performance
    op.create_index('ix_prompt_versions_is_production', 'prompt_versions', ['is_production'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index
    op.drop_index('ix_prompt_versions_is_production', 'prompt_versions')
    
    # Drop column
    op.drop_column('prompt_versions', 'is_production')
