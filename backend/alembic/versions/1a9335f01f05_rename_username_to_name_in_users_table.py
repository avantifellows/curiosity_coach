"""rename username to name in users table

Revision ID: 1a9335f01f05
Revises: 48522185c7e1
Create Date: 2025-07-11 17:37:49.610642

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a9335f01f05'
down_revision: Union[str, None] = '48522185c7e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('name', sa.String(length=50), nullable=True))
    op.drop_index('ix_users_username', table_name='users')
    op.create_index(op.f('ix_users_name'), 'users', ['name'], unique=True)
    op.drop_column('users', 'username')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('username', sa.VARCHAR(length=50), autoincrement=False, nullable=True))
    op.drop_index(op.f('ix_users_name'), table_name='users')
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.drop_column('users', 'name')
    # ### end Alembic commands ###
