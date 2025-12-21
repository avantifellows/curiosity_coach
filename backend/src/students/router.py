from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_
import logging
import hashlib
import uuid
from datetime import datetime, timezone

from src.database import get_db
from src.models import (
    Student,
    Conversation,
    Message,
    ClassAnalysis,
    StudentAnalysis,
    AnalysisJob,
    PromptVersion,
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
from src.prompts.service import PromptService
from src.queue.service import get_queue_service, QueueService
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


def _get_class_analysis_prompt_version(db: Session) -> Optional[PromptVersion]:
    """Fetch the production version of the class analysis prompt."""
    prompt_service = PromptService()
    return prompt_service.get_production_prompt_version(db, "overall_class_latest_topic_analysis")


def _get_student_analysis_prompt_version(db: Session) -> Optional[PromptVersion]:
    """Fetch the production version of the student analysis prompt."""
    prompt_service = PromptService()
    return prompt_service.get_production_prompt_version(db, "analyse_student_all_conversation")


def _build_class_conversation_hash(
    students: List[Student],
    conversations_map: Dict[int, Conversation],
    prompt_version: Optional[PromptVersion] = None,
) -> str:
    if not students:
        return "no-students"

    parts: List[str] = []
    
    # Include prompt version in hash - when prompt changes, hash changes
    if prompt_version:
        parts.append(f"prompt:{prompt_version.id}:{prompt_version.created_at.isoformat()}")
    else:
        parts.append("prompt:none")
    
    for student in students:
        conversation = conversations_map.get(student.user_id)
        if conversation:
            parts.append(
                f"{student.user_id}:{conversation.id}:{conversation.updated_at.isoformat()}"
            )
        else:
            parts.append(f"{student.user_id}:none")

    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _build_student_conversation_hash(
    conversations: List[Conversation],
    prompt_version: Optional[PromptVersion] = None,
) -> str:
    if not conversations:
        return "no-conversations"

    parts: List[str] = []
    
    # Include prompt version in hash - when prompt changes, hash changes
    if prompt_version:
        parts.append(f"prompt:{prompt_version.id}:{prompt_version.created_at.isoformat()}")
    else:
        parts.append("prompt:none")
    
    for conversation in conversations:
        parts.append(f"{conversation.id}:{conversation.updated_at.isoformat()}")
    
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


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
                    curiosity_score=message.curiosity_score,
                )
                for message in messages_by_conversation_raw.get(latest_conversation.id, [])
            ]
            latest_conversation_payload = ConversationWithMessagesResponse(
                id=latest_conversation.id,
                title=latest_conversation.title,
                created_at=latest_conversation.created_at,
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
                    curiosity_score=message.curiosity_score,
                )
            )

    response_conversations = [
        ConversationWithMessagesResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
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
                    curiosity_score=message.curiosity_score,
                )
            )

    response_conversations = [
        ConversationWithMessagesResponse(
            id=conversation.id,
            title=conversation.title,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            messages=messages_by_conversation.get(conversation.id, []),
        )
        for conversation in conversations
    ]

    return response_conversations


