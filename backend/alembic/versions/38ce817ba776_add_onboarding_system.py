"""add_onboarding_system

Revision ID: 38ce817ba776
Revises: 95c87a1cdec9
Create Date: 2025-10-02 19:29:52.267956

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38ce817ba776'
down_revision: Union[str, None] = '95c87a1cdec9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create conversation_visits table
    op.create_table(
        'conversation_visits',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('visit_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_conversation_visits_conversation_id', 'conversation_visits', ['conversation_id'], unique=False)
    op.create_index('idx_conversation_visits_visit_number', 'conversation_visits', ['visit_number'], unique=False)
    op.create_unique_constraint('uq_user_visit', 'conversation_visits', ['user_id', 'visit_number'])
    
    # Add prompt_purpose column to prompts table
    op.add_column('prompts', sa.Column('prompt_purpose', sa.String(length=50), nullable=True))
    op.create_index('idx_prompts_purpose', 'prompts', ['prompt_purpose'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove prompt_purpose from prompts
    op.drop_index('idx_prompts_purpose', table_name='prompts')
    op.drop_column('prompts', 'prompt_purpose')
    
    # Remove conversation_visits table
    op.drop_constraint('uq_user_visit', 'conversation_visits', type_='unique')
    op.drop_index('idx_conversation_visits_visit_number', table_name='conversation_visits')
    op.drop_index('idx_conversation_visits_conversation_id', table_name='conversation_visits')
    op.drop_table('conversation_visits')
