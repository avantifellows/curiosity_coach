"""add_file_name_to_kb_source

Revision ID: 8e6b5fdeb99d
Revises: ec11dbf4d8ae
Create Date: 2026-04-06 12:43:02.282169

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8e6b5fdeb99d'
down_revision: Union[str, None] = 'ec11dbf4d8ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("kb_source", sa.Column("file_name", sa.String(length=255), nullable=True))
    op.execute(
        """
        UPDATE kb_source
        SET file_name = CONCAT('legacy_source_', id::text, '.pdf')
        WHERE file_name IS NULL
        """
    )
    op.alter_column("kb_source", "file_name", nullable=False)
    op.create_index(op.f("ix_kb_source_file_name"), "kb_source", ["file_name"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_kb_source_file_name"), table_name="kb_source")
    op.drop_column("kb_source", "file_name")
