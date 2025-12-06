from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from sqlalchemy import func, and_
import httpx
import logging

from src.database import get_db
from src.models import Student, Conversation, Message
from src.students.schemas import (
    StudentWithConversationResponse,
    ConversationWithMessagesResponse,
    ConversationMessageResponse,
    PaginatedConversationsResponse,
    ClassAnalysisResponse,
)
from src.config.settings import settings

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/api/students",
    tags=["students"],
)


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
    school_value = school.strip()
    if not school_value:
        raise HTTPException(status_code=400, detail="School is required")

    section_value: Optional[str] = None
    if section is not None:
        section_value = section.strip().upper() or None

    query = (
        db.query(Student)
        .filter(
            Student.school == school_value,
            Student.grade == grade,
        )
    )

    if section_value is not None:
        query = query.filter(Student.section == section_value)

    students = query.order_by(Student.roll_number.asc()).all()

    user_ids = [student.user_id for student in students]
    conversations_map: Dict[int, Conversation] = {}
    messages_by_conversation: Dict[int, List[ConversationMessageResponse]] = {}

    if user_ids:
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

        for conversation in latest_conversations:
            conversations_map[conversation.user_id] = conversation

        conversation_ids = [conversation.id for conversation in latest_conversations]

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
    else:
        messages_by_conversation = {}

    response: List[StudentWithConversationResponse] = []
    for student in students:
        latest_conversation = conversations_map.get(student.user_id)
        latest_conversation_payload: Optional[ConversationWithMessagesResponse] = None

        if latest_conversation:
            latest_conversation_payload = ConversationWithMessagesResponse(
                id=latest_conversation.id,
                title=latest_conversation.title,
                updated_at=latest_conversation.updated_at,
                messages=messages_by_conversation.get(latest_conversation.id, []),
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
    school: str = Query(..., description="School name to filter students"),
    grade: int = Query(..., ge=1, le=12, description="Grade to filter students"),
    section: Optional[str] = Query(None, description="Optional section (e.g., A, B)"),
    db: Session = Depends(get_db),
):
    """
    Analyze all conversations for a class by calling Brain's analysis endpoint.
    Returns AI-generated insights about the class conversations.
    """
    school_value = school.strip()
    if not school_value:
        raise HTTPException(status_code=400, detail="School is required")

    section_value: Optional[str] = None
    if section is not None:
        section_value = section.strip().upper() or None

    # Get all students for the class (reuse existing logic)
    query = (
        db.query(Student)
        .filter(
            Student.school == school_value,
            Student.grade == grade,
        )
    )

    if section_value is not None:
        query = query.filter(Student.section == section_value)

    students = query.order_by(Student.roll_number.asc()).all()

    user_ids = [student.user_id for student in students]
    conversations_map: Dict[int, Conversation] = {}
    messages_by_conversation: Dict[int, List[ConversationMessageResponse]] = {}

    if user_ids:
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

        for conversation in latest_conversations:
            conversations_map[conversation.user_id] = conversation

        conversation_ids = [conversation.id for conversation in latest_conversations]

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

    # Format conversations as flat text (same format as ClassSummary displays)
    all_conversations_text_parts = []
    student_map = {student.user_id: student for student in students}
    
    for student in students:
        latest_conversation = conversations_map.get(student.user_id)
        if latest_conversation:
            all_conversations_text_parts.append(f"{student.first_name}")
            messages = messages_by_conversation.get(latest_conversation.id, [])
            for message in messages:
                sender = "Student" if message.is_user else "AI"
                all_conversations_text_parts.append(f"  {sender}: {message.content}")
    
    all_conversations_text = "\n".join(all_conversations_text_parts)
    
    if not all_conversations_text.strip():
        raise HTTPException(status_code=400, detail="No conversations found for this class to analyze")

    # Call Brain's /class-analysis endpoint
    brain_endpoint = (
        settings.LOCAL_BRAIN_ENDPOINT_URL
        if settings.APP_ENV == "development"
        else settings.BRAIN_ENDPOINT_URL
    )
    
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{brain_endpoint}/class-analysis",
                json={
                    "all_conversations": all_conversations_text,
                    "call_type": "class_analysis"
                }
            )
            response.raise_for_status()
            brain_response = response.json()
            return ClassAnalysisResponse(
                analysis=brain_response.get("analysis", ""),
                status="success"
            )
    except httpx.TimeoutException:
        logger.error("Timeout calling Brain for class analysis")
        raise HTTPException(status_code=504, detail="Analysis request timed out. Please try again.")
    except httpx.HTTPStatusError as e:
        logger.error(f"Brain returned error {e.response.status_code}: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Brain analysis failed: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Brain: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to Brain service: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in class analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate analysis: {str(e)}")


@router.post("/{student_id}/analysis", response_model=ClassAnalysisResponse)
async def analyze_student_conversations(
    student_id: int,
    db: Session = Depends(get_db),
):
    """
    Analyze all conversations for a student by calling Brain's analysis endpoint.
    Returns AI-generated insights about the student's conversations.
    """
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get all conversations for this student
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

    # Format conversations as flat text
    all_conversations_text_parts = []
    
    for conversation in conversations:
        all_conversations_text_parts.append(f"Conversation: {conversation.title or 'Untitled'}")
        messages = messages_by_conversation.get(conversation.id, [])
        for message in messages:
            sender = "Student" if message.is_user else "AI"
            all_conversations_text_parts.append(f"  {sender}: {message.content}")
        all_conversations_text_parts.append("")  # Empty line between conversations
    
    all_conversations_text = "\n".join(all_conversations_text_parts)
    
    if not all_conversations_text.strip():
        raise HTTPException(status_code=400, detail="No conversations found for this student to analyze")

    # Call Brain's /student-analysis endpoint
    brain_endpoint = (
        settings.LOCAL_BRAIN_ENDPOINT_URL
        if settings.APP_ENV == "development"
        else settings.BRAIN_ENDPOINT_URL
    )
    
    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                f"{brain_endpoint}/student-analysis",
                json={
                    "all_conversations": all_conversations_text,
                    "call_type": "student_analysis"
                }
            )
            response.raise_for_status()
            brain_response = response.json()
            return ClassAnalysisResponse(
                analysis=brain_response.get("analysis", ""),
                status="success"
            )
    except httpx.TimeoutException:
        logger.error("Timeout calling Brain for student analysis")
        raise HTTPException(status_code=504, detail="Analysis request timed out. Please try again.")
    except httpx.HTTPStatusError as e:
        logger.error(f"Brain returned error {e.response.status_code}: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Brain analysis failed: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Error connecting to Brain: {e}")
        raise HTTPException(status_code=503, detail=f"Failed to connect to Brain service: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in student analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate analysis: {str(e)}")

