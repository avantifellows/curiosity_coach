"""add foundational_unit_id to conversations

Revision ID: a1b2c3d4e5f6
Revises: 8e6b5fdeb99d
Create Date: 2026-05-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "8e6b5fdeb99d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.drop_constraint("fk_conversations_foundational_unit_id", "conversations", type_="foreignkey")
    op.drop_index(op.f("ix_conversations_foundational_unit_id"), table_name="conversations")
    op.drop_column("conversations", "foundational_unit_id")
