from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from sqlalchemy import func, and_

from src.database import get_db
from src.models import Student, Conversation, Message
from src.students.schemas import (
    StudentWithConversationResponse,
    ConversationWithMessagesResponse,
    ConversationMessageResponse,
    PaginatedConversationsResponse,
)


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

