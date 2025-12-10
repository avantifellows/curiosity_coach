"""add analysis cache tables

Revision ID: 3c0b0a0dcb5d
Revises: 052454e90e53
Create Date: 2025-11-04 20:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3c0b0a0dcb5d'
down_revision: Union[str, None] = '052454e90e53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'class_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('school', sa.String(length=100), nullable=False),
        sa.Column('grade', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(length=10), nullable=True),
        sa.Column('analysis_text', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ready'),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_message_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('school', 'grade', 'section', name='uq_class_analysis_identifier')
    )
    op.create_index(op.f('ix_class_analyses_grade'), 'class_analyses', ['grade'], unique=False)
    op.create_index(op.f('ix_class_analyses_school'), 'class_analyses', ['school'], unique=False)
    op.create_index(op.f('ix_class_analyses_section'), 'class_analyses', ['section'], unique=False)

    op.create_table(
        'student_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('analysis_text', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ready'),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_message_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', name='uq_student_analysis_student_id')
    )
    op.create_index(op.f('ix_student_analyses_student_id'), 'student_analyses', ['student_id'], unique=False)

    op.create_table(
        'analysis_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(length=36), nullable=False),
        sa.Column('analysis_kind', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='queued'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('class_analysis_id', sa.Integer(), nullable=True),
        sa.Column('student_analysis_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['class_analysis_id'], ['class_analyses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['student_analysis_id'], ['student_analyses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('job_id', name='uq_analysis_jobs_job_id'),
        sa.CheckConstraint(
            '(class_analysis_id IS NOT NULL AND student_analysis_id IS NULL) OR '
            '(class_analysis_id IS NULL AND student_analysis_id IS NOT NULL)',
            name='ck_analysis_job_target'
        )
    )
    op.create_index(op.f('ix_analysis_jobs_status'), 'analysis_jobs', ['status'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_class_analysis_id'), 'analysis_jobs', ['class_analysis_id'], unique=False)
    op.create_index(op.f('ix_analysis_jobs_student_analysis_id'), 'analysis_jobs', ['student_analysis_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_analysis_jobs_student_analysis_id'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_class_analysis_id'), table_name='analysis_jobs')
    op.drop_index(op.f('ix_analysis_jobs_status'), table_name='analysis_jobs')
    op.drop_table('analysis_jobs')

    op.drop_index(op.f('ix_student_analyses_student_id'), table_name='student_analyses')
    op.drop_table('student_analyses')

    op.drop_index(op.f('ix_class_analyses_section'), table_name='class_analyses')
    op.drop_index(op.f('ix_class_analyses_school'), table_name='class_analyses')
    op.drop_index(op.f('ix_class_analyses_grade'), table_name='class_analyses')
    op.drop_table('class_analyses')
