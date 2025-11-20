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

    model_config = ConfigDict(from_attributes=True)


class ConversationWithMessagesResponse(BaseModel):
    id: int
    title: Optional[str] = None
    updated_at: datetime
    messages: List[ConversationMessageResponse]

    model_config = ConfigDict(from_attributes=True)


class StudentWithConversationResponse(BaseModel):
    student: StudentResponse
    latest_conversation: Optional[ConversationWithMessagesResponse] = None