@router.post("/class-analysis", response_model=ClassAnalysisResponse)
async def analyze_class_conversations(
    school: str = Query(..., description="School name to filter students"),
    grade: int = Query(..., ge=1, le=12, description="Grade to filter students"),
    section: Optional[str] = Query(None, description="Optional section (e.g., A, B)"),
    force_refresh: bool = Query(False, description="Force recomputing the analysis even if cached"),
    db: Session = Depends(get_db),
    queue_service: QueueService = Depends(get_queue_service),
):
    """
    Returns cached analysis immediately if available, queues SQS job for refresh.
    This endpoint returns quickly to avoid API Gateway timeout.
    """
    school_value = _normalize_school_value(school)
    section_value = _normalize_section_value(section)

    # Quick check: get or create analysis record (lightweight)
    class_analysis = _get_or_create_class_analysis(db, school_value, grade, section_value)
    
    # Check for active job first - even with force_refresh, don't create duplicate jobs
    active_job = _find_active_job_for_analysis(db, class_analysis.id, "class")
    
    # If there's already a job running, return current state immediately
    # Don't waste resources creating duplicate jobs even if user clicks refresh
    if active_job:
        logger.info("Active job %s already running for class analysis, returning existing job", active_job.job_id)
        return JSONResponse(
            status_code=HTTP_202_ACCEPTED,
            content=ClassAnalysisResponse(
                analysis=class_analysis.analysis_text,
                status=class_analysis.status,
                job_id=active_job.job_id,
                computed_at=class_analysis.computed_at,
            ).model_dump(mode="json"),
        )
    
    # Fetch data needed for hash check and (potentially) for queueing
    prompt_version = _get_class_analysis_prompt_version(db)
    students = _fetch_students_for_class(db, school_value, grade, section_value)
    user_ids = [s.user_id for s in students]
    conversations_map, conversation_ids = _get_latest_conversations_for_users(db, user_ids)
    current_hash = _build_class_conversation_hash(students, conversations_map, prompt_version)
    
    # If we have cached analysis, check staleness
    if class_analysis.analysis_text and class_analysis.status == "ready":
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

    # Quick check: are there any conversations to analyze?
    if not conversation_ids:
        logger.warning("No conversations available for class analysis %s/%s/%s", school_value, grade, section_value)
        return ClassAnalysisResponse(
            analysis=None,
            status="ready",
            job_id=None,
            computed_at=None,
        )

    # Create job record
    job = _create_analysis_job(db, kind="class", class_analysis=class_analysis)
    class_analysis.status = "queued"
    class_analysis.updated_at = datetime.now(timezone.utc)
    db.add(class_analysis)
    db.commit()
    
    # Queue via SQS - send only identifiers, Brain will fetch transcript
    task_payload = {
        "task_type": "CLASS_ANALYSIS",
        "job_id": job.job_id,
        "school": school_value,
        "grade": grade,
        "section": section_value,
        "last_message_hash": current_hash,
    }
    
    try:
        await queue_service.send_batch_task(task_payload)
        logger.info("Queued CLASS_ANALYSIS task for job %s", job.job_id)
    except Exception as e:
        # If queue fails, mark job as failed
        logger.error("Failed to queue CLASS_ANALYSIS task: %s", e)
        job.status = "failed"
        job.error_message = f"Failed to queue task: {str(e)}"
        class_analysis.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to queue analysis task")

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
    student_id: int,
    force_refresh: bool = Query(False, description="Force recomputing the analysis even if cached"),
    db: Session = Depends(get_db),
    queue_service: QueueService = Depends(get_queue_service),
):
    """
    Returns cached analysis immediately if available, queues SQS job for refresh.
    This endpoint returns quickly to avoid API Gateway timeout.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Quick check: get or create analysis record (lightweight)
    student_analysis = _get_or_create_student_analysis(db, student)
    
    # Check for active job first - even with force_refresh, don't create duplicate jobs
    active_job = _find_active_job_for_analysis(db, student_analysis.id, "student")
    
    # If there's already a job running, return current state immediately
    # Don't waste resources creating duplicate jobs even if user clicks refresh
    if active_job:
        logger.info("Active job %s already running for student %s analysis, returning existing job", active_job.job_id, student_id)
        return JSONResponse(
            status_code=HTTP_202_ACCEPTED,
            content=ClassAnalysisResponse(
                analysis=student_analysis.analysis_text,
                status=student_analysis.status,
                job_id=active_job.job_id,
                computed_at=student_analysis.computed_at,
            ).model_dump(mode="json"),
        )
    
    # Compute hash for cache check (lightweight - just conversation metadata)
    prompt_version = _get_student_analysis_prompt_version(db)
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == student.user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    current_hash = _build_student_conversation_hash(conversations, prompt_version)
    
    # If we have cached analysis, check staleness
    if student_analysis.analysis_text and student_analysis.status == "ready":
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

    # Quick check: are there any conversations to analyze?
    if not conversations:
        logger.warning("No conversations available for student %s analysis", student_id)
        return ClassAnalysisResponse(
            analysis=None,
            status="ready",
            job_id=None,
            computed_at=None,
        )

    # Create job record
    job = _create_analysis_job(db, kind="student", student_analysis=student_analysis)
    student_analysis.status = "queued"
    student_analysis.updated_at = datetime.now(timezone.utc)
    db.add(student_analysis)
    db.commit()
    
    # Queue via SQS - send only identifiers, Brain will fetch transcript
    task_payload = {
        "task_type": "STUDENT_ANALYSIS",
        "job_id": job.job_id,
        "student_id": student_id,
        "last_message_hash": current_hash,
    }
    
    try:
        await queue_service.send_batch_task(task_payload)
        logger.info("Queued STUDENT_ANALYSIS task for job %s", job.job_id)
    except Exception as e:
        # If queue fails, mark job as failed
        logger.error("Failed to queue STUDENT_ANALYSIS task: %s", e)
        job.status = "failed"
        job.error_message = f"Failed to queue task: {str(e)}"
        student_analysis.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to queue analysis task")

    return JSONResponse(
        status_code=HTTP_202_ACCEPTED,
        content=ClassAnalysisResponse(
            analysis=student_analysis.analysis_text,
            status="queued",
            job_id=job.job_id,
            computed_at=student_analysis.computed_at,
        ).model_dump(mode="json"),
    )


## NOTE: _process_class_analysis_job and _process_student_analysis_job have been removed.
# Analysis processing is now handled by Brain via SQS queue.
# Brain receives the task, calls LLM, and posts results back via /api/internal/analysis-callback


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
