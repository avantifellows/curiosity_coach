"""add_user_pipeline_slots

Revision ID: d9e0f1a2b3c4
Revises: c8d9e0f1a2b3
Create Date: 2026-05-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d9e0f1a2b3c4"
down_revision: Union[str, None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "tutor_pipeline_key",
            sa.String(length=50),
            nullable=False,
            server_default="tutor_flow_v1",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "quiz_pipeline_key",
            sa.String(length=50),
            nullable=False,
            server_default="quiz_flow_v1",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "quiz_pipeline_key")
    op.drop_column("users", "tutor_pipeline_key")
