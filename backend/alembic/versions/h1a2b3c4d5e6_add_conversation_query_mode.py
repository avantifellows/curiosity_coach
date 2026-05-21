"""add conversation query_mode

Revision ID: h1a2b3c4d5e6
Revises: d9e0f1a2b3c4
Create Date: 2026-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1a2b3c4d5e6"
down_revision: Union[str, None] = "d9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column(
            "query_mode",
            sa.String(length=20),
            nullable=False,
            server_default="include",
        ),
    )
    op.create_check_constraint(
        "ck_conversations_query_mode_valid",
        "conversations",
        "query_mode IN ('include', 'omit', 'opening_only')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_conversations_query_mode_valid", "conversations", type_="check")
    op.drop_column("conversations", "query_mode")
