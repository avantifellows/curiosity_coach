from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.models import (
    ClassDailyMetrics,
    ClassSummaryMetrics,
    Conversation,
    ConversationEvaluation,
    HourlyActivityMetrics,
    Message,
    Student,
    StudentDailyMetrics,
    StudentSummaryMetrics,
)

logger = logging.getLogger(__name__)


_AFTER_SCHOOL_SQL_CONDITION = """
CASE
    WHEN EXTRACT(DOW FROM m.timestamp AT TIME ZONE 'UTC') IN (0, 6) THEN TRUE
    WHEN EXTRACT(HOUR FROM m.timestamp AT TIME ZONE 'UTC') >= 12 THEN TRUE
    WHEN EXTRACT(HOUR FROM m.timestamp AT TIME ZONE 'UTC') < 3 THEN TRUE
    ELSE FALSE
END
"""


@dataclass
class MetricsRefreshSummary:
    class_daily_rows: int = 0
    student_daily_rows: int = 0
    class_summary_rows: int = 0
    student_summary_rows: int = 0
    hourly_rows: int = 0
    deleted_rows: Dict[str, int] | None = None


def _apply_section_filter(query, column, section: Optional[str]):
    if section is None:
        return query.filter(column.is_(None))
    return query.filter(column == section)


def _decimal_to_float(value: Optional[Any]) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _ensure_decimal_to_float(value: Optional[Any]) -> Optional[float]:
    """Convert Decimal(None) -> float(None) but keep plain numbers untouched."""
    if value is None:
        return None
    return _decimal_to_float(value)


def _empty_evaluation_bucket() -> Dict[str, Any]:
    return {
        'conversation_count': 0,
        'depth_sum': 0.0,
        'depth_count': 0,
        'relevant_sum': 0.0,
        'relevant_count': 0,
        'topics': {},  # term -> {'weight': float, 'count': int}
    }


def _update_topic_totals(
    topic_totals: Dict[str, Dict[str, float]],
    topics: Optional[Iterable[Dict[str, Any]]],
) -> None:
    if not topics:
        return

    for item in topics:
        if not isinstance(item, dict):
            continue
        term = item.get('term')
        if not term:
            continue
        weight_raw = item.get('weight')
        try:
            weight = float(weight_raw)
        except (TypeError, ValueError):
            continue
        term_key = str(term).strip().lower()
        if not term_key:
            continue
        entry = topic_totals.setdefault(term_key, {'weight': 0.0, 'count': 0})
        entry['weight'] += weight
        entry['count'] += 1


def _finalize_topics(topic_totals: Dict[str, Dict[str, float]], limit: int = 5) -> List[Dict[str, Any]]:
    if not topic_totals:
        return []
    sorted_topics = sorted(
        topic_totals.items(),
        key=lambda item: item[1]['weight'],
        reverse=True,
    )
    payload: List[Dict[str, Any]] = []
    for term, data in sorted_topics[:limit]:
        payload.append(
            {
                'term': term,
                'total_weight': data['weight'],
                'conversation_count': data['count'],
            }
        )
    return payload


