"""Add pipeline keys for prompt systems

Revision ID: 3b1a6c2d9e4f
Revises: 1f9d9bb0c7a8
Create Date: 2026-04-02 15:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3b1a6c2d9e4f"
down_revision = "1f9d9bb0c7a8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("default_pipeline_key", sa.String(length=50), nullable=False, server_default="legacy"),
    )
    op.add_column(
        "conversations",
        sa.Column("pipeline_key", sa.String(length=50), nullable=False, server_default="legacy"),
    )


def downgrade() -> None:
    op.drop_column("conversations", "pipeline_key")
    op.drop_column("users", "default_pipeline_key")
