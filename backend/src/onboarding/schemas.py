"""
Schemas for onboarding system responses.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ConversationWithVisit(BaseModel):
    id: int
    user_id: int
    title: str
    visit_number: Optional[int] = None
    prompt_version_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ConversationCreateResponse(BaseModel):
    """Response for conversation creation with onboarding info."""
    conversation: ConversationWithVisit
    visit_number: int
    ai_opening_message: Optional[str] = None
    preparation_status: str  # "ready", "generating_memory", "generating_persona"
    requires_opening_message: bool = True
    
    class Config:
        from_attributes = True


class OpeningMessageCallbackPayload(BaseModel):
    """Payload for opening message callback from Brain."""
    conversation_id: int
    ai_message: str
    is_opening_message: bool = True
    pipeline_data: Optional[dict] = None  # Includes prompt_used, visit_number, context flags

