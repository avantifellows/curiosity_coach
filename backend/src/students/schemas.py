from __future__ import annotations

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from src.auth.schemas import StudentResponse


class ConversationMessageResponse(BaseModel):
    id: int
    content: str
    is_user: bool
    timestamp: datetime
    curiosity_score: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationWithMessagesResponse(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[ConversationMessageResponse]

    model_config = ConfigDict(from_attributes=True)


class StudentWithConversationResponse(BaseModel):
    student: StudentResponse
    latest_conversation: Optional[ConversationWithMessagesResponse] = None


class PaginatedConversationsResponse(BaseModel):
    conversations: List[ConversationWithMessagesResponse]
    next_offset: Optional[int] = None


class ClassAnalysisResponse(BaseModel):
    analysis: Optional[str] = None
    status: str
    job_id: Optional[str] = None
    computed_at: Optional[datetime] = None


class AnalysisJobStatusResponse(BaseModel):
    job_id: str
    status: str
    analysis: Optional[str] = None
    computed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    analysis_status: Optional[str] = None
