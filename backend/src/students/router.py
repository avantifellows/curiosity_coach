from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_
import httpx
import logging
import hashlib
import uuid
from datetime import datetime, timezone

from src.database import get_db, SessionLocal
from src.models import (
    Student,
    Conversation,
    Message,
    ClassAnalysis,
    StudentAnalysis,
    AnalysisJob,
)
from src.students.schemas import (
    StudentWithConversationResponse,
    ConversationWithMessagesResponse,
    ConversationMessageResponse,
    PaginatedConversationsResponse,
    ClassAnalysisResponse,
    AnalysisJobStatusResponse,
)
from src.config.settings import settings
from starlette.status import HTTP_202_ACCEPTED

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/students",
    tags=["students"],
)


def _normalize_school_value(value: str) -> str:
    school_value = value.strip()
    if not school_value:
        raise HTTPException(status_code=400, detail="School is required")
    return school_value


def _normalize_section_value(section: Optional[str]) -> Optional[str]:
    if section is None:
        return None
    normalized = section.strip().upper()
    return normalized or None


def _fetch_students_for_class(
    db: Session,
    school_value: str,
    grade: int,
    section_value: Optional[str],
) -> List[Student]:
    query = (
        db.query(Student)
        .filter(
            Student.school == school_value,
            Student.grade == grade,
        )
    )

    if section_value is not None:
        query = query.filter(Student.section == section_value)

    return query.order_by(Student.roll_number.asc()).all()


def _get_latest_conversations_for_users(
    db: Session,
    user_ids: List[int],
) -> Tuple[Dict[int, Conversation], List[int]]:
    if not user_ids:
        return {}, []

    latest_convo_subquery = (
        db.query(
            Conversation.user_id.label("user_id"),
            func.max(Conversation.updated_at).label("latest_updated_at")
        )
        .filter(Conversation.user_id.in_(user_ids))
        .group_by(Conversation.user_id)
        .subquery()
    )

    latest_conversations = (
        db.query(Conversation)
        .join(
            latest_convo_subquery,
            and_(
                Conversation.user_id == latest_convo_subquery.c.user_id,
                Conversation.updated_at == latest_convo_subquery.c.latest_updated_at
            )
        )
        .all()
    )

    conversations_map = {conversation.user_id: conversation for conversation in latest_conversations}
    conversation_ids = [conversation.id for conversation in latest_conversations]
    return conversations_map, conversation_ids


def _get_messages_by_conversation(
    db: Session,
    conversation_ids: List[int],
) -> Dict[int, List[Message]]:
    if not conversation_ids:
        return {}

    messages = (
        db.query(Message)
        .filter(Message.conversation_id.in_(conversation_ids))
        .order_by(Message.conversation_id.asc(), Message.timestamp.asc())
        .all()
    )

    messages_by_conversation: Dict[int, List[Message]] = {}
    for message in messages:
        messages_by_conversation.setdefault(message.conversation_id, []).append(message)
    return messages_by_conversation


def _build_class_conversation_hash(
    students: List[Student],
    conversations_map: Dict[int, Conversation],
) -> str:
    if not students:
        return "no-students"

    parts: List[str] = []
    for student in students:
        conversation = conversations_map.get(student.user_id)
        if conversation:
            parts.append(
                f"{student.user_id}:{conversation.id}:{conversation.updated_at.isoformat()}"
            )
        else:
            parts.append(f"{student.user_id}:none")

    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _collect_class_conversation_text(
    students: List[Student],
    conversations_map: Dict[int, Conversation],
    messages_by_conversation: Dict[int, List[Message]],
) -> str:
    text_parts: List[str] = []
    for student in students:
        conversation = conversations_map.get(student.user_id)
        if not conversation:
            continue
        text_parts.append(student.first_name)
        for message in messages_by_conversation.get(conversation.id, []):
            sender = "Student" if message.is_user else "AI"
            text_parts.append(f"  {sender}: {message.content}")
    return "\n".join(text_parts)


