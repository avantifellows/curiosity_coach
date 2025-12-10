"""add created_at to lm_user_knowledge

Revision ID: 052454e90e53
Revises: d0042b026319
Create Date: 2025-10-31 13:50:41.838915

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '052454e90e53'
down_revision: Union[str, None] = 'd0042b026319'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column(
        'lm_user_knowledge',
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )

def downgrade():
    op.drop_column('lm_user_knowledge', 'created_at')
