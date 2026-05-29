"""merge pipeline and topic data heads

Revision ID: b7c9d1e2f3a4
Revises: 3b1a6c2d9e4f, g9a0b1c2d3e4
Create Date: 2026-05-18

"""
from typing import Sequence, Union


revision: str = "b7c9d1e2f3a4"
down_revision: Union[str, Sequence[str], None] = (
    "3b1a6c2d9e4f",
    "g9a0b1c2d3e4",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