def _finalize_evaluation_bucket(bucket: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if bucket['conversation_count'] == 0:
        return None

    depth_average = (
        bucket['depth_sum'] / bucket['depth_count']
        if bucket['depth_count']
        else None
    )
    relevant_average = (
        bucket['relevant_sum'] / bucket['relevant_count']
        if bucket['relevant_count']
        else None
    )

    return {
        'conversation_count': bucket['conversation_count'],
        'avg_depth': depth_average,
        'depth_sample_size': bucket['depth_count'],
        'avg_relevant_questions': relevant_average,
        'relevant_sample_size': bucket['relevant_count'],
        'total_relevant_questions': bucket['relevant_sum'],
        'top_topics': _finalize_topics(bucket['topics']),
    }


def _collect_conversation_evaluations(
    db: Session,
    student_ids: Sequence[int],
    start_date: date,
    end_date: date,
) -> Dict[str, Any]:
    if not student_ids:
        return {
            'class_daily': {},
            'class_summary': None,
            'student_daily': {},
            'student_summary': {},
        }

    window_start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    window_end = datetime.combine(end_date + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

    rows = (
        db.query(
            ConversationEvaluation.metrics,
            ConversationEvaluation.status,
            Conversation.updated_at,
            Conversation.created_at,
            Student.id.label('student_id'),
        )
        .join(Conversation, Conversation.id == ConversationEvaluation.conversation_id)
        .join(Student, Student.user_id == Conversation.user_id)
        .filter(Student.id.in_(student_ids))
        .filter(ConversationEvaluation.status == 'ready')
        .filter(ConversationEvaluation.metrics.isnot(None))
        .filter(Conversation.updated_at >= window_start)
        .filter(Conversation.updated_at < window_end)
        .all()
    )

    class_daily_buckets: Dict[date, Dict[str, Any]] = {}
    class_summary_bucket = _empty_evaluation_bucket()
    student_daily_buckets: Dict[int, Dict[date, Dict[str, Any]]] = {}
    student_summary_buckets: Dict[int, Dict[str, Any]] = {}

    for metrics, status, updated_at, created_at, student_id in rows:
        if not isinstance(metrics, dict):
            continue

        reference_dt = updated_at or created_at
        if not reference_dt:
            continue
        reference_day = reference_dt.date()
        if reference_day < start_date or reference_day > end_date:
            continue

        bucket = class_daily_buckets.setdefault(reference_day, _empty_evaluation_bucket())
        student_daily = student_daily_buckets.setdefault(student_id, {})
        student_bucket = student_daily.setdefault(reference_day, _empty_evaluation_bucket())
        student_summary_bucket = student_summary_buckets.setdefault(student_id, _empty_evaluation_bucket())

        for target_bucket in (bucket, class_summary_bucket, student_bucket, student_summary_bucket):
            target_bucket['conversation_count'] += 1
            depth = metrics.get('depth')
            if depth is not None:
                try:
                    depth_value = float(depth)
                except (TypeError, ValueError):
                    depth_value = None
                if depth_value is not None:
                    target_bucket['depth_sum'] += depth_value
                    target_bucket['depth_count'] += 1
            relevant = metrics.get('relevant_question_count')
            if relevant is not None:
                try:
                    relevant_value = float(relevant)
                except (TypeError, ValueError):
                    relevant_value = None
                if relevant_value is not None:
                    target_bucket['relevant_sum'] += relevant_value
                    target_bucket['relevant_count'] += 1
            _update_topic_totals(target_bucket['topics'], metrics.get('topics'))

    class_daily_payload: Dict[date, Dict[str, Any]] = {}
    for day, bucket in class_daily_buckets.items():
        finalized = _finalize_evaluation_bucket(bucket)
        if finalized is not None:
            class_daily_payload[day] = finalized

    student_daily_payload: Dict[int, Dict[date, Dict[str, Any]]] = {}
    for student_id, buckets in student_daily_buckets.items():
        daily_payload: Dict[date, Dict[str, Any]] = {}
        for day, bucket in buckets.items():
            finalized = _finalize_evaluation_bucket(bucket)
            if finalized is not None:
                daily_payload[day] = finalized
        if daily_payload:
            student_daily_payload[student_id] = daily_payload

    student_summary_payload: Dict[int, Dict[str, Any]] = {}
    for student_id, bucket in student_summary_buckets.items():
        finalized = _finalize_evaluation_bucket(bucket)
        if finalized is not None:
            student_summary_payload[student_id] = finalized

    class_summary_payload = _finalize_evaluation_bucket(class_summary_bucket)

    return {
        'class_daily': class_daily_payload,
        'class_summary': class_summary_payload,
        'student_daily': student_daily_payload,
        'student_summary': student_summary_payload,
    }


def refresh_metrics(
    db: Session,
    *,
    school: str,
    grade: int,
    section: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    include_hourly: bool = True,
) -> MetricsRefreshSummary:
    """Recompute class and student metrics for a cohort."""

    school_value = school.strip()
    section_value = section.strip().upper() if section else None

    cohort_query = db.query(Student).filter(
        Student.school == school_value,
        Student.grade == grade,
        Student.roll_number < 100,
    )
    if section_value is not None:
        cohort_query = cohort_query.filter(Student.section == section_value)

    students = cohort_query.all()
    if not students:
        return MetricsRefreshSummary(deleted_rows={})

    student_ids = [student.id for student in students]
    user_ids = [student.user_id for student in students if student.user_id is not None]

    resolved_start, resolved_end = _resolve_date_window(
        db, user_ids, start_date, end_date
    )

    deleted = _delete_existing_metrics(
        db,
        school_value,
        grade,
        section_value,
        student_ids,
        resolved_start,
        resolved_end,
        include_hourly,
    )

    if resolved_start is None or resolved_end is None:
        db.commit()
        return MetricsRefreshSummary(deleted_rows=deleted)

    class_daily_records = _compute_class_daily(
        db,
        school_value,
        grade,
        section_value,
        resolved_start,
        resolved_end,
    )
    student_daily_records = _compute_student_daily(
        db,
        school_value,
        grade,
        section_value,
        resolved_start,
        resolved_end,
    )

    class_summary_extra: Optional[Dict[str, Any]] = None
    student_summary_extra: Dict[int, Dict[str, Any]] = {}

    class_daily_rows = _bulk_insert(
        db,
        ClassDailyMetrics,
        _attach_cohort_fields(
            class_daily_records,
            school=school_value,
            grade=grade,
            section=section_value,
        ),
        conflict_columns=['school', 'grade', 'section', 'day'],
    )

    student_daily_rows = _bulk_insert(
        db,
        StudentDailyMetrics,
        student_daily_records,
        conflict_columns=['student_id', 'day'],
    )

    class_summary_rows, student_summary_rows = _persist_summaries(
        db,
        school_value,
        grade,
        section_value,
        resolved_start,
        resolved_end,
        class_daily_records,
        student_daily_records,
        class_summary_extra,
        student_summary_extra,
    )

    hourly_rows = 0
    if include_hourly:
        hourly_rows = _refresh_hourly_activity(
            db,
            school_value,
            grade,
            section_value,
            user_ids,
        )

    db.commit()

    return MetricsRefreshSummary(
        class_daily_rows=class_daily_rows,
        student_daily_rows=student_daily_rows,
        class_summary_rows=class_summary_rows,
        student_summary_rows=student_summary_rows,
        hourly_rows=hourly_rows,
        deleted_rows=deleted,
    )


def _resolve_date_window(
    db: Session,
    user_ids: Sequence[int],
    start_date: Optional[date],
    end_date: Optional[date],
) -> tuple[Optional[date], Optional[date]]:
    if start_date and end_date:
        return start_date, end_date

    if not user_ids:
        return None, None

    min_ts, max_ts = (
        db.query(func.min(Message.timestamp), func.max(Message.timestamp))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id.in_(user_ids))
        .first()
    )

    if min_ts is None or max_ts is None:
        return None, None

    computed_start = start_date or min_ts.date()
    computed_end = end_date or max_ts.date()
    if computed_end < computed_start:
        computed_end = computed_start

    return computed_start, computed_end


def _delete_existing_metrics(
    db: Session,
    school: str,
    grade: int,
    section: Optional[str],
    student_ids: Sequence[int],
    start_date: Optional[date],
    end_date: Optional[date],
    include_hourly: bool,
) -> Dict[str, int]:
    deleted_counts: Dict[str, int] = {}

    def _apply_day_range(query, column):
        if start_date is not None:
            query = query.filter(column >= start_date)
        if end_date is not None:
            query = query.filter(column <= end_date)
        return query

    class_daily_q = db.query(ClassDailyMetrics).filter(
        ClassDailyMetrics.school == school,
        ClassDailyMetrics.grade == grade,
    )
    class_daily_q = _apply_section_filter(class_daily_q, ClassDailyMetrics.section, section)
    class_daily_q = _apply_day_range(class_daily_q, ClassDailyMetrics.day)
    deleted_counts['class_daily_metrics'] = class_daily_q.delete(synchronize_session=False)

    student_daily_q = db.query(StudentDailyMetrics).filter(
        StudentDailyMetrics.student_id.in_(student_ids)
    )
    student_daily_q = _apply_day_range(student_daily_q, StudentDailyMetrics.day)
    deleted_counts['student_daily_metrics'] = student_daily_q.delete(synchronize_session=False)

    class_summary_q = db.query(ClassSummaryMetrics).filter(
        ClassSummaryMetrics.school == school,
        ClassSummaryMetrics.grade == grade,
    )
    class_summary_q = _apply_section_filter(class_summary_q, ClassSummaryMetrics.section, section)
    class_summary_q = class_summary_q.filter(
        ClassSummaryMetrics.cohort_start == start_date,
        ClassSummaryMetrics.cohort_end == end_date,
    )
    deleted_counts['class_summary_metrics'] = class_summary_q.delete(synchronize_session=False)

    student_summary_q = db.query(StudentSummaryMetrics).filter(
        StudentSummaryMetrics.student_id.in_(student_ids),
        StudentSummaryMetrics.cohort_start == start_date,
        StudentSummaryMetrics.cohort_end == end_date,
    )
    deleted_counts['student_summary_metrics'] = student_summary_q.delete(synchronize_session=False)

    if include_hourly:
        window_bounds = _hourly_window_bounds()
        hourly_q = db.query(HourlyActivityMetrics).filter(
            HourlyActivityMetrics.school == school,
            HourlyActivityMetrics.grade == grade,
        )
        hourly_q = _apply_section_filter(hourly_q, HourlyActivityMetrics.section, section)
        hourly_q = hourly_q.filter(
            HourlyActivityMetrics.window_start >= window_bounds['start'],
            HourlyActivityMetrics.window_start < window_bounds['end'],
        )
        deleted_counts['hourly_activity_metrics'] = hourly_q.delete(synchronize_session=False)

    return deleted_counts


def _compute_class_daily(
    db: Session,
    school: str,
    grade: int,
    section: Optional[str],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    section_filter_value = section or ''
    sql = text(
        f"""
        WITH cohort_students AS (
            SELECT s.id AS student_id,
                   s.user_id
            FROM students s
            WHERE s.school = :school
              AND s.grade = :grade
              AND COALESCE(s.section, '') = :section
              AND s.roll_number < 100
        ),
        valid_conversations AS (
            SELECT c.id AS conversation_id,
                   c.user_id
            FROM conversations c
            JOIN cohort_students cs ON cs.user_id = c.user_id
            WHERE EXISTS (
                SELECT 1
                FROM messages m
                WHERE m.conversation_id = c.id
                  AND m.is_user = TRUE
            )
        ),
        conversation_windows AS (
            SELECT vc.conversation_id,
                   vc.user_id,
                   MIN(m.timestamp) AS first_msg_at,
                   MAX(m.timestamp) AS last_msg_at,
                   EXTRACT(EPOCH FROM (MAX(m.timestamp) - MIN(m.timestamp))) / 60.0 AS minutes_spent
            FROM valid_conversations vc
            JOIN messages m ON m.conversation_id = vc.conversation_id
            GROUP BY vc.conversation_id, vc.user_id
        ),
        message_details AS (
            SELECT m.conversation_id,
                   vc.user_id,
                   m.is_user,
                   (m.timestamp AT TIME ZONE 'UTC')::date AS message_day,
                   {_AFTER_SCHOOL_SQL_CONDITION} AS is_after_school,
                   COALESCE(cardinality(regexp_split_to_array(NULLIF(trim(m.content), ''), '\\s+')), 0) AS word_count
            FROM valid_conversations vc
            JOIN messages m ON m.conversation_id = vc.conversation_id
        ),
        day_message_stats AS (
            SELECT md.message_day AS day,
                   COUNT(DISTINCT CASE WHEN md.is_user THEN md.user_id END) AS active_students,
                   COUNT(DISTINCT md.conversation_id) AS conversations_with_messages,
                   SUM(CASE WHEN md.is_user THEN 1 ELSE 0 END) AS total_user_messages,
                   SUM(CASE WHEN NOT md.is_user THEN 1 ELSE 0 END) AS total_ai_messages,
                   SUM(CASE WHEN md.is_user THEN md.word_count ELSE 0 END) AS total_user_words,
                   SUM(CASE WHEN NOT md.is_user THEN md.word_count ELSE 0 END) AS total_ai_words,
                   SUM(CASE WHEN md.is_user AND md.is_after_school THEN 1 ELSE 0 END) AS user_messages_after_school,
                   SUM(CASE WHEN md.is_after_school THEN 1 ELSE 0 END) AS total_messages_after_school,
                   COUNT(DISTINCT CASE WHEN md.is_user AND md.is_after_school THEN md.conversation_id END) AS after_school_conversations
            FROM message_details md
            GROUP BY md.message_day
        ),
        conversation_minutes AS (
            SELECT (cw.first_msg_at AT TIME ZONE 'UTC')::date AS day,
                   COUNT(*) AS conversations_started,
                   SUM(cw.minutes_spent) AS total_minutes
            FROM conversation_windows cw
            WHERE cw.first_msg_at IS NOT NULL
            GROUP BY day
        ),
        day_series AS (
            SELECT generate_series(:start_date, :end_date, interval '1 day')::date AS day
        )
        SELECT
            ds.day,
            (SELECT COUNT(*) FROM cohort_students) AS total_students,
            COALESCE(cm.conversations_started, 0) AS conversations_started,
            COALESCE(dms.active_students, 0) AS active_students,
            COALESCE(dms.conversations_with_messages, 0) AS conversations_with_messages,
            COALESCE(dms.total_user_messages, 0) AS total_user_messages,
            COALESCE(dms.total_ai_messages, 0) AS total_ai_messages,
            COALESCE(dms.total_user_words, 0) AS total_user_words,
            COALESCE(dms.total_ai_words, 0) AS total_ai_words,
            COALESCE(cm.total_minutes, 0) AS total_minutes,
            CASE
                WHEN cm.conversations_started > 0 THEN cm.total_minutes / cm.conversations_started
                ELSE NULL
            END AS avg_minutes_per_conversation,
            CASE
                WHEN cm.conversations_started > 0 THEN dms.total_user_messages::numeric / cm.conversations_started
                ELSE NULL
            END AS avg_user_msgs_per_conversation,
            CASE
                WHEN cm.conversations_started > 0 THEN dms.total_ai_messages::numeric / cm.conversations_started
                ELSE NULL
            END AS avg_ai_msgs_per_conversation,
            COALESCE(dms.user_messages_after_school, 0) AS user_messages_after_school,
            COALESCE(dms.total_messages_after_school, 0) AS total_messages_after_school,
            COALESCE(dms.after_school_conversations, 0) AS after_school_conversations,
            CASE
                WHEN dms.total_user_messages > 0 THEN dms.total_user_words::numeric / dms.total_user_messages
                ELSE NULL
            END AS avg_user_words_per_message,
            CASE
                WHEN dms.total_ai_messages > 0 THEN dms.total_ai_words::numeric / dms.total_ai_messages
                ELSE NULL
            END AS avg_ai_words_per_message,
            CASE
                WHEN dms.total_user_messages > 0 THEN (dms.user_messages_after_school::numeric * 100) / dms.total_user_messages
                ELSE NULL
            END AS after_school_user_pct
        FROM day_series ds
        LEFT JOIN day_message_stats dms ON dms.day = ds.day
        LEFT JOIN conversation_minutes cm ON cm.day = ds.day
        ORDER BY ds.day
        """
    )

    result = db.execute(
        sql,
        {
            'school': school,
            'grade': grade,
            'section': section_filter_value,
            'start_date': start_date,
            'end_date': end_date,
        },
    )
    records: List[Dict[str, Any]] = [dict(row._mapping) for row in result]
    return records


def _compute_student_daily(
    db: Session,
    school: str,
    grade: int,
    section: Optional[str],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    section_filter_value = section or ''
    sql = text(
        f"""
        WITH cohort_students AS (
            SELECT s.id AS student_id,
                   s.user_id,
                   s.first_name
            FROM students s
            WHERE s.school = :school
              AND s.grade = :grade
              AND COALESCE(s.section, '') = :section
              AND s.roll_number < 100
        ),
        valid_conversations AS (
            SELECT c.id AS conversation_id,
                   c.user_id
            FROM conversations c
            JOIN cohort_students cs ON cs.user_id = c.user_id
            WHERE EXISTS (
                SELECT 1
                FROM messages m
                WHERE m.conversation_id = c.id
                  AND m.is_user = TRUE
            )
        ),
        message_details AS (
            SELECT m.conversation_id,
                   cs.student_id,
                   cs.first_name,
                   m.is_user,
                   (m.timestamp AT TIME ZONE 'UTC')::date AS message_day,
                   {_AFTER_SCHOOL_SQL_CONDITION} AS is_after_school,
                   COALESCE(cardinality(regexp_split_to_array(NULLIF(trim(m.content), ''), '\\s+')), 0) AS word_count
            FROM valid_conversations vc
            JOIN messages m ON m.conversation_id = vc.conversation_id
            JOIN cohort_students cs ON cs.user_id = vc.user_id
        ),
        conversation_windows AS (
            SELECT vc.conversation_id,
                   vc.user_id,
                   MIN(m.timestamp) AS first_msg_at,
                   MAX(m.timestamp) AS last_msg_at,
                   EXTRACT(EPOCH FROM (MAX(m.timestamp) - MIN(m.timestamp))) / 60.0 AS minutes_spent
            FROM valid_conversations vc
            JOIN messages m ON m.conversation_id = vc.conversation_id
            GROUP BY vc.conversation_id, vc.user_id
        ),
        student_day_messages AS (
            SELECT md.student_id,
                   md.first_name,
                   md.message_day AS day,
                   COUNT(DISTINCT md.conversation_id) AS conversations,
                   SUM(CASE WHEN md.is_user THEN 1 ELSE 0 END) AS user_messages,
                   SUM(CASE WHEN NOT md.is_user THEN 1 ELSE 0 END) AS ai_messages,
                   SUM(CASE WHEN md.is_user THEN md.word_count ELSE 0 END) AS user_words,
                   SUM(CASE WHEN NOT md.is_user THEN md.word_count ELSE 0 END) AS ai_words,
                   SUM(CASE WHEN md.is_user AND md.is_after_school THEN 1 ELSE 0 END) AS user_messages_after_school,
                   SUM(CASE WHEN md.is_after_school THEN 1 ELSE 0 END) AS total_messages_after_school
            FROM message_details md
            GROUP BY md.student_id, md.first_name, md.message_day
        ),
        student_day_minutes AS (
            SELECT cs.student_id,
                   cs.first_name,
                   (cw.first_msg_at AT TIME ZONE 'UTC')::date AS day,
                   SUM(cw.minutes_spent) AS minutes_spent
            FROM conversation_windows cw
            JOIN cohort_students cs ON cs.user_id = cw.user_id
            WHERE cw.first_msg_at IS NOT NULL
            GROUP BY cs.student_id, cs.first_name, (cw.first_msg_at AT TIME ZONE 'UTC')::date
        )
        SELECT
            COALESCE(sdm.student_id, sdmn.student_id) AS student_id,
            COALESCE(sdm.first_name, sdmn.first_name) AS first_name,
            COALESCE(sdm.day, sdmn.day) AS day,
            COALESCE(sdm.conversations, 0) AS conversations,
            COALESCE(sdm.user_messages, 0) AS user_messages,
            COALESCE(sdm.ai_messages, 0) AS ai_messages,
            COALESCE(sdm.user_words, 0) AS user_words,
            COALESCE(sdm.ai_words, 0) AS ai_words,
            COALESCE(sdm.user_messages_after_school, 0) AS user_messages_after_school,
            COALESCE(sdm.total_messages_after_school, 0) AS total_messages_after_school,
            COALESCE(sdmn.minutes_spent, 0) AS minutes_spent,
            CASE
                WHEN COALESCE(sdm.user_messages, 0) > 0 THEN COALESCE(sdm.user_words, 0)::numeric / sdm.user_messages
                ELSE NULL
            END AS avg_user_words_per_message,
            CASE
                WHEN COALESCE(sdm.ai_messages, 0) > 0 THEN COALESCE(sdm.ai_words, 0)::numeric / sdm.ai_messages
                ELSE NULL
            END AS avg_ai_words_per_message
        FROM student_day_messages sdm
        FULL OUTER JOIN student_day_minutes sdmn
          ON sdmn.student_id = sdm.student_id AND sdmn.day = sdm.day
        WHERE COALESCE(sdm.day, sdmn.day) BETWEEN :start_date AND :end_date
        ORDER BY COALESCE(sdm.first_name, sdmn.first_name), COALESCE(sdm.day, sdmn.day)
        """
    )

    result = db.execute(
        sql,
        {
            'school': school,
            'grade': grade,
            'section': section_filter_value,
            'start_date': start_date,
            'end_date': end_date,
        },
    )
    records: List[Dict[str, Any]] = []
    for row in result:
        data = dict(row._mapping)
        data.pop('first_name', None)
        records.append(data)
    return records


def _persist_summaries(
    db: Session,
    school: str,
    grade: int,
    section: Optional[str],
    start_date: date,
    end_date: date,
    class_daily_records: List[Dict[str, Any]],
    student_daily_records: List[Dict[str, Any]],
    class_summary_extra: Optional[Dict[str, Any]] = None,
    student_summary_extra: Optional[Dict[int, Dict[str, Any]]] = None,
) -> tuple[int, int]:
    class_summary_row = _compute_class_summary(
        school,
        grade,
        section,
        start_date,
        end_date,
        class_daily_records,
    )
    class_summary_rows = 0
    if class_summary_row:
        class_summary_row.pop('metrics_extra', None)
        class_summary_rows = _bulk_insert(
            db,
            ClassSummaryMetrics,
            [class_summary_row],
            conflict_columns=['school', 'grade', 'section', 'cohort_start', 'cohort_end'],
        )

    student_summary_rows = 0
    student_summary_payload = _compute_student_summaries(
        student_daily_records,
        start_date,
        end_date,
    )
    if student_summary_payload:
        for record in student_summary_payload:
            record.pop('metrics_extra', None)
        student_summary_rows = _bulk_insert(
            db,
            StudentSummaryMetrics,
            student_summary_payload,
            conflict_columns=['student_id', 'cohort_start', 'cohort_end'],
        )

    return class_summary_rows, student_summary_rows


def _compute_class_summary(
    school: str,
    grade: int,
    section: Optional[str],
    start_date: date,
    end_date: date,
    class_daily_records: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not class_daily_records:
        return None

    total_students = max(record.get('total_students') or 0 for record in class_daily_records)
    total_conversations = sum(record.get('conversations_started') or 0 for record in class_daily_records)
    total_user_messages = sum(record.get('total_user_messages') or 0 for record in class_daily_records)
    total_ai_messages = sum(record.get('total_ai_messages') or 0 for record in class_daily_records)
    total_user_words = sum(record.get('total_user_words') or 0 for record in class_daily_records)
    total_ai_words = sum(record.get('total_ai_words') or 0 for record in class_daily_records)
    total_minutes = sum(record.get('total_minutes') or 0 for record in class_daily_records)
    user_messages_after_school = sum(
        record.get('user_messages_after_school') or 0 for record in class_daily_records
    )
    total_messages_after_school = sum(
        record.get('total_messages_after_school') or 0 for record in class_daily_records
    )
    after_school_conversations = sum(
        record.get('after_school_conversations') or 0 for record in class_daily_records
    )

    avg_minutes_per_conversation = (
        total_minutes / total_conversations if total_conversations else None
    )
    avg_user_msgs_per_conversation = (
        total_user_messages / total_conversations if total_conversations else None
    )
    avg_ai_msgs_per_conversation = (
        total_ai_messages / total_conversations if total_conversations else None
    )
    avg_user_words_per_conversation = (
        total_user_words / total_conversations if total_conversations else None
    )
    avg_ai_words_per_conversation = (
        total_ai_words / total_conversations if total_conversations else None
    )
    avg_user_words_per_message = (
        total_user_words / total_user_messages if total_user_messages else None
    )
    avg_ai_words_per_message = (
        total_ai_words / total_ai_messages if total_ai_messages else None
    )
    after_school_user_pct = (
        (user_messages_after_school * 100) / total_user_messages
        if total_user_messages
        else None
    )

    return {
        'school': school,
        'grade': grade,
        'section': section,
        'cohort_start': start_date,
        'cohort_end': end_date,
        'total_students': total_students,
        'total_conversations': total_conversations,
        'total_user_messages': total_user_messages,
        'total_ai_messages': total_ai_messages,
        'total_user_words': total_user_words,
        'total_ai_words': total_ai_words,
        'total_minutes': total_minutes,
        'user_messages_after_school': user_messages_after_school,
        'total_messages_after_school': total_messages_after_school,
        'after_school_conversations': after_school_conversations,
        'avg_minutes_per_conversation': avg_minutes_per_conversation,
        'avg_user_msgs_per_conversation': avg_user_msgs_per_conversation,
        'avg_ai_msgs_per_conversation': avg_ai_msgs_per_conversation,
        'avg_user_words_per_conversation': avg_user_words_per_conversation,
        'avg_ai_words_per_conversation': avg_ai_words_per_conversation,
        'avg_user_words_per_message': avg_user_words_per_message,
        'avg_ai_words_per_message': avg_ai_words_per_message,
        'after_school_user_pct': after_school_user_pct,
    }


def _compute_student_summaries(
    student_daily_records: List[Dict[str, Any]],
    start_date: date,
    end_date: date,
) -> List[Dict[str, Any]]:
    summaries: Dict[int, Dict[str, Any]] = {}
    for record in student_daily_records:
        student_id = record['student_id']
        payload = summaries.setdefault(
            student_id,
            {
                'student_id': student_id,
                'cohort_start': start_date,
                'cohort_end': end_date,
                'total_conversations': 0,
                'active_days': 0,
                'total_minutes': 0,
                'total_user_messages': 0,
                'total_ai_messages': 0,
                'total_user_words': 0,
                'total_ai_words': 0,
                'user_messages_after_school': 0,
                'total_messages_after_school': 0,
            },
        )

        payload['total_conversations'] += record.get('conversations') or 0
        payload['total_minutes'] += float(record.get('minutes_spent') or 0)
        payload['total_user_messages'] += record.get('user_messages') or 0
        payload['total_ai_messages'] += record.get('ai_messages') or 0
        payload['total_user_words'] += record.get('user_words') or 0
        payload['total_ai_words'] += record.get('ai_words') or 0
        payload['user_messages_after_school'] += record.get('user_messages_after_school') or 0
        payload['total_messages_after_school'] += record.get('total_messages_after_school') or 0
        payload['active_days'] += 1

    for payload in summaries.values():
        total_user_messages = payload['total_user_messages']
        total_ai_messages = payload['total_ai_messages']
        total_user_words = payload['total_user_words']
        total_ai_words = payload['total_ai_words']
        payload['avg_user_words_per_message'] = (
            total_user_words / total_user_messages if total_user_messages else None
        )
        payload['avg_ai_words_per_message'] = (
            total_ai_words / total_ai_messages if total_ai_messages else None
        )
        payload['after_school_user_pct'] = (
            (payload['user_messages_after_school'] * 100) / total_user_messages
            if total_user_messages
            else None
        )

    return list(summaries.values())


def _refresh_hourly_activity(
    db: Session,
    school: str,
    grade: int,
    section: Optional[str],
    user_ids: Sequence[int],
) -> int:
    if not user_ids:
        return 0

    bounds = _hourly_window_bounds()
    section_filter_value = section or ''
    sql = text(
        f"""
        WITH cohort_users AS (
            SELECT DISTINCT s.user_id
            FROM students s
            WHERE s.school = :school
              AND s.grade = :grade
              AND COALESCE(s.section, '') = :section
              AND s.roll_number < 100
        ),
        message_source AS (
            SELECT
                date_trunc('hour', m.timestamp) AS bucket_start,
                m.is_user,
                m.conversation_id,
                {_AFTER_SCHOOL_SQL_CONDITION} AS is_after_school
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            JOIN cohort_users cu ON cu.user_id = c.user_id
            WHERE m.timestamp >= :window_start AND m.timestamp < :window_end
        ),
        hourly AS (
            SELECT
                bucket_start,
                COUNT(*) FILTER (WHERE is_user) AS user_message_count,
                COUNT(*) FILTER (WHERE NOT is_user) AS ai_message_count,
                COUNT(DISTINCT CASE WHEN is_user THEN c.user_id END) AS active_users,
                COUNT(DISTINCT CASE WHEN is_user AND is_after_school THEN c.user_id END) AS after_school_user_count
            FROM message_source ms
            JOIN conversations c ON c.id = ms.conversation_id
            GROUP BY bucket_start
        )
        SELECT
            series.bucket_start,
            COALESCE(h.user_message_count, 0) AS user_message_count,
            COALESCE(h.ai_message_count, 0) AS ai_message_count,
            COALESCE(h.active_users, 0) AS active_users,
            COALESCE(h.after_school_user_count, 0) AS after_school_user_count
        FROM (
            SELECT generate_series(:window_start, :window_end - interval '1 hour', interval '1 hour') AS bucket_start
        ) AS series
        LEFT JOIN hourly h ON h.bucket_start = series.bucket_start
        ORDER BY series.bucket_start
        """
    )

    result = db.execute(
        sql,
        {
            'school': school,
            'grade': grade,
            'section': section_filter_value,
            'window_start': bounds['start'],
            'window_end': bounds['end'],
        },
    )

    rows = []
    for record in result:
        bucket_start = record.bucket_start
        bucket_end = bucket_start + timedelta(hours=1)
        rows.append(
            {
                'school': school,
                'grade': grade,
                'section': section,
                'window_start': bucket_start,
                'window_end': bucket_end,
                'user_message_count': record.user_message_count,
                'ai_message_count': record.ai_message_count,
                'active_users': record.active_users,
                'after_school_user_count': record.after_school_user_count,
            }
        )

    return _bulk_insert(
        db,
        HourlyActivityMetrics,
        rows,
        conflict_columns=['school', 'grade', 'section', 'window_start'],
    )


def get_student_daily_series(
    db: Session,
    *,
    school: str,
    grade: int,
    section: Optional[str] = None,
    student_ids: Sequence[int],
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> List[Dict[str, Any]]:
    if not student_ids:
        return []

    school_value = school.strip()
    section_value = section.strip().upper() if section else None

    cohort_students_query = db.query(Student).filter(
        Student.school == school_value,
        Student.grade == grade,
        Student.roll_number < 100,
    )

    if section_value is None:
        cohort_students_query = cohort_students_query.filter(Student.section.is_(None))
    else:
        cohort_students_query = cohort_students_query.filter(Student.section == section_value)

    cohort_students_query = cohort_students_query.filter(Student.id.in_(student_ids))

    cohort_students = cohort_students_query.all()
    if not cohort_students:
        return []

    student_lookup = {student.id: student for student in cohort_students}

    metrics_query = (
        db.query(StudentDailyMetrics)
        .filter(StudentDailyMetrics.student_id.in_(student_lookup.keys()))
    )

    if start_date:
        metrics_query = metrics_query.filter(StudentDailyMetrics.day >= start_date)
    if end_date:
        metrics_query = metrics_query.filter(StudentDailyMetrics.day <= end_date)

    metrics_rows = (
        metrics_query
        .order_by(StudentDailyMetrics.student_id.asc(), StudentDailyMetrics.day.asc())
        .all()
    )

    series_map: Dict[int, Dict[str, Any]] = {
        student_id: {
            'student_id': student_id,
            'student_name': student_lookup[student_id].first_name,
            'records': [],
        }
        for student_id in student_lookup.keys()
    }

    for metrics in metrics_rows:
        records = series_map[metrics.student_id]['records']
        records.append(
            {
                'day': metrics.day,
                'user_messages': metrics.user_messages,
                'ai_messages': metrics.ai_messages,
                'user_words': metrics.user_words,
                'ai_words': metrics.ai_words,
                'minutes_spent': _ensure_decimal_to_float(metrics.minutes_spent),
                'user_messages_after_school': metrics.user_messages_after_school,
                'total_messages_after_school': metrics.total_messages_after_school,
                'avg_depth': None,
                'total_relevant_questions': None,
            }
        )

    eval_start = start_date
    eval_end = end_date
    if metrics_rows and (eval_start is None or eval_end is None):
        days = [row.day for row in metrics_rows]
        eval_start = eval_start or min(days)
        eval_end = eval_end or max(days)

    if student_ids and eval_start is not None and eval_end is not None:
        evaluation_rollups = _collect_conversation_evaluations(
            db,
            student_ids,
            eval_start,
            eval_end,
        )
        student_daily_eval = evaluation_rollups.get('student_daily', {})
        for student_id, payload in series_map.items():
            daily_map = student_daily_eval.get(student_id, {})
            for record in payload['records']:
                extra = daily_map.get(record['day'])
                if extra:
                    record['metrics_extra'] = extra
                    record['avg_depth'] = extra.get('avg_depth')
                    record['total_relevant_questions'] = extra.get('total_relevant_questions')

    # Ensure deterministic ordering by student name then id for stability
    ordered_series = sorted(
        series_map.values(),
        key=lambda item: (item['student_name'] or '', item['student_id']),
    )

    return ordered_series


def get_dashboard_metrics(
    db: Session,
    *,
    school: str,
    grade: int,
    section: Optional[str] = None,
) -> Dict[str, Any]:
    school_value = school.strip()
    section_value = section.strip().upper() if section else None

    student_query = db.query(Student).filter(
        Student.school == school_value,
        Student.grade == grade,
        Student.roll_number < 100,
    )
    student_query = _apply_section_filter(student_query, Student.section, section_value)
    students = student_query.all()
    student_ids = [student.id for student in students]

    class_summary_query = db.query(ClassSummaryMetrics).filter(
        ClassSummaryMetrics.school == school_value,
        ClassSummaryMetrics.grade == grade,
    )
    class_summary_query = _apply_section_filter(class_summary_query, ClassSummaryMetrics.section, section_value)
    class_summary = class_summary_query.order_by(ClassSummaryMetrics.updated_at.desc()).first()

    class_summary_payload: Optional[Dict[str, Any]] = None
    summary_window: Optional[Tuple[date, date]] = None

    if class_summary:
        class_summary_payload = {
            'cohort_start': class_summary.cohort_start,
            'cohort_end': class_summary.cohort_end,
            'total_students': class_summary.total_students,
            'total_conversations': class_summary.total_conversations,
            'total_user_messages': class_summary.total_user_messages,
            'total_ai_messages': class_summary.total_ai_messages,
            'total_user_words': class_summary.total_user_words,
            'total_ai_words': class_summary.total_ai_words,
            'total_minutes': _decimal_to_float(class_summary.total_minutes),
            'avg_minutes_per_conversation': _decimal_to_float(class_summary.avg_minutes_per_conversation),
            'avg_user_msgs_per_conversation': _decimal_to_float(class_summary.avg_user_msgs_per_conversation),
            'avg_ai_msgs_per_conversation': _decimal_to_float(class_summary.avg_ai_msgs_per_conversation),
            'avg_user_words_per_conversation': _decimal_to_float(class_summary.avg_user_words_per_conversation),
            'avg_ai_words_per_conversation': _decimal_to_float(class_summary.avg_ai_words_per_conversation),
            'avg_user_words_per_message': _decimal_to_float(class_summary.avg_user_words_per_message),
            'avg_ai_words_per_message': _decimal_to_float(class_summary.avg_ai_words_per_message),
            'user_messages_after_school': class_summary.user_messages_after_school,
            'total_messages_after_school': class_summary.total_messages_after_school,
            'after_school_conversations': class_summary.after_school_conversations,
            'after_school_user_pct': _decimal_to_float(class_summary.after_school_user_pct),
            'total_relevant_questions': None,
            'avg_depth': None,
        }
        summary_window = (class_summary.cohort_start, class_summary.cohort_end)

    class_daily_query = db.query(ClassDailyMetrics).filter(
        ClassDailyMetrics.school == school_value,
        ClassDailyMetrics.grade == grade,
    )
    class_daily_query = _apply_section_filter(class_daily_query, ClassDailyMetrics.section, section_value)
    recent_daily_rows = (
        class_daily_query
        .order_by(
            ClassDailyMetrics.total_user_messages.desc().nullslast(),
            ClassDailyMetrics.day.desc(),
        )
        .limit(7)
        .all()
    )
    recent_days = [
        {
            'day': row.day,
            'total_minutes': _decimal_to_float(row.total_minutes),
            'total_user_messages': row.total_user_messages,
            'total_ai_messages': row.total_ai_messages,
            'active_students': row.active_students,
            'user_messages_after_school': row.user_messages_after_school,
            'after_school_conversations': row.after_school_conversations,
            'avg_depth': None,
            'total_relevant_questions': None,
        }
        for row in recent_daily_rows
    ]

    recent_days = [
        entry
        for entry in recent_days
        if (entry['total_user_messages'] or 0) > 0
    ]

    student_snapshots: List[Dict[str, Any]] = []
    if summary_window is not None:
        start, end = summary_window
        student_summary_query = (
            db.query(StudentSummaryMetrics, Student)
            .join(Student, StudentSummaryMetrics.student_id == Student.id)
            .filter(
                Student.school == school_value,
                Student.grade == grade,
                Student.roll_number < 100,
            )
        )
        if section_value is None:
            student_summary_query = student_summary_query.filter(Student.section.is_(None))
        else:
            student_summary_query = student_summary_query.filter(Student.section == section_value)

        student_summary_query = student_summary_query.filter(
            StudentSummaryMetrics.cohort_start == start,
            StudentSummaryMetrics.cohort_end == end,
        )

        summary_rows = student_summary_query.all()
        for summary_row, student in summary_rows:
            total_user_messages = summary_row.total_user_messages or 0
            total_user_words = summary_row.total_user_words or 0
            avg_words_per_message: Optional[float]
            if total_user_messages:
                avg_words_per_message = float(total_user_words) / float(total_user_messages)
            else:
                avg_words_per_message = None

            student_snapshots.append(
                {
                    'student_id': summary_row.student_id,
                    'student_name': student.first_name,
                    'total_minutes': _decimal_to_float(summary_row.total_minutes),
                    'total_user_messages': total_user_messages,
                    'total_user_words': total_user_words,
                    'total_ai_messages': summary_row.total_ai_messages,
                    'after_school_user_pct': _decimal_to_float(summary_row.after_school_user_pct),
                    'avg_words_per_message': avg_words_per_message,
                    'avg_depth': None,
                    'total_relevant_questions': None,
                }
            )

        student_snapshots.sort(
            key=lambda entry: entry['avg_words_per_message'] if entry['avg_words_per_message'] is not None else -1,
            reverse=True,
        )
        student_snapshots = student_snapshots[:10]

    hourly_query = db.query(HourlyActivityMetrics).filter(
        HourlyActivityMetrics.school == school_value,
        HourlyActivityMetrics.grade == grade,
    )
    hourly_query = _apply_section_filter(hourly_query, HourlyActivityMetrics.section, section_value)
    bounds = _hourly_window_bounds()
    hourly_rows = (
        hourly_query
        .filter(
            HourlyActivityMetrics.window_start >= bounds['start'],
            HourlyActivityMetrics.window_start < bounds['end'],
        )
        .order_by(HourlyActivityMetrics.window_start.asc())
        .all()
    )
    hourly_activity = [
        {
            'window_start': row.window_start,
            'window_end': row.window_end,
            'user_message_count': row.user_message_count or 0,
            'ai_message_count': row.ai_message_count or 0,
            'active_users': row.active_users or 0,
            'after_school_user_count': row.after_school_user_count or 0,
        }
        for row in hourly_rows
    ]

    if student_ids:
        eval_start: Optional[date] = None
        eval_end: Optional[date] = None

        if summary_window is not None:
            eval_start, eval_end = summary_window

        if recent_days:
            first_day = recent_days[0]['day']
            last_day = recent_days[-1]['day']
            eval_start = min(eval_start or first_day, first_day)
            eval_end = max(eval_end or last_day, last_day)

        if eval_start is not None and eval_end is not None:
            evaluation_rollups = _collect_conversation_evaluations(
                db,
                student_ids,
                eval_start,
                eval_end,
            )

            class_eval = evaluation_rollups.get('class_summary')
            if class_summary_payload and class_eval:
                class_summary_payload['metrics_extra'] = class_eval
                class_summary_payload['avg_depth'] = class_eval.get('avg_depth')
                class_summary_payload['total_relevant_questions'] = class_eval.get('total_relevant_questions')
                if class_eval.get('top_topics'):
                    class_summary_payload['top_topics'] = class_eval.get('top_topics')

        class_daily_eval = evaluation_rollups.get('class_daily', {})
        for entry in recent_days:
            extra = class_daily_eval.get(entry['day'])
            if extra:
                entry['metrics_extra'] = extra
                if (extra.get('conversation_count') or 0) > 0:
                    entry['avg_depth'] = extra.get('avg_depth')
                    entry['total_relevant_questions'] = extra.get('total_relevant_questions')
                    if extra.get('top_topics'):
                        entry['top_topics'] = extra.get('top_topics')

        student_eval = evaluation_rollups.get('student_summary', {})
        for entry in student_snapshots:
            extra = student_eval.get(entry['student_id'])
            if extra:
                entry['metrics_extra'] = extra
                if (extra.get('conversation_count') or 0) > 0:
                    entry['avg_depth'] = extra.get('avg_depth')
                    entry['total_relevant_questions'] = extra.get('total_relevant_questions')
                    if extra.get('top_topics'):
                        entry['top_topics'] = extra.get('top_topics')

    return {
        'class_summary': class_summary_payload,
        'recent_days': recent_days,
        'student_snapshots': student_snapshots,
        'hourly_activity': hourly_activity,
    }


def _bulk_insert(
    db: Session,
    model,
    payload: Iterable[Dict[str, Any]],
    *,
    conflict_columns: Optional[Sequence[str]] = None,
) -> int:
    payload_list = [dict(item) for item in payload]
    if not payload_list:
        return 0
    if conflict_columns:
        stmt = pg_insert(model.__table__).values(payload_list)
        update_columns = {
            column: stmt.excluded[column]
            for column in payload_list[0].keys()
            if column != 'id'
        }
        if 'updated_at' in model.__table__.c:
            update_columns['updated_at'] = func.now()
        stmt = stmt.on_conflict_do_update(index_elements=conflict_columns, set_=update_columns)
        db.execute(stmt)
    else:
        db.bulk_insert_mappings(model, payload_list)
    return len(payload_list)


def _attach_cohort_fields(
    records: List[Dict[str, Any]],
    *,
    school: str,
    grade: int,
    section: Optional[str],
) -> List[Dict[str, Any]]:
    for record in records:
        record['school'] = school
        record['grade'] = grade
        record['section'] = section
        record.pop('metrics_extra', None)
    return records


def _hourly_window_bounds() -> Dict[str, datetime]:
    now_utc = datetime.now(timezone.utc)
    window_end = now_utc.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    window_start = window_end - timedelta(hours=24)
    return {'start': window_start, 'end': window_end}
