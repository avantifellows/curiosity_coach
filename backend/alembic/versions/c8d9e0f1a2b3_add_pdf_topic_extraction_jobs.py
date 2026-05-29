"""add_pdf_topic_extraction_jobs

Revision ID: c8d9e0f1a2b3
Revises: b7c9d1e2f3a4
Create Date: 2026-05-18

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, None] = "b7c9d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pdf_topic_extraction_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("job_id", name="uq_pdf_topic_extraction_jobs_job_id"),
    )
    op.create_index(op.f("ix_pdf_topic_extraction_jobs_id"), "pdf_topic_extraction_jobs", ["id"], unique=False)
    op.create_index(op.f("ix_pdf_topic_extraction_jobs_job_id"), "pdf_topic_extraction_jobs", ["job_id"], unique=True)
    op.create_index(op.f("ix_pdf_topic_extraction_jobs_status"), "pdf_topic_extraction_jobs", ["status"], unique=False)
    op.create_index(op.f("ix_pdf_topic_extraction_jobs_created_by"), "pdf_topic_extraction_jobs", ["created_by"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_pdf_topic_extraction_jobs_created_by"), table_name="pdf_topic_extraction_jobs")
    op.drop_index(op.f("ix_pdf_topic_extraction_jobs_status"), table_name="pdf_topic_extraction_jobs")
    op.drop_index(op.f("ix_pdf_topic_extraction_jobs_job_id"), table_name="pdf_topic_extraction_jobs")
    op.drop_index(op.f("ix_pdf_topic_extraction_jobs_id"), table_name="pdf_topic_extraction_jobs")
    op.drop_table("pdf_topic_extraction_jobs")
