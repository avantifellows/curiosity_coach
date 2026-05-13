"""sections replace questions foundational_unit progress

Revision ID: f8a1b2c3d4e5
Revises: d4e5f6a7b8c1
Create Date: 2026-05-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a1b2c3d4e5"
down_revision: Union[str, None] = "d4e5f6a7b8c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS progress CASCADE")
    op.execute("DROP TABLE IF EXISTS foundational_unit CASCADE")
    op.execute("DROP TABLE IF EXISTS questions CASCADE")

    op.create_table(
        "sections",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("kb_source_id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.String(length=255), nullable=False),
        sa.Column("section_name", sa.Text(), nullable=False, server_default=""),
        sa.Column("section_description", sa.Text(), nullable=False, server_default=""),
        sa.Column("section_content", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "section_question_list",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
        ),
        sa.Column("section_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["kb_source_id"], ["kb_source.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("kb_source_id", "section_id", name="uq_sections_kb_section_id"),
    )
    op.create_index(op.f("ix_sections_kb_source_id"), "sections", ["kb_source_id"], unique=False)
    op.create_index(op.f("ix_sections_section_order"), "sections", ["section_order"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_sections_section_order"), table_name="sections")
    op.drop_index(op.f("ix_sections_kb_source_id"), table_name="sections")
    op.drop_table("sections")

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
