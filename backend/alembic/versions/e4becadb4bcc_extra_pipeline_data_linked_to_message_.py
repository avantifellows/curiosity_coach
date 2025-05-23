"""extra pipeline data linked to message in a new table

Revision ID: e4becadb4bcc
Revises: a12a99fd0c79
Create Date: 2025-05-06 21:43:16.345851

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4becadb4bcc'
down_revision: Union[str, None] = 'a12a99fd0c79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('message_pipeline_data',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('message_id', sa.Integer(), nullable=False),
    sa.Column('pipeline_data', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_message_pipeline_data_id'), 'message_pipeline_data', ['id'], unique=False)
    op.create_index(op.f('ix_message_pipeline_data_message_id'), 'message_pipeline_data', ['message_id'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_message_pipeline_data_message_id'), table_name='message_pipeline_data')
    op.drop_index(op.f('ix_message_pipeline_data_id'), table_name='message_pipeline_data')
    op.drop_table('message_pipeline_data')
    # ### end Alembic commands ###