def _fetch_student_conversations(
    db: Session,
    student: Student,
) -> Tuple[List[Conversation], Dict[int, List[Message]]]:
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == student.user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    conversation_ids = [conversation.id for conversation in conversations]
    messages_by_conversation = _get_messages_by_conversation(db, conversation_ids)
    return conversations, messages_by_conversation


def _build_student_conversation_hash(conversations: List[Conversation]) -> str:
    if not conversations:
        return "no-conversations"

    parts = [f"{conversation.id}:{conversation.updated_at.isoformat()}" for conversation in conversations]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _collect_student_conversation_text(
    conversations: List[Conversation],
    messages_by_conversation: Dict[int, List[Message]],
) -> str:
    text_parts: List[str] = []
    for conversation in conversations:
        text_parts.append(f"Conversation: {conversation.title or 'Untitled'}")
        for message in messages_by_conversation.get(conversation.id, []):
            sender = "Student" if message.is_user else "AI"
            text_parts.append(f"  {sender}: {message.content}")
        text_parts.append("")
    return "\n".join(text_parts)


def _get_or_create_class_analysis(
    db: Session,
    school_value: str,
    grade: int,
    section_value: Optional[str],
) -> ClassAnalysis:
    existing = (
        db.query(ClassAnalysis)
        .filter(
            ClassAnalysis.school == school_value,
            ClassAnalysis.grade == grade,
            ClassAnalysis.section == section_value,
        )
        .first()
    )
    if existing:
        return existing

    new_row = ClassAnalysis(
        school=school_value,
        grade=grade,
        section=section_value,
        status="ready",
        analysis_text=None,
    )
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return new_row


def _get_or_create_student_analysis(
    db: Session,
    student: Student,
) -> StudentAnalysis:
    existing = (
        db.query(StudentAnalysis)
        .filter(StudentAnalysis.student_id == student.id)
        .first()
    )
    if existing:
        return existing

    new_row = StudentAnalysis(student_id=student.id, status="ready", analysis_text=None)
    db.add(new_row)
    db.commit()
    db.refresh(new_row)
    return new_row


def _find_active_job_for_analysis(db: Session, analysis_id: int, kind: str) -> Optional[AnalysisJob]:
    query = db.query(AnalysisJob).filter(AnalysisJob.analysis_kind == kind)
    if kind == "class":
        query = query.filter(AnalysisJob.class_analysis_id == analysis_id)
    else:
        query = query.filter(AnalysisJob.student_analysis_id == analysis_id)

    return query.filter(AnalysisJob.status.in_(["queued", "running"]))\
        .order_by(AnalysisJob.created_at.desc())\
        .first()


