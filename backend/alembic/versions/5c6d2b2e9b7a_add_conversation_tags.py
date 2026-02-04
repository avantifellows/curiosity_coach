"""add_conversation_tags

Revision ID: 5c6d2b2e9b7a
Revises: 59691f10bab7
Create Date: 2026-01-20 10:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c6d2b2e9b7a'
down_revision: Union[str, None] = '59691f10bab7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'conversation_tags',
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('conversation_id', 'tag_id')
    )
    op.create_index(op.f('ix_conversation_tags_conversation_id'), 'conversation_tags', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_tags_tag_id'), 'conversation_tags', ['tag_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_conversation_tags_tag_id'), table_name='conversation_tags')
    op.drop_index(op.f('ix_conversation_tags_conversation_id'), table_name='conversation_tags')
    op.drop_table('conversation_tags')
