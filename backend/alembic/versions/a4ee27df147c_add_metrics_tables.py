"""add metrics aggregation tables

Revision ID: a4ee27df147c
Revises: 39bb69b1b5e7
Create Date: 2025-01-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4ee27df147c'
down_revision: Union[str, None] = '39bb69b1b5e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'class_daily_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('school', sa.String(length=100), nullable=False),
        sa.Column('grade', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(length=10), nullable=True),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('total_students', sa.Integer(), nullable=True),
        sa.Column('conversations_started', sa.Integer(), nullable=True),
        sa.Column('active_students', sa.Integer(), nullable=True),
        sa.Column('conversations_with_messages', sa.Integer(), nullable=True),
        sa.Column('total_user_messages', sa.Integer(), nullable=True),
        sa.Column('total_ai_messages', sa.Integer(), nullable=True),
        sa.Column('total_user_words', sa.Integer(), nullable=True),
        sa.Column('total_ai_words', sa.Integer(), nullable=True),
        sa.Column('total_minutes', sa.Numeric(12, 2), nullable=True),
        sa.Column('avg_minutes_per_conversation', sa.Numeric(8, 2), nullable=True),
        sa.Column('avg_user_msgs_per_conversation', sa.Numeric(8, 2), nullable=True),
        sa.Column('avg_ai_msgs_per_conversation', sa.Numeric(8, 2), nullable=True),
        sa.Column('user_messages_after_school', sa.Integer(), nullable=True),
        sa.Column('total_messages_after_school', sa.Integer(), nullable=True),
        sa.Column('after_school_conversations', sa.Integer(), nullable=True),
        sa.Column('avg_user_words_per_message', sa.Numeric(8, 2), nullable=True),
        sa.Column('avg_ai_words_per_message', sa.Numeric(8, 2), nullable=True),
        sa.Column('after_school_user_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('metrics_extra', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), server_onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('school', 'grade', 'section', 'day', name='uq_class_daily_metrics')
    )
    op.create_index(op.f('ix_class_daily_metrics_school'), 'class_daily_metrics', ['school'], unique=False)
    op.create_index(op.f('ix_class_daily_metrics_grade'), 'class_daily_metrics', ['grade'], unique=False)
    op.create_index(op.f('ix_class_daily_metrics_section'), 'class_daily_metrics', ['section'], unique=False)
    op.create_index(op.f('ix_class_daily_metrics_day'), 'class_daily_metrics', ['day'], unique=False)

    op.create_table(
        'class_summary_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('school', sa.String(length=100), nullable=False),
        sa.Column('grade', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(length=10), nullable=True),
        sa.Column('cohort_start', sa.Date(), nullable=False),
        sa.Column('cohort_end', sa.Date(), nullable=False),
        sa.Column('total_students', sa.Integer(), nullable=True),
        sa.Column('total_conversations', sa.Integer(), nullable=True),
        sa.Column('total_user_messages', sa.Integer(), nullable=True),
        sa.Column('total_ai_messages', sa.Integer(), nullable=True),
        sa.Column('total_user_words', sa.Integer(), nullable=True),
        sa.Column('total_ai_words', sa.Integer(), nullable=True),
        sa.Column('total_minutes', sa.Numeric(12, 2), nullable=True),
        sa.Column('user_messages_after_school', sa.Integer(), nullable=True),
        sa.Column('total_messages_after_school', sa.Integer(), nullable=True),
        sa.Column('after_school_conversations', sa.Integer(), nullable=True),
        sa.Column('avg_minutes_per_conversation', sa.Numeric(8, 2), nullable=True),
        sa.Column('avg_user_msgs_per_conversation', sa.Numeric(8, 2), nullable=True),
        sa.Column('avg_ai_msgs_per_conversation', sa.Numeric(8, 2), nullable=True),
        sa.Column('avg_user_words_per_conversation', sa.Numeric(8, 2), nullable=True),
        sa.Column('avg_ai_words_per_conversation', sa.Numeric(8, 2), nullable=True),
        sa.Column('avg_user_words_per_message', sa.Numeric(8, 2), nullable=True),
        sa.Column('avg_ai_words_per_message', sa.Numeric(8, 2), nullable=True),
        sa.Column('after_school_user_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('metrics_extra', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), server_onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('school', 'grade', 'section', 'cohort_start', 'cohort_end', name='uq_class_summary_window')
    )
    op.create_index(op.f('ix_class_summary_metrics_school'), 'class_summary_metrics', ['school'], unique=False)
    op.create_index(op.f('ix_class_summary_metrics_grade'), 'class_summary_metrics', ['grade'], unique=False)
    op.create_index(op.f('ix_class_summary_metrics_section'), 'class_summary_metrics', ['section'], unique=False)

    op.create_table(
        'student_daily_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('day', sa.Date(), nullable=False),
        sa.Column('conversations', sa.Integer(), nullable=True),
        sa.Column('user_messages', sa.Integer(), nullable=True),
        sa.Column('ai_messages', sa.Integer(), nullable=True),
        sa.Column('user_words', sa.Integer(), nullable=True),
        sa.Column('ai_words', sa.Integer(), nullable=True),
        sa.Column('user_messages_after_school', sa.Integer(), nullable=True),
        sa.Column('total_messages_after_school', sa.Integer(), nullable=True),
        sa.Column('minutes_spent', sa.Numeric(12, 2), nullable=True),
        sa.Column('avg_user_words_per_message', sa.Numeric(8, 2), nullable=True),
        sa.Column('avg_ai_words_per_message', sa.Numeric(8, 2), nullable=True),
        sa.Column('metrics_extra', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), server_onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'day', name='uq_student_daily_metrics')
    )
    op.create_index(op.f('ix_student_daily_metrics_student_id'), 'student_daily_metrics', ['student_id'], unique=False)
    op.create_index(op.f('ix_student_daily_metrics_day'), 'student_daily_metrics', ['day'], unique=False)

    op.create_table(
        'student_summary_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('cohort_start', sa.Date(), nullable=False),
        sa.Column('cohort_end', sa.Date(), nullable=False),
        sa.Column('total_conversations', sa.Integer(), nullable=True),
        sa.Column('active_days', sa.Integer(), nullable=True),
        sa.Column('total_minutes', sa.Numeric(12, 2), nullable=True),
        sa.Column('total_user_messages', sa.Integer(), nullable=True),
        sa.Column('total_ai_messages', sa.Integer(), nullable=True),
        sa.Column('total_user_words', sa.Integer(), nullable=True),
        sa.Column('total_ai_words', sa.Integer(), nullable=True),
        sa.Column('user_messages_after_school', sa.Integer(), nullable=True),
        sa.Column('total_messages_after_school', sa.Integer(), nullable=True),
        sa.Column('avg_user_words_per_message', sa.Numeric(8, 2), nullable=True),
        sa.Column('avg_ai_words_per_message', sa.Numeric(8, 2), nullable=True),
        sa.Column('after_school_user_pct', sa.Numeric(5, 2), nullable=True),
        sa.Column('metrics_extra', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), server_onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'cohort_start', 'cohort_end', name='uq_student_summary_window')
    )
    op.create_index(op.f('ix_student_summary_metrics_student_id'), 'student_summary_metrics', ['student_id'], unique=False)

    op.create_table(
        'hourly_activity_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('school', sa.String(length=100), nullable=False),
        sa.Column('grade', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(length=10), nullable=True),
        sa.Column('window_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('window_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_message_count', sa.Integer(), nullable=True),
        sa.Column('ai_message_count', sa.Integer(), nullable=True),
        sa.Column('active_users', sa.Integer(), nullable=True),
        sa.Column('after_school_user_count', sa.Integer(), nullable=True),
        sa.Column('metrics_extra', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), server_onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('school', 'grade', 'section', 'window_start', name='uq_hourly_activity_window')
    )
    op.create_index(op.f('ix_hourly_activity_metrics_school'), 'hourly_activity_metrics', ['school'], unique=False)
    op.create_index(op.f('ix_hourly_activity_metrics_grade'), 'hourly_activity_metrics', ['grade'], unique=False)
    op.create_index(op.f('ix_hourly_activity_metrics_section'), 'hourly_activity_metrics', ['section'], unique=False)
    op.create_index(op.f('ix_hourly_activity_metrics_window_start'), 'hourly_activity_metrics', ['window_start'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_hourly_activity_metrics_window_start'), table_name='hourly_activity_metrics')
    op.drop_index(op.f('ix_hourly_activity_metrics_section'), table_name='hourly_activity_metrics')
    op.drop_index(op.f('ix_hourly_activity_metrics_grade'), table_name='hourly_activity_metrics')
    op.drop_index(op.f('ix_hourly_activity_metrics_school'), table_name='hourly_activity_metrics')
    op.drop_table('hourly_activity_metrics')

    op.drop_index(op.f('ix_student_summary_metrics_student_id'), table_name='student_summary_metrics')
    op.drop_table('student_summary_metrics')

    op.drop_index(op.f('ix_student_daily_metrics_day'), table_name='student_daily_metrics')
    op.drop_index(op.f('ix_student_daily_metrics_student_id'), table_name='student_daily_metrics')
    op.drop_table('student_daily_metrics')

    op.drop_index(op.f('ix_class_summary_metrics_section'), table_name='class_summary_metrics')
    op.drop_index(op.f('ix_class_summary_metrics_grade'), table_name='class_summary_metrics')
    op.drop_index(op.f('ix_class_summary_metrics_school'), table_name='class_summary_metrics')
    op.drop_table('class_summary_metrics')

    op.drop_index(op.f('ix_class_daily_metrics_day'), table_name='class_daily_metrics')
    op.drop_index(op.f('ix_class_daily_metrics_section'), table_name='class_daily_metrics')
    op.drop_index(op.f('ix_class_daily_metrics_grade'), table_name='class_daily_metrics')
    op.drop_index(op.f('ix_class_daily_metrics_school'), table_name='class_daily_metrics')
    op.drop_table('class_daily_metrics')
