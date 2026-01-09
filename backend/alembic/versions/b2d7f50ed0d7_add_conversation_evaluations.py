"""add conversation evaluations table

Revision ID: b2d7f50ed0d7
Revises: a4ee27df147c
Create Date: 2025-02-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2d7f50ed0d7'
down_revision: Union[str, None] = 'a4ee27df147c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'conversation_evaluations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('metrics', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ready'),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_message_hash', sa.String(length=64), nullable=True),
        sa.Column('prompt_version_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['prompt_version_id'], ['prompt_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('conversation_id', name='uq_conversation_evaluations_conversation'),
    )
    op.create_index(op.f('ix_conversation_evaluations_conversation_id'), 'conversation_evaluations', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_conversation_evaluations_status'), 'conversation_evaluations', ['status'], unique=False)

    op.add_column('analysis_jobs', sa.Column('conversation_evaluation_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_analysis_jobs_conversation_evaluation_id'), 'analysis_jobs', ['conversation_evaluation_id'], unique=False)
    op.create_foreign_key(
        'fk_analysis_jobs_conversation_evaluations',
        'analysis_jobs',
        'conversation_evaluations',
        ['conversation_evaluation_id'],
        ['id'],
        ondelete='CASCADE'
    )

    op.drop_constraint('ck_analysis_job_target', 'analysis_jobs', type_='check')
    op.create_check_constraint(
        'ck_analysis_job_target',
        'analysis_jobs',
        """
        ((CASE WHEN class_analysis_id IS NULL THEN 0 ELSE 1 END) +
         (CASE WHEN student_analysis_id IS NULL THEN 0 ELSE 1 END) +
         (CASE WHEN conversation_evaluation_id IS NULL THEN 0 ELSE 1 END)) = 1
        """,
    )


def downgrade() -> None:
    op.drop_constraint('ck_analysis_job_target', 'analysis_jobs', type_='check')
    op.create_check_constraint(
        'ck_analysis_job_target',
        'analysis_jobs',
        """
        ((CASE WHEN class_analysis_id IS NULL THEN 0 ELSE 1 END) +
         (CASE WHEN student_analysis_id IS NULL THEN 0 ELSE 1 END)) = 1
        """,
    )

    op.drop_constraint('fk_analysis_jobs_conversation_evaluations', 'analysis_jobs', type_='foreignkey')
    op.drop_index(op.f('ix_analysis_jobs_conversation_evaluation_id'), table_name='analysis_jobs')
    op.drop_column('analysis_jobs', 'conversation_evaluation_id')

    op.drop_index(op.f('ix_conversation_evaluations_status'), table_name='conversation_evaluations')
    op.drop_index(op.f('ix_conversation_evaluations_conversation_id'), table_name='conversation_evaluations')
    op.drop_table('conversation_evaluations')
