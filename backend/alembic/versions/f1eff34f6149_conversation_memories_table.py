"""conversation memories table

Revision ID: f1eff34f6149
Revises: eea6b4548bb3
Create Date: 2025-06-12 14:15:10.042524

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1eff34f6149'
down_revision: Union[str, None] = 'eea6b4548bb3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('conversation_memories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.Integer(), nullable=False),
    sa.Column('memory_data', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_conversation_memories_conversation_id'), 'conversation_memories', ['conversation_id'], unique=True)
    op.create_index(op.f('ix_conversation_memories_id'), 'conversation_memories', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_conversation_memories_id'), table_name='conversation_memories')
    op.drop_index(op.f('ix_conversation_memories_conversation_id'), table_name='conversation_memories')
    op.drop_table('conversation_memories')
    # ### end Alembic commands ###
