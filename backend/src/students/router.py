from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, selectinload
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_
import logging
import hashlib
import uuid
from datetime import datetime, timezone, timedelta, date

from src.database import get_db
from src.models import (
    Student,
    Tag,
    Conversation,
    Message,
    ConversationEvaluation,
    ClassAnalysis,
    StudentAnalysis,
    AnalysisJob,
    PromptVersion,
)
from src.students.schemas import (
    StudentWithConversationResponse,
    ConversationWithMessagesResponse,
    ConversationMessageResponse,
    ConversationEvaluationMetricsResponse,
    ConversationCuriositySummaryResponse,
    ConversationTopicResponse,
    PaginatedConversationsResponse,
    ClassAnalysisResponse,
    AnalysisJobStatusResponse,
    StudentTagsUpdateRequest,
    ConversationLookupResponse,
)
from src.conversations.schemas import ConversationTagsUpdate, ConversationTagsResponse
from src.auth.schemas import StudentResponse
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


def _normalize_tag_name(raw_tag: str) -> str:
    normalized = " ".join(raw_tag.strip().split())
    if not normalized:
        raise HTTPException(status_code=400, detail="Tag names cannot be empty")
    if len(normalized) > 64:
        raise HTTPException(status_code=400, detail="Tag names must be 64 characters or fewer")
    return normalized.lower()


def _normalize_tag_list(raw_tags: List[str]) -> List[str]:
    normalized_tags: List[str] = []
    seen = set()
    for raw_tag in raw_tags:
        if raw_tag is None:
            continue
        normalized = _normalize_tag_name(raw_tag)
        if normalized in seen:
            continue
        seen.add(normalized)
        normalized_tags.append(normalized)
    return normalized_tags


def _normalize_tag_query(raw_tags: Optional[List[str]]) -> List[str]:
    if not raw_tags:
        return []
    flattened: List[str] = []
    for item in raw_tags:
        if not item:
            continue
        parts = [part for part in item.split(",") if part.strip()]
        flattened.extend(parts)
    return _normalize_tag_list(flattened)


def _fetch_students_for_class(
    db: Session,
    school_value: str,
    grade: int,
    section_value: Optional[str],
    tags: Optional[List[str]] = None,
    tag_mode: str = "any",
) -> List[Student]:
    query = (
        db.query(Student)
        .options(selectinload(Student.tags))
        .filter(
            Student.school == school_value,
            Student.grade == grade,
        )
    )

    if section_value is not None:
        query = query.filter(Student.section == section_value)

    if tags:
        if tag_mode == "all":
            query = (
                query.join(Student.tags)
                .filter(Tag.name.in_(tags))
                .group_by(Student.id)
                .having(func.count(func.distinct(Tag.id)) == len(tags))
            )
        else:
            query = query.join(Student.tags).filter(Tag.name.in_(tags)).distinct()

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
        .options(selectinload(Conversation.tags))
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


def _get_evaluations_by_conversation(
    db: Session,
    conversation_ids: List[int],
) -> Dict[int, ConversationEvaluation]:
    if not conversation_ids:
        return {}

    evaluations = (
        db.query(ConversationEvaluation)
        .filter(ConversationEvaluation.conversation_id.in_(conversation_ids))
        .all()
    )

    return {evaluation.conversation_id: evaluation for evaluation in evaluations}


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "y"}:
            return True
        if normalized in {"false", "no", "n"}:
            return False
    return None


def _normalize_topics(raw_topics) -> List[ConversationTopicResponse]:
    topics: List[ConversationTopicResponse] = []
    if not raw_topics or not isinstance(raw_topics, list):
        return topics

    for item in raw_topics:
        if isinstance(item, str):
            term = item.strip()
            if term:
                topics.append(ConversationTopicResponse(term=term))
        elif isinstance(item, dict):
            term = item.get('term') or item.get('topic') or item.get('name')
            if not term:
                continue
            weight = _safe_float(item.get('weight') or item.get('total_weight') or item.get('score'))
            count = _safe_int(item.get('conversation_count') or item.get('count'))
            total_weight = _safe_float(item.get('total_weight'))
            conversation_count = _safe_int(item.get('conversation_count'))
            topics.append(
                ConversationTopicResponse(
                    term=str(term),
                    weight=weight,
                    count=count,
                    total_weight=total_weight,
                    conversation_count=conversation_count,
                )
            )

    return topics


