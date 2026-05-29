"""add_ingestion_progress_tables

Revision ID: ec11dbf4d8ae
Revises: 5c6d2b2e9b7a
Create Date: 2026-04-06 12:08:08.299985

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec11dbf4d8ae'
down_revision: Union[str, None] = '5c6d2b2e9b7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "kb_source",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
    )

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("kb_source_id", sa.Integer(), nullable=False),
        sa.Column("q_seq_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["kb_source_id"], ["kb_source.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("kb_source_id", "q_seq_number", name="uq_questions_seq_per_source"),
    )
    op.create_index(op.f("ix_questions_kb_source_id"), "questions", ["kb_source_id"], unique=False)

    op.create_table(
        "foundational_unit",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("fu_seq_number", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("question_id", "fu_seq_number", name="uq_fu_seq_per_question"),
    )
    op.create_index(op.f("ix_foundational_unit_question_id"), "foundational_unit", ["question_id"], unique=False)

    op.create_table(
        "progress",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("foundational_unit_id", sa.Integer(), nullable=False),
        sa.Column("conversation_id", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("action_point_given", sa.Text(), nullable=True),
        sa.Column("context", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('not_started', 'ongoing', 'done')",
            name="ck_progress_status_valid",
        ),
        sa.ForeignKeyConstraint(["foundational_unit_id"], ["foundational_unit.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "foundational_unit_id", name="uq_progress_user_fu"),
    )
    op.create_index(op.f("ix_progress_foundational_unit_id"), "progress", ["foundational_unit_id"], unique=False)
    op.create_index(op.f("ix_progress_user_id"), "progress", ["user_id"], unique=False)
    op.create_index(op.f("ix_progress_conversation_id"), "progress", ["conversation_id"], unique=False)
    op.create_index(op.f("ix_progress_status"), "progress", ["status"], unique=False)

    op.create_table(
        "student_progress_tracker",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("context", sa.Text(), nullable=False),
        sa.UniqueConstraint("user_id", name="uq_student_progress_tracker_user"),
    )
    op.create_index(op.f("ix_student_progress_tracker_user_id"), "student_progress_tracker", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_student_progress_tracker_user_id"), table_name="student_progress_tracker")
    op.drop_table("student_progress_tracker")

    op.drop_index(op.f("ix_progress_status"), table_name="progress")
    op.drop_index(op.f("ix_progress_conversation_id"), table_name="progress")
    op.drop_index(op.f("ix_progress_user_id"), table_name="progress")
    op.drop_index(op.f("ix_progress_foundational_unit_id"), table_name="progress")
    op.drop_table("progress")

    op.drop_index(op.f("ix_foundational_unit_question_id"), table_name="foundational_unit")
    op.drop_table("foundational_unit")

    op.drop_index(op.f("ix_questions_kb_source_id"), table_name="questions")
    op.drop_table("questions")

    op.drop_table("kb_source")
