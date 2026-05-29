"""drop foundational_unit_id from conversations

Curriculum linkage stays on progress (user + foundational_unit + conversation_id).

Revision ID: d4e5f6a7b8c1
Revises: a1b2c3d4e5f6
Create Date: 2026-05-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c1"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Safe if column was never created (IF EXISTS)
    op.execute(
        "ALTER TABLE conversations DROP CONSTRAINT IF EXISTS fk_conversations_foundational_unit_id"
    )
    op.execute("DROP INDEX IF EXISTS ix_conversations_foundational_unit_id")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS foundational_unit_id")


def downgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("foundational_unit_id", sa.Integer(), nullable=True),
    )
    op.create_index(
        op.f("ix_conversations_foundational_unit_id"),
        "conversations",
        ["foundational_unit_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_conversations_foundational_unit_id",
        "conversations",
        "foundational_unit",
        ["foundational_unit_id"],
        ["id"],
        ondelete="SET NULL",
    )