def _create_analysis_job(
    db: Session,
    *,
    kind: str,
    class_analysis: Optional[ClassAnalysis] = None,
    student_analysis: Optional[StudentAnalysis] = None,
) -> AnalysisJob:
    job = AnalysisJob(
        job_id=str(uuid.uuid4()),
        analysis_kind=kind,
        status="queued",
        class_analysis=class_analysis,
        student_analysis=student_analysis,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


async def _call_brain(endpoint: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(endpoint, json=payload)
        response.raise_for_status()
        return response.json()


def _resolve_brain_endpoint() -> str:
    return (
        settings.LOCAL_BRAIN_ENDPOINT_URL
        if settings.APP_ENV == "development" and settings.LOCAL_BRAIN_ENDPOINT_URL
        else settings.BRAIN_ENDPOINT_URL
    )


def _mark_job_failure(
    db: Session,
    job: AnalysisJob,
    analysis,
    message: str,
) -> None:
    job.status = "failed"
    job.error_message = message
    job.updated_at = datetime.now(timezone.utc)
    if analysis is not None:
        analysis.status = "failed"
        analysis.updated_at = datetime.now(timezone.utc)
    db.commit()

@router.get("", response_model=List[StudentWithConversationResponse])
def list_students(
    school: str = Query(..., description="School name to filter students"),
    grade: int = Query(..., ge=1, le=12, description="Grade to filter students"),
    section: Optional[str] = Query(None, description="Optional section (e.g., A, B)"),
    db: Session = Depends(get_db),
):
    """
    Return all students that match the provided school, grade, and optional section.
    """
    school_value = _normalize_school_value(school)
    section_value = _normalize_section_value(section)

    students = _fetch_students_for_class(db, school_value, grade, section_value)

    user_ids = [student.user_id for student in students]
    conversations_map, conversation_ids = _get_latest_conversations_for_users(db, user_ids)
    messages_by_conversation_raw = _get_messages_by_conversation(db, conversation_ids)

    response: List[StudentWithConversationResponse] = []
    for student in students:
        latest_conversation = conversations_map.get(student.user_id)
        latest_conversation_payload: Optional[ConversationWithMessagesResponse] = None

        if latest_conversation:
            message_payloads = [
                ConversationMessageResponse(
                    id=message.id,
                    content=message.content,
                    is_user=message.is_user,
                    timestamp=message.timestamp,
                )
                for message in messages_by_conversation_raw.get(latest_conversation.id, [])
            ]
            latest_conversation_payload = ConversationWithMessagesResponse(
                id=latest_conversation.id,
                title=latest_conversation.title,
                updated_at=latest_conversation.updated_at,
                messages=message_payloads,
            )

        response.append(
            StudentWithConversationResponse(
                student=student, latest_conversation=latest_conversation_payload
            )
        )

    return response


@router.get("/{student_id}/conversations", response_model=PaginatedConversationsResponse)
def list_student_conversations(
    student_id: int,
    limit: int = Query(3, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    base_query = (
        db.query(Conversation)
        .filter(Conversation.user_id == student.user_id)
        .order_by(Conversation.updated_at.desc())
    )

    conversations = base_query.offset(offset).limit(limit + 1).all()
    has_more = len(conversations) > limit
    conversations = conversations[:limit]

    conversation_ids = [conversation.id for conversation in conversations]
    messages_by_conversation: Dict[int, List[ConversationMessageResponse]] = {}

    if conversation_ids:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id.in_(conversation_ids))
            .order_by(Message.conversation_id.asc(), Message.timestamp.asc())
            .all()
        )

        for message in messages:
            messages_by_conversation.setdefault(message.conversation_id, []).append(
                ConversationMessageResponse(
                    id=message.id,
                    content=message.content,
                    is_user=message.is_user,
                    timestamp=message.timestamp,
                )
            )

    response_conversations = [
        ConversationWithMessagesResponse(
            id=conversation.id,
            title=conversation.title,
            updated_at=conversation.updated_at,
            messages=messages_by_conversation.get(conversation.id, []),
        )
        for conversation in conversations
    ]

    return PaginatedConversationsResponse(
        conversations=response_conversations,
        next_offset=offset + limit if has_more else None,
    )


@router.get("/{student_id}/conversations/all", response_model=List[ConversationWithMessagesResponse])
def list_all_student_conversations(
    student_id: int,
    db: Session = Depends(get_db),
):
    """
    Return all conversations for a student with all messages, in a flat structure.
    No pagination - returns everything at once.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get all conversations for this student, ordered by most recent first
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == student.user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    conversation_ids = [conversation.id for conversation in conversations]
    messages_by_conversation: Dict[int, List[ConversationMessageResponse]] = {}

    if conversation_ids:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id.in_(conversation_ids))
            .order_by(Message.conversation_id.asc(), Message.timestamp.asc())
            .all()
        )

        for message in messages:
            messages_by_conversation.setdefault(message.conversation_id, []).append(
                ConversationMessageResponse(
                    id=message.id,
                    content=message.content,
                    is_user=message.is_user,
                    timestamp=message.timestamp,
                )
            )

    response_conversations = [
        ConversationWithMessagesResponse(
            id=conversation.id,
            title=conversation.title,
            updated_at=conversation.updated_at,
            messages=messages_by_conversation.get(conversation.id, []),
        )
        for conversation in conversations
    ]

    return response_conversations


@router.post("/class-analysis", response_model=ClassAnalysisResponse)
async def analyze_class_conversations(
    background_tasks: BackgroundTasks,
    school: str = Query(..., description="School name to filter students"),
    grade: int = Query(..., ge=1, le=12, description="Grade to filter students"),
    section: Optional[str] = Query(None, description="Optional section (e.g., A, B)"),
    force_refresh: bool = Query(False, description="Force recomputing the analysis even if cached"),
    db: Session = Depends(get_db),
):
    """
    Returns cached analysis immediately if available, queues background job for refresh.
    This endpoint returns quickly to avoid API Gateway timeout.
    """
    school_value = _normalize_school_value(school)
    section_value = _normalize_section_value(section)

    # Quick check: get or create analysis record (lightweight)
    class_analysis = _get_or_create_class_analysis(db, school_value, grade, section_value)
    
    # Check for active job first
    active_job = _find_active_job_for_analysis(db, class_analysis.id, "class")
    
    # If there's already a job running, return current state immediately
    if active_job and not force_refresh:
        return JSONResponse(
            status_code=HTTP_202_ACCEPTED,
            content=ClassAnalysisResponse(
                analysis=class_analysis.analysis_text,
                status=class_analysis.status,
                job_id=active_job.job_id,
                computed_at=class_analysis.computed_at,
            ).model_dump(mode="json"),
        )
    
    # If we have cached analysis, check staleness
    if class_analysis.analysis_text and class_analysis.status == "ready":
        # Compute current hash to detect changes
        students = _fetch_students_for_class(db, school_value, grade, section_value)
        user_ids = [s.user_id for s in students]
        conversations_map, _ = _get_latest_conversations_for_users(db, user_ids)
        current_hash = _build_class_conversation_hash(students, conversations_map)
        
        is_stale = (
            not class_analysis.last_message_hash 
            or current_hash != class_analysis.last_message_hash
        )
        
        if not is_stale and not force_refresh:
            # Nothing changed - return cached immediately
            return ClassAnalysisResponse(
                analysis=class_analysis.analysis_text,
                status="ready",
                job_id=None,
                computed_at=class_analysis.computed_at,
            )
        
        if not is_stale and force_refresh:
            # User clicked refresh but nothing changed - return cached
            logger.info("Class analysis hash unchanged, returning cached result")
            return ClassAnalysisResponse(
                analysis=class_analysis.analysis_text,
                status="ready",
                job_id=None,
                computed_at=class_analysis.computed_at,
            )
        
        # Data changed - queue refresh, but return cached for now
        logger.info("Class analysis is stale, queueing refresh")

    # No cached analysis, or stale - queue a job
    job = _create_analysis_job(db, kind="class", class_analysis=class_analysis)
    class_analysis.status = "queued"
    class_analysis.updated_at = datetime.now(timezone.utc)
    db.add(class_analysis)
    db.commit()
    
    # Queue background task - all heavy work happens here
    background_tasks.add_task(
        _process_class_analysis_job,
        job.job_id,
        school_value,
        grade,
        section_value,
    )

    return JSONResponse(
        status_code=HTTP_202_ACCEPTED,
        content=ClassAnalysisResponse(
            analysis=class_analysis.analysis_text,
            status="queued",
            job_id=job.job_id,
            computed_at=class_analysis.computed_at,
        ).model_dump(mode="json"),
    )


@router.post("/{student_id}/analysis", response_model=ClassAnalysisResponse)
async def analyze_student_conversations(
    background_tasks: BackgroundTasks,
    student_id: int,
    force_refresh: bool = Query(False, description="Force recomputing the analysis even if cached"),
    db: Session = Depends(get_db),
):
    """
    Returns cached analysis immediately if available, queues background job for refresh.
    This endpoint returns quickly to avoid API Gateway timeout.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Quick check: get or create analysis record (lightweight)
    student_analysis = _get_or_create_student_analysis(db, student)
    
    # Check for active job first
    active_job = _find_active_job_for_analysis(db, student_analysis.id, "student")
    
    # If there's already a job running, return current state immediately
    if active_job and not force_refresh:
        return JSONResponse(
            status_code=HTTP_202_ACCEPTED,
            content=ClassAnalysisResponse(
                analysis=student_analysis.analysis_text,
                status=student_analysis.status,
                job_id=active_job.job_id,
                computed_at=student_analysis.computed_at,
            ).model_dump(mode="json"),
        )
    
    # If we have cached analysis, check staleness
    if student_analysis.analysis_text and student_analysis.status == "ready":
        # Lightweight query for hash - only need conversation metadata, not messages
        conversations = (
            db.query(Conversation)
            .filter(Conversation.user_id == student.user_id)
            .order_by(Conversation.updated_at.desc())
            .all()
        )
        current_hash = _build_student_conversation_hash(conversations)
        
        is_stale = (
            not student_analysis.last_message_hash 
            or current_hash != student_analysis.last_message_hash
        )
        
        if not is_stale and not force_refresh:
            # Nothing changed - return cached immediately
            return ClassAnalysisResponse(
                analysis=student_analysis.analysis_text,
                status="ready",
                job_id=None,
                computed_at=student_analysis.computed_at,
            )
        
        if not is_stale and force_refresh:
            # User clicked refresh but nothing changed - return cached
            logger.info("Student analysis hash unchanged, returning cached result")
            return ClassAnalysisResponse(
                analysis=student_analysis.analysis_text,
                status="ready",
                job_id=None,
                computed_at=student_analysis.computed_at,
            )
        
        # Data changed - queue refresh, but return cached for now
        logger.info("Student analysis is stale, queueing refresh")

    # No cached analysis, or stale - queue a job
    job = _create_analysis_job(db, kind="student", student_analysis=student_analysis)
    student_analysis.status = "queued"
    student_analysis.updated_at = datetime.now(timezone.utc)
    db.add(student_analysis)
    db.commit()
    
    # Queue background task - all heavy work happens here
    background_tasks.add_task(
        _process_student_analysis_job,
        job.job_id,
        student.id,
    )

    return JSONResponse(
        status_code=HTTP_202_ACCEPTED,
        content=ClassAnalysisResponse(
            analysis=student_analysis.analysis_text,
            status="queued",
            job_id=job.job_id,
            computed_at=student_analysis.computed_at,
        ).model_dump(mode="json"),
    )


async def _process_class_analysis_job(
    job_id: str,
    school_value: str,
    grade: int,
    section_value: Optional[str],
) -> None:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
        if not job or not job.class_analysis_id:
            logger.warning("Class analysis job %s missing target", job_id)
            return

        class_analysis = job.class_analysis
        job.status = "running"
        job.updated_at = datetime.now(timezone.utc)
        class_analysis.status = "running"
        class_analysis.updated_at = datetime.now(timezone.utc)
        db.commit()

        students = _fetch_students_for_class(db, school_value, grade, section_value)
        user_ids = [student.user_id for student in students]
        conversations_map, conversation_ids = _get_latest_conversations_for_users(db, user_ids)

        if not conversation_ids:
            _mark_job_failure(db, job, class_analysis, "No conversations available for analysis")
            return

        messages_by_conversation = _get_messages_by_conversation(db, conversation_ids)
        transcript = _collect_class_conversation_text(students, conversations_map, messages_by_conversation)

        if not transcript.strip():
            _mark_job_failure(db, job, class_analysis, "Conversation transcript was empty")
            return

        brain_endpoint = _resolve_brain_endpoint()
        if not brain_endpoint:
            _mark_job_failure(db, job, class_analysis, "Brain endpoint is not configured")
            return

        try:
            response_json = await _call_brain(
                f"{brain_endpoint.rstrip('/')}/class-analysis",
                {
                    "all_conversations": transcript,
                    "call_type": "class_analysis",
                },
            )
        except httpx.TimeoutException:
            logger.error("Timeout while generating class analysis for %s/%s/%s", school_value, grade, section_value)
            _mark_job_failure(db, job, class_analysis, "Brain analysis timed out")
            return
        except httpx.HTTPStatusError as exc:
            logger.error("Brain returned %s for class analysis: %s", exc.response.status_code, exc.response.text)
            _mark_job_failure(db, job, class_analysis, f"Brain analysis failed: {exc.response.text}")
            return
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Unexpected error while processing class analysis job %s", job_id)
            _mark_job_failure(db, job, class_analysis, str(exc))
            return

        analysis_text = response_json.get("analysis", "")
        class_analysis.analysis_text = analysis_text
        class_analysis.status = "ready"
        class_analysis.computed_at = datetime.now(timezone.utc)
        class_analysis.last_message_hash = _build_class_conversation_hash(students, conversations_map)
        class_analysis.updated_at = datetime.now(timezone.utc)

        job.status = "completed"
        job.error_message = None
        job.completed_at = datetime.now(timezone.utc)
        job.updated_at = job.completed_at
        db.commit()
    finally:
        db.close()


async def _process_student_analysis_job(
    job_id: str,
    student_id: int,
) -> None:
    db = SessionLocal()
    try:
        job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
        if not job or not job.student_analysis_id:
            logger.warning("Student analysis job %s missing target", job_id)
            return

        student_analysis = job.student_analysis
        job.status = "running"
        job.updated_at = datetime.now(timezone.utc)
        student_analysis.status = "running"
        student_analysis.updated_at = datetime.now(timezone.utc)
        db.commit()

        student = db.query(Student).filter(Student.id == student_id).first()
        if not student:
            _mark_job_failure(db, job, student_analysis, "Student not found during analysis")
            return

        conversations, messages_by_conversation = _fetch_student_conversations(db, student)
        if not conversations:
            _mark_job_failure(db, job, student_analysis, "No conversations available for analysis")
            return

        transcript = _collect_student_conversation_text(conversations, messages_by_conversation)
        if not transcript.strip():
            _mark_job_failure(db, job, student_analysis, "Conversation transcript was empty")
            return

        brain_endpoint = _resolve_brain_endpoint()
        if not brain_endpoint:
            _mark_job_failure(db, job, student_analysis, "Brain endpoint is not configured")
            return

        try:
            response_json = await _call_brain(
                f"{brain_endpoint.rstrip('/')}/student-analysis",
                {
                    "all_conversations": transcript,
                    "call_type": "student_analysis",
                },
            )
        except httpx.TimeoutException:
            logger.error("Timeout while generating student analysis for student_id=%s", student_id)
            _mark_job_failure(db, job, student_analysis, "Brain analysis timed out")
            return
        except httpx.HTTPStatusError as exc:
            logger.error("Brain returned %s for student analysis: %s", exc.response.status_code, exc.response.text)
            _mark_job_failure(db, job, student_analysis, f"Brain analysis failed: {exc.response.text}")
            return
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Unexpected error while processing student analysis job %s", job_id)
            _mark_job_failure(db, job, student_analysis, str(exc))
            return

        analysis_text = response_json.get("analysis", "")
        student_analysis.analysis_text = analysis_text
        student_analysis.status = "ready"
        student_analysis.computed_at = datetime.now(timezone.utc)
        student_analysis.last_message_hash = _build_student_conversation_hash(conversations)
        student_analysis.updated_at = datetime.now(timezone.utc)

        job.status = "completed"
        job.error_message = None
        job.completed_at = datetime.now(timezone.utc)
        job.updated_at = job.completed_at
        db.commit()
    finally:
        db.close()


@router.get("/analysis-jobs/{job_id}", response_model=AnalysisJobStatusResponse)
def get_analysis_job_status(
    job_id: str,
    db: Session = Depends(get_db),
):
    job = db.query(AnalysisJob).filter(AnalysisJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.analysis_kind == "class" and job.class_analysis:
        analysis = job.class_analysis
    elif job.analysis_kind == "student" and job.student_analysis:
        analysis = job.student_analysis
    else:
        analysis = None

    payload = AnalysisJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        analysis=getattr(analysis, "analysis_text", None),
        computed_at=getattr(analysis, "computed_at", None),
        error_message=job.error_message,
        analysis_status=getattr(analysis, "status", None) if analysis else None,
    )

    return JSONResponse(content=payload.model_dump(mode="json"))
