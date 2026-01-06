from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.analytics.metrics_service import (
    MetricsRefreshSummary,
    get_dashboard_metrics,
    get_student_daily_series,
    refresh_metrics,
)
from src.database import get_db

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class MetricsRefreshRequest(BaseModel):
    school: str = Field(..., description="School identifier")
    grade: int = Field(..., ge=1, description="Grade level")
    section: Optional[str] = Field(None, description="Optional section identifier (e.g., 'B')")
    start_date: Optional[date] = Field(None, description="Restrict computation from this date (inclusive)")
    end_date: Optional[date] = Field(None, description="Restrict computation to this date (inclusive)")
    include_hourly: bool = Field(True, description="Compute hourly activity metrics for the last 24 hours")

    def normalized_section(self) -> Optional[str]:
        return self.section.strip().upper() if self.section else None


class MetricsRefreshResponse(BaseModel):
    class_daily_rows: int
    student_daily_rows: int
    class_summary_rows: int
    student_summary_rows: int
    hourly_rows: int
    deleted_rows: dict[str, int]


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


class DashboardDailyStat(BaseModel):
    day: date
    total_minutes: Optional[float]
    total_user_messages: Optional[int]
    total_ai_messages: Optional[int]
    active_students: Optional[int]
    user_messages_after_school: Optional[int]
    after_school_conversations: Optional[int]


class DashboardStudentSnapshot(BaseModel):
    student_id: int
    student_name: Optional[str]
    total_minutes: Optional[float]
    total_user_messages: Optional[int]
    total_user_words: Optional[int]
    total_ai_messages: Optional[int]
    after_school_user_pct: Optional[float]


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


class StudentDailySeries(BaseModel):
    student_id: int
    student_name: Optional[str]
    records: List[StudentDailyPoint]


class StudentDailyMetricsResponse(BaseModel):
    students: List[StudentDailySeries]


@router.post("/refresh", response_model=MetricsRefreshResponse)
def refresh_metrics_endpoint(
    payload: MetricsRefreshRequest,
    db: Session = Depends(get_db),
) -> MetricsRefreshResponse:
    if payload.start_date and payload.end_date and payload.end_date < payload.start_date:
        raise HTTPException(status_code=400, detail="end_date must be greater than or equal to start_date")

    summary: MetricsRefreshSummary = refresh_metrics(
        db,
        school=payload.school,
        grade=payload.grade,
        section=payload.normalized_section(),
        start_date=payload.start_date,
        end_date=payload.end_date,
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
