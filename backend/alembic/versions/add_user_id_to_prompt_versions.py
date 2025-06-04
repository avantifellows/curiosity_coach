"""add_user_id_to_prompt_versions

Revision ID: add_user_to_prompt_versions
Revises: 36a75af4bf63
Create Date: 2025-01-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_user_to_prompt_versions'
down_revision: Union[str, None] = '36a75af4bf63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add user_id column to prompt_versions table
    op.add_column('prompt_versions', sa.Column('user_id', sa.Integer(), nullable=True))
    
    # Add production flag column
    op.add_column('prompt_versions', sa.Column('is_production', sa.Boolean(), default=False, nullable=False))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_prompt_versions_user_id', 
        'prompt_versions', 
        'users', 
        ['user_id'], 
        ['id'],
        ondelete='SET NULL'
    )
    
    # Add index for performance
    op.create_index('ix_prompt_versions_user_id', 'prompt_versions', ['user_id'])
    op.create_index('ix_prompt_versions_is_production', 'prompt_versions', ['is_production'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_prompt_versions_user_id', 'prompt_versions')
    op.drop_index('ix_prompt_versions_is_production', 'prompt_versions')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_prompt_versions_user_id', 'prompt_versions', type_='foreignkey')
    
    # Drop columns
    op.drop_column('prompt_versions', 'user_id')
    op.drop_column('prompt_versions', 'is_production') 