def _build_conversation_evaluation_response(
    evaluation: Optional[ConversationEvaluation],
) -> Optional[ConversationEvaluationMetricsResponse]:
    if not evaluation or not isinstance(evaluation.metrics, dict):
        return None

    metrics = evaluation.metrics

    depth = _safe_float(metrics.get('depth'))
    relevant_questions = _safe_int(metrics.get('relevant_question_count'))
    attention_span = _safe_float(metrics.get('attention_span'))
    depth_sample_size = _safe_int(metrics.get('depth_sample_size') or metrics.get('depth_count'))
    relevant_sample_size = _safe_int(metrics.get('relevant_sample_size') or metrics.get('relevant_count'))
    conversation_count = _safe_int(metrics.get('conversation_count'))
    divergent = _safe_bool(metrics.get('divergent'))
    student_request = metrics.get('student_request')
    if isinstance(student_request, str):
        student_request = student_request.strip().lower() or None
    else:
        student_request = None

    topics = _normalize_topics(metrics.get('topics'))

    return ConversationEvaluationMetricsResponse(
        depth=depth,
        relevant_question_count=relevant_questions,
        topics=topics,
        attention_span=attention_span,
        divergent=divergent,
        student_request=student_request,
        avg_attention_span=_safe_float(metrics.get('avg_attention_span')),
        attention_sample_size=_safe_int(metrics.get('attention_sample_size')),
        total_attention_span=_safe_float(metrics.get('total_attention_span')),
        computed_at=evaluation.computed_at,
        status=evaluation.status,
        prompt_version_id=evaluation.prompt_version_id,
        depth_sample_size=depth_sample_size,
        relevant_sample_size=relevant_sample_size,
        conversation_count=conversation_count,
    )


def _build_curiosity_summary(messages: List[Message]) -> Optional[ConversationCuriositySummaryResponse]:
    scores = [score for score in (message.curiosity_score for message in messages) if isinstance(score, (int, float))]
    if not scores:
        return None

    average = sum(scores) / len(scores)
    latest_score: Optional[int] = None
    for message in reversed(messages):
        if isinstance(message.curiosity_score, (int, float)):
            latest_score = int(message.curiosity_score)
            break

    return ConversationCuriositySummaryResponse(
        average=average,
        latest=latest_score,
        sample_size=len(scores),
    )


def _compute_attention_minutes(messages: List[Message], attention_turns: Optional[float]) -> Optional[float]:
    if attention_turns is None:
        return None
    try:
        attention_value = float(attention_turns)
    except (TypeError, ValueError):
        return None
    user_message_count = sum(1 for message in messages if message.is_user)
    if user_message_count <= 0:
        return None
    timestamps = [message.timestamp for message in messages if message.timestamp]
    if not timestamps:
        return None
    minutes_spent = (max(timestamps) - min(timestamps)).total_seconds() / 60.0
    if minutes_spent < 0:
        return None
    avg_minutes_per_user_message = minutes_spent / user_message_count
    return attention_value * avg_minutes_per_user_message


def _build_conversation_payload(
    conversation: Conversation,
    messages: List[Message],
    evaluation: Optional[ConversationEvaluation],
) -> ConversationWithMessagesResponse:
    has_user_message = any(message.is_user for message in messages)
    message_payloads = [
        ConversationMessageResponse(
            id=message.id,
            content=message.content,
            is_user=message.is_user,
            timestamp=message.timestamp,
            curiosity_score=message.curiosity_score,
        )
        for message in messages
    ]

    evaluation_payload = _build_conversation_evaluation_response(evaluation) if has_user_message else None
    if evaluation_payload and evaluation_payload.attention_span is not None:
        attention_minutes = _compute_attention_minutes(messages, evaluation_payload.attention_span)
        if attention_minutes is not None:
            evaluation_payload.attention_span = attention_minutes
    curiosity_summary = (
        _build_curiosity_summary(messages)
        if has_user_message
        else None
    )

    return ConversationWithMessagesResponse(
        id=conversation.id,
        title=conversation.title,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        tags=[tag.name for tag in conversation.tags],
        messages=message_payloads,
        evaluation=evaluation_payload,
        curiosity_summary=curiosity_summary,
    )


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
    tags: Optional[List[str]] = Query(None, description="Optional tag filters (comma-separated or repeated)"),
    tag_mode: str = Query("any", description="Tag match mode: any or all"),
    db: Session = Depends(get_db),
):
    """
    Return all students that match the provided school, grade, and optional section.
    """
    school_value = _normalize_school_value(school)
    section_value = _normalize_section_value(section)

    normalized_tags = _normalize_tag_query(tags)
    if tag_mode not in ("any", "all"):
        raise HTTPException(status_code=400, detail="tag_mode must be 'any' or 'all'")

    students = _fetch_students_for_class(
        db,
        school_value,
        grade,
        section_value,
        tags=normalized_tags or None,
        tag_mode=tag_mode,
    )

    user_ids = [student.user_id for student in students]
    conversations_map, conversation_ids = _get_latest_conversations_for_users(db, user_ids)
    messages_by_conversation_raw = _get_messages_by_conversation(db, conversation_ids)
    evaluations_by_conversation = _get_evaluations_by_conversation(db, conversation_ids)

    response: List[StudentWithConversationResponse] = []
    for student in students:
        latest_conversation = conversations_map.get(student.user_id)
        latest_conversation_payload: Optional[ConversationWithMessagesResponse] = None

        if latest_conversation:
            messages_raw = messages_by_conversation_raw.get(latest_conversation.id, [])
            evaluation = evaluations_by_conversation.get(latest_conversation.id)
            latest_conversation_payload = _build_conversation_payload(
                latest_conversation,
                messages_raw,
                evaluation,
            )

        response.append(
            StudentWithConversationResponse(
                student=student, latest_conversation=latest_conversation_payload
            )
        )

    return response


