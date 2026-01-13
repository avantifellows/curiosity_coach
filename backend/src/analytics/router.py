from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import exists
from sqlalchemy.orm import Session

from src.analytics.metrics_service import (
    MetricsRefreshSummary,
    get_dashboard_metrics,
    get_student_daily_series,
    refresh_metrics,
)
from src.database import get_db
from src.models import (
    AnalysisJob,
    Conversation,
    ConversationEvaluation,
    Message,
    Student,
    PromptVersion,
)
from src.prompts.service import PromptService
from src.queue.service import QueueService, get_queue_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)


class MetricsRefreshRequest(BaseModel):
    school: str = Field(..., description="School identifier")
    grade: int = Field(..., ge=1, description="Grade level")
    section: Optional[str] = Field(None, description="Optional section identifier (e.g., 'B')")
    include_hourly: bool = Field(True, description="Compute hourly activity metrics for the last 24 hours")

    def normalized_section(self) -> Optional[str]:
        return self.section.strip().upper() if self.section else None

    class Config:
        json_schema_extra = {
            "example": {
                "school": "Ekya School JP Nagar",
                "grade": 8,
                "section": "B",
                "include_hourly": True,
            }
        }


class MetricsRefreshResponse(BaseModel):
    class_daily_rows: int
    student_daily_rows: int
    class_summary_rows: int
    student_summary_rows: int
    hourly_rows: int
    deleted_rows: dict[str, int]


class DashboardTopic(BaseModel):
    term: str
    total_weight: Optional[float] = None
    conversation_count: Optional[int] = None


class DepthLevelStat(BaseModel):
    level: int
    count: int


class DashboardClassSummary(BaseModel):
    cohort_start: date
    cohort_end: date
    total_students: Optional[int]
    total_conversations: Optional[int]
    total_user_messages: Optional[int]
    total_ai_messages: Optional[int]
    total_user_words: Optional[int]
    total_ai_words: Optional[int]
    total_minutes: Optional[float]
    avg_minutes_per_conversation: Optional[float]
    avg_user_msgs_per_conversation: Optional[float]
    avg_ai_msgs_per_conversation: Optional[float]
    avg_user_words_per_conversation: Optional[float]
    avg_ai_words_per_conversation: Optional[float]
    avg_user_words_per_message: Optional[float]
    avg_ai_words_per_message: Optional[float]
    user_messages_after_school: Optional[int]
    total_messages_after_school: Optional[int]
    after_school_conversations: Optional[int]
    after_school_user_pct: Optional[float]
    total_relevant_questions: Optional[float] = None
    avg_attention_span: Optional[float] = None
    depth_levels: Optional[List[DepthLevelStat]] = None
    top_topics: Optional[List[DashboardTopic]] = None
    metrics_extra: Optional[Dict[str, Any]] = None


class DashboardDailyStat(BaseModel):
    day: date
    total_minutes: Optional[float]
    total_user_messages: Optional[int]
    total_ai_messages: Optional[int]
    active_students: Optional[int]
    user_messages_after_school: Optional[int]
    after_school_conversations: Optional[int]
    total_relevant_questions: Optional[float] = None
    avg_attention_span: Optional[float] = None
    depth_levels: Optional[List[DepthLevelStat]] = None
    top_topics: Optional[List[DashboardTopic]] = None
    metrics_extra: Optional[Dict[str, Any]] = None


class DashboardStudentSnapshot(BaseModel):
    student_id: int
    student_name: Optional[str]
    total_minutes: Optional[float]
    total_user_messages: Optional[int]
    total_user_words: Optional[int]
    total_ai_messages: Optional[int]
    after_school_user_pct: Optional[float]
    avg_words_per_message: Optional[float] = None
    total_relevant_questions: Optional[float] = None
    avg_attention_span: Optional[float] = None
    depth_levels: Optional[List[DepthLevelStat]] = None
    top_topics: Optional[List[DashboardTopic]] = None
    metrics_extra: Optional[Dict[str, Any]] = None


class DashboardHourlyBucket(BaseModel):
    window_start: datetime
    window_end: datetime
    user_message_count: int
    ai_message_count: int
    active_users: int
    after_school_user_count: int


class MetricsDashboardResponse(BaseModel):
    class_summary: Optional[DashboardClassSummary]
    recent_days: List[DashboardDailyStat]
    student_snapshots: List[DashboardStudentSnapshot]
    hourly_activity: List[DashboardHourlyBucket]


class StudentDailyPoint(BaseModel):
    day: date
    user_messages: Optional[int]
    ai_messages: Optional[int]
    user_words: Optional[int]
    ai_words: Optional[int]
    minutes_spent: Optional[float]
    user_messages_after_school: Optional[int]
    total_messages_after_school: Optional[int]
    total_relevant_questions: Optional[float] = None
    metrics_extra: Optional[Dict[str, Any]] = None
    depth_levels: Optional[List[DepthLevelStat]] = None


