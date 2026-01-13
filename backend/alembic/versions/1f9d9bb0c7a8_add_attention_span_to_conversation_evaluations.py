"""Add attention_span to conversation evaluations

Revision ID: 1f9d9bb0c7a8
Revises: b2d7f50ed0d7
Create Date: 2026-01-09 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1f9d9bb0c7a8"
down_revision = "b2d7f50ed0d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "conversation_evaluations",
        sa.Column("attention_span", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("conversation_evaluations", "attention_span")