@router.get("/tags", response_model=List[str])
def list_class_tags(
    school: str = Query(..., description="School name to filter tags"),
    grade: int = Query(..., ge=1, le=12, description="Grade to filter tags"),
    section: Optional[str] = Query(None, description="Optional section (e.g., A, B)"),
    q: Optional[str] = Query(None, description="Optional search term"),
    db: Session = Depends(get_db),
):
    school_value = _normalize_school_value(school)
    section_value = _normalize_section_value(section)
    normalized_query = None
    if q:
        normalized_query = " ".join(q.strip().split()).lower()
        if not normalized_query:
            normalized_query = None

    query = (
        db.query(Tag.name)
        .join(Tag.students)
        .filter(
            Student.school == school_value,
            Student.grade == grade,
        )
    )

    if section_value is not None:
        query = query.filter(Student.section == section_value)

    if normalized_query:
        query = query.filter(Tag.name.ilike(f"%{normalized_query}%"))

    tags = query.distinct().order_by(Tag.name.asc()).all()
    return [row[0] for row in tags]


@router.get("/conversation-tags", response_model=List[str])
def list_class_conversation_tags(
    school: str = Query(..., description="School name to filter tags"),
    grade: int = Query(..., ge=1, le=12, description="Grade to filter tags"),
    section: Optional[str] = Query(None, description="Optional section (e.g., A, B)"),
    q: Optional[str] = Query(None, description="Optional search term"),
    db: Session = Depends(get_db),
):
    school_value = _normalize_school_value(school)
    section_value = _normalize_section_value(section)
    normalized_query = None
    if q:
        normalized_query = " ".join(q.strip().split()).lower()
        if not normalized_query:
            normalized_query = None

    query = (
        db.query(Tag.name)
        .join(Tag.conversations)
        .join(Student, Student.user_id == Conversation.user_id)
        .filter(
            Student.school == school_value,
            Student.grade == grade,
        )
    )

    if section_value is not None:
        query = query.filter(Student.section == section_value)

    if normalized_query:
        query = query.filter(Tag.name.ilike(f"%{normalized_query}%"))

    tags = query.distinct().order_by(Tag.name.asc()).all()
    return [row[0] for row in tags]


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student_tags(
    student_id: int,
    payload: StudentTagsUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    Replace all tags for a student.
    """
    student = (
        db.query(Student)
        .options(selectinload(Student.tags))
        .filter(Student.id == student_id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    normalized_tags = _normalize_tag_list(payload.tags)
    if not normalized_tags:
        student.tags = []
        db.commit()
        db.refresh(student)
        return student

    existing_tags = db.query(Tag).filter(Tag.name.in_(normalized_tags)).all()
    tag_map = {tag.name: tag for tag in existing_tags}
    ordered_tags: List[Tag] = []

    for name in normalized_tags:
        tag = tag_map.get(name)
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            tag_map[name] = tag
        ordered_tags.append(tag)

    student.tags = ordered_tags
    db.commit()
    db.refresh(student)
    return student


@router.patch("/{student_id}/conversations/{conversation_id}/tags", response_model=ConversationTagsResponse)
def update_student_conversation_tags(
    student_id: int,
    conversation_id: int,
    payload: ConversationTagsUpdate,
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    conversation = (
        db.query(Conversation)
        .options(selectinload(Conversation.tags))
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if not conversation or conversation.user_id != student.user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    normalized_tags = _normalize_tag_list(payload.tags)
    if not normalized_tags:
        conversation.tags = []
        db.commit()
        db.refresh(conversation)
        return conversation

    existing_tags = db.query(Tag).filter(Tag.name.in_(normalized_tags)).all()
    tag_map = {tag.name: tag for tag in existing_tags}
    ordered_tags: List[Tag] = []

    for name in normalized_tags:
        tag = tag_map.get(name)
        if not tag:
            tag = Tag(name=name)
            db.add(tag)
            tag_map[name] = tag
        ordered_tags.append(tag)

    conversation.tags = ordered_tags
    db.commit()
    db.refresh(conversation)
    return conversation


@router.get("/{student_id}/conversations", response_model=PaginatedConversationsResponse)
def list_student_conversations(
    student_id: int,
    limit: int = Query(3, ge=1, le=50),
    offset: int = Query(0, ge=0),
    day: Optional[date] = Query(None, description="Optional day filter (YYYY-MM-DD)"),
    tags: Optional[List[str]] = Query(None, description="Optional tag filters (comma-separated or repeated)"),
    tag_mode: str = Query("any", description="Tag match mode: any or all"),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    normalized_tags = _normalize_tag_query(tags)
    if tag_mode not in ("any", "all"):
        raise HTTPException(status_code=400, detail="tag_mode must be 'any' or 'all'")

    base_query = (
        db.query(Conversation)
        .options(selectinload(Conversation.tags))
        .filter(Conversation.user_id == student.user_id)
        .order_by(Conversation.updated_at.desc())
    )
    if day:
        window_start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
        window_end = window_start + timedelta(days=1)
        timestamp = func.coalesce(Conversation.updated_at, Conversation.created_at)
        base_query = base_query.filter(timestamp >= window_start, timestamp < window_end)

    if normalized_tags:
        if tag_mode == "all":
            base_query = (
                base_query.join(Conversation.tags)
                .filter(Tag.name.in_(normalized_tags))
                .group_by(Conversation.id)
                .having(func.count(func.distinct(Tag.id)) == len(normalized_tags))
            )
        else:
            base_query = base_query.join(Conversation.tags).filter(Tag.name.in_(normalized_tags)).distinct()

    conversations = base_query.offset(offset).limit(limit + 1).all()
    has_more = len(conversations) > limit
    conversations = conversations[:limit]

    conversation_ids = [conversation.id for conversation in conversations]
    messages_by_conversation_raw: Dict[int, List[Message]] = {}

    if conversation_ids:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id.in_(conversation_ids))
            .order_by(Message.conversation_id.asc(), Message.timestamp.asc())
            .all()
        )

        for message in messages:
            messages_by_conversation_raw.setdefault(message.conversation_id, []).append(message)

    evaluations_by_conversation = _get_evaluations_by_conversation(db, conversation_ids)

    response_conversations = [
        _build_conversation_payload(
            conversation,
            messages_by_conversation_raw.get(conversation.id, []),
            evaluations_by_conversation.get(conversation.id),
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
        .options(selectinload(Conversation.tags))
        .filter(Conversation.user_id == student.user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )

    conversation_ids = [conversation.id for conversation in conversations]
    messages_by_conversation_raw: Dict[int, List[Message]] = {}

    if conversation_ids:
        messages = (
            db.query(Message)
            .filter(Message.conversation_id.in_(conversation_ids))
            .order_by(Message.conversation_id.asc(), Message.timestamp.asc())
            .all()
        )

        for message in messages:
            messages_by_conversation_raw.setdefault(message.conversation_id, []).append(message)

    evaluations_by_conversation = _get_evaluations_by_conversation(db, conversation_ids)

    response_conversations = [
        _build_conversation_payload(
            conversation,
            messages_by_conversation_raw.get(conversation.id, []),
            evaluations_by_conversation.get(conversation.id),
        )
        for conversation in conversations
    ]

    return response_conversations


@router.get("/conversations/{conversation_id}/lookup", response_model=ConversationLookupResponse)
def lookup_conversation_student(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    """
    Resolve a conversation_id to its student (for teacher/admin views).
    """
    student = (
        db.query(Student)
        .join(Conversation, Conversation.user_id == Student.user_id)
        .options(selectinload(Student.tags))
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Conversation not found for any student")

    return ConversationLookupResponse(conversation_id=conversation_id, student=student)


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

    analysis_text: Optional[str] = None
    computed_at: Optional[datetime] = None
    analysis_status: Optional[str] = None
    metrics: Optional[dict] = None

    if job.analysis_kind == "class" and job.class_analysis:
        analysis = job.class_analysis
        analysis_text = analysis.analysis_text
        computed_at = analysis.computed_at
        analysis_status = analysis.status
    elif job.analysis_kind == "student" and job.student_analysis:
        analysis = job.student_analysis
        analysis_text = analysis.analysis_text
        computed_at = analysis.computed_at
        analysis_status = analysis.status
    elif job.analysis_kind == "conversation" and job.conversation_evaluation:
        evaluation = job.conversation_evaluation
        metrics = evaluation.metrics
        computed_at = evaluation.computed_at
        analysis_status = evaluation.status

    payload = AnalysisJobStatusResponse(
        job_id=job.job_id,
        status=job.status,
        analysis=analysis_text,
        computed_at=computed_at,
        error_message=job.error_message,
        analysis_status=analysis_status,
        metrics=metrics,
    )

    return JSONResponse(content=payload.model_dump(mode="json"))