class StudentDailySeries(BaseModel):
    student_id: int
    student_name: Optional[str]
    records: List[StudentDailyPoint]


class StudentDailyMetricsResponse(BaseModel):
    students: List[StudentDailySeries]


class EvaluationRunRequest(BaseModel):
    school: str = Field(..., description="School identifier")
    grade: int = Field(..., ge=1, description="Grade level")
    section: Optional[str] = Field(None, description="Optional section identifier")
    scope: Literal["all", "missing"] = Field(
        "missing",
        description="Run on all conversations or only those missing/stale evaluation metrics",
    )
    conversation_ids: Optional[List[int]] = Field(
        None,
        description="Optional list of specific conversation IDs to evaluate",
    )

    def normalized_section(self) -> Optional[str]:
        return self.section.strip().upper() if self.section else None

    def normalized_school(self) -> str:
        return self.school.strip()


class EvaluationRunResponse(BaseModel):
    total_candidates: int
    queued: int
    skipped: int
    already_running: int
    job_ids: List[str]
    prompt_version_id: Optional[int]


def _get_conversation_evaluation_prompt_version(db: Session) -> Optional[PromptVersion]:
    """Fetch the production version of the conversation evaluation prompt."""
    prompt_service = PromptService()
    return prompt_service.get_production_prompt_version(db, "conversation_evaluation_analysis")


def _build_conversation_evaluation_hash(
    conversation: Conversation,
    prompt_version: Optional[PromptVersion],
) -> str:
    parts: List[str] = []
    if prompt_version:
        version_stamp = (
            getattr(prompt_version, "updated_at", None)
            or getattr(prompt_version, "created_at", None)
            or datetime.now(timezone.utc)
        )
        parts.append(f"prompt:{prompt_version.id}:{version_stamp.isoformat()}")
    else:
        parts.append("prompt:none")

    updated_at = conversation.updated_at or conversation.created_at
    if updated_at:
        parts.append(f"conversation:{conversation.id}:{updated_at.isoformat()}")
    else:
        parts.append(f"conversation:{conversation.id}:unknown")

    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _get_or_create_conversation_evaluation(
    db: Session,
    conversation_id: int,
) -> ConversationEvaluation:
    evaluation = (
        db.query(ConversationEvaluation)
        .filter(ConversationEvaluation.conversation_id == conversation_id)
        .first()
    )
    if evaluation:
        return evaluation

    evaluation = ConversationEvaluation(conversation_id=conversation_id, status="ready")
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


def _find_active_job_for_evaluation(
    db: Session,
    evaluation_id: int,
) -> Optional[AnalysisJob]:
    return (
        db.query(AnalysisJob)
        .filter(AnalysisJob.analysis_kind == "conversation")
        .filter(AnalysisJob.conversation_evaluation_id == evaluation_id)
        .filter(AnalysisJob.status.in_(["queued", "running"]))
        .order_by(AnalysisJob.created_at.desc())
        .first()
    )


