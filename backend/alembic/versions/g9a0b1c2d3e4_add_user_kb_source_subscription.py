"""add user_kb_source_subscription

Revision ID: g9a0b1c2d3e4
Revises: f8a1b2c3d4e5
Create Date: 2026-05-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g9a0b1c2d3e4"
down_revision: Union[str, None] = "f8a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_kb_source_subscription",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("kb_source_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["kb_source_id"], ["kb_source.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "kb_source_id", name="uq_user_kb_source_subscription"),
    )
    op.create_index(
        op.f("ix_user_kb_source_subscription_user_id"),
        "user_kb_source_subscription",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_kb_source_subscription_kb_source_id"),
        "user_kb_source_subscription",
        ["kb_source_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_user_kb_source_subscription_kb_source_id"),
        table_name="user_kb_source_subscription",
    )
    op.drop_index(
        op.f("ix_user_kb_source_subscription_user_id"),
        table_name="user_kb_source_subscription",
    )
    op.drop_table("user_kb_source_subscription")
