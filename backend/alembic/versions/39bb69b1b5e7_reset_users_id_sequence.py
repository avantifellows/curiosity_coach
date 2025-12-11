"""reset_users_and_students_id_sequences

Revision ID: 39bb69b1b5e7
Revises: c9819cf4d257
Create Date: 2025-12-11 23:07:38.347651

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '39bb69b1b5e7'
down_revision: Union[str, None] = 'c9819cf4d257'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Reset the users_id_seq to the current maximum ID in the users table
    # This fixes issues when users are manually inserted with specific IDs
    op.execute(
        "SELECT setval('users_id_seq', (SELECT COALESCE(MAX(id), 1) FROM users));"
    )
    
    # Reset the students_id_seq to the current maximum ID in the students table
    op.execute(
        "SELECT setval('students_id_seq', (SELECT COALESCE(MAX(id), 1) FROM students));"
    )


def downgrade() -> None:
    """Downgrade schema."""
    # No downgrade needed for sequence reset
    pass