def _create_conversation_evaluation_job(
    db: Session,
    evaluation: ConversationEvaluation,
) -> AnalysisJob:
    job = AnalysisJob(
        job_id=str(uuid.uuid4()),
        analysis_kind="conversation",
        status="queued",
        conversation_evaluation=evaluation,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/refresh", response_model=MetricsRefreshResponse)
def refresh_metrics_endpoint(
    payload: MetricsRefreshRequest,
    start_date: Optional[date] = Query(
        None,
        description="Optional start date (inclusive) to limit recomputation",
    ),
    end_date: Optional[date] = Query(
        None,
        description="Optional end date (inclusive) to limit recomputation",
    ),
    db: Session = Depends(get_db),
) -> MetricsRefreshResponse:
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be greater than or equal to start_date")

    summary: MetricsRefreshSummary = refresh_metrics(
        db,
        school=payload.school,
        grade=payload.grade,
        section=payload.normalized_section(),
        start_date=start_date,
        end_date=end_date,
        include_hourly=payload.include_hourly,
    )

    return MetricsRefreshResponse(
        class_daily_rows=summary.class_daily_rows,
        student_daily_rows=summary.student_daily_rows,
        class_summary_rows=summary.class_summary_rows,
        student_summary_rows=summary.student_summary_rows,
        hourly_rows=summary.hourly_rows,
        deleted_rows=summary.deleted_rows or {},
    )


@router.post("/evaluation-analysis/run", response_model=EvaluationRunResponse)
async def run_conversation_evaluation_endpoint(
    payload: EvaluationRunRequest,
    db: Session = Depends(get_db),
    queue_service: QueueService = Depends(get_queue_service),
) -> EvaluationRunResponse:
    if payload.conversation_ids is not None and len(payload.conversation_ids) == 0:
        raise HTTPException(status_code=400, detail="conversation_ids cannot be empty")

    prompt_version = _get_conversation_evaluation_prompt_version(db)
    if not prompt_version:
        raise HTTPException(status_code=400, detail="Conversation evaluation prompt not configured")

    school_value = payload.normalized_school()
    section_value = payload.normalized_section()

    conversation_query = (
        db.query(Conversation)
        .join(Student, Student.user_id == Conversation.user_id)
        .filter(Student.school == school_value)
        .filter(Student.grade == payload.grade)
        .filter(Student.roll_number < 100)
    )

    if section_value:
        conversation_query = conversation_query.filter(Student.section == section_value)

    if payload.conversation_ids:
        conversation_query = conversation_query.filter(Conversation.id.in_(payload.conversation_ids))

    conversation_query = conversation_query.filter(
        exists().where(Message.conversation_id == Conversation.id)
    )

    conversations = conversation_query.all()
    total_candidates = len(conversations)

    if total_candidates == 0:
        return EvaluationRunResponse(
            total_candidates=0,
            queued=0,
            skipped=0,
            already_running=0,
            job_ids=[],
            prompt_version_id=prompt_version.id if prompt_version else None,
        )

    queued_count = 0
    skipped_count = 0
    already_running_count = 0
    job_ids: List[str] = []

    for conversation in conversations:
        evaluation = _get_or_create_conversation_evaluation(db, conversation.id)

        active_job = _find_active_job_for_evaluation(db, evaluation.id)
        if active_job:
            already_running_count += 1
            continue

        current_hash = _build_conversation_evaluation_hash(conversation, prompt_version)

        if (
            payload.scope == "missing"
            and evaluation.status == "ready"
            and evaluation.last_message_hash == current_hash
        ):
            skipped_count += 1
            continue

        now = datetime.now(timezone.utc)
        evaluation.status = "queued"
        evaluation.updated_at = now

        job = _create_conversation_evaluation_job(db, evaluation)

        task_payload: Dict[str, Any] = {
            "task_type": "EVALUATION_ANALYSIS",
            "job_id": job.job_id,
            "conversation_id": conversation.id,
            "last_message_hash": current_hash,
            "prompt_version_id": prompt_version.id if prompt_version else None,
        }

        try:
            await queue_service.send_batch_task(task_payload)
        except Exception as exc:  # pragma: no cover - network/queue failure paths
            logger.error("Failed to queue evaluation job %s: %s", job.job_id, exc)
            job.status = "failed"
            job.error_message = f"Failed to queue task: {exc}"
            evaluation.status = "failed"
            evaluation.updated_at = datetime.now(timezone.utc)
            db.commit()
            raise HTTPException(status_code=500, detail="Failed to queue evaluation task") from exc

        queued_count += 1
        job_ids.append(job.job_id)

    return EvaluationRunResponse(
        total_candidates=total_candidates,
        queued=queued_count,
        skipped=skipped_count,
        already_running=already_running_count,
        job_ids=job_ids,
        prompt_version_id=prompt_version.id if prompt_version else None,
    )


@router.get("/dashboard", response_model=MetricsDashboardResponse)
def get_dashboard_endpoint(
    school: str = Query(..., description="School identifier"),
    grade: int = Query(..., ge=1, description="Grade level"),
    section: Optional[str] = Query(None, description="Optional section identifier"),
    db: Session = Depends(get_db),
) -> MetricsDashboardResponse:
    summary = get_dashboard_metrics(
        db,
        school=school,
        grade=grade,
        section=section.strip().upper() if section else None,
    )
    return MetricsDashboardResponse(**summary)


@router.get("/student-daily", response_model=StudentDailyMetricsResponse)
def get_student_daily_endpoint(
    school: str = Query(..., description="School identifier"),
    grade: int = Query(..., ge=1, description="Grade level"),
    section: Optional[str] = Query(None, description="Optional section identifier"),
    student_ids: List[int] = Query(..., min_length=1, description="Student IDs to retrieve daily metrics for"),
    start_date: Optional[date] = Query(None, description="Optional start date (inclusive)"),
    end_date: Optional[date] = Query(None, description="Optional end date (inclusive)"),
    db: Session = Depends(get_db),
) -> StudentDailyMetricsResponse:
    if start_date and end_date and end_date < start_date:
        raise HTTPException(status_code=400, detail="end_date must be greater than or equal to start_date")

    normalized_section = section.strip().upper() if section else None
    series = get_student_daily_series(
        db,
        school=school,
        grade=grade,
        section=normalized_section,
        student_ids=student_ids,
        start_date=start_date,
        end_date=end_date,
    )

    if not series:
        raise HTTPException(status_code=404, detail="No matching students or metrics found")

    return StudentDailyMetricsResponse(students=series)
