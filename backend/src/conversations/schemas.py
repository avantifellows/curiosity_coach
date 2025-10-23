from pydantic import BaseModel, constr
from datetime import datetime
from typing import List, Optional

# --- Conversation Schemas ---

class ConversationBase(BaseModel):
    title: Optional[str] = "New Chat"
    core_chat_theme: Optional[str] = None

class ConversationTitleUpdate(BaseModel):
    title: str

class ConversationCreate(ConversationBase):
    pass # No extra fields needed for creation beyond title

class Conversation(ConversationBase):
    id: int
    user_id: int
    visit_number: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Replace orm_mode=True

# For listing conversations - might want less detail or specific fields
class ConversationSummary(BaseModel):
    id: int
    title: Optional[str]
    core_chat_theme: Optional[str] = None
    visit_number: Optional[int] = None
    updated_at: datetime

    class Config:
        from_attributes = True 
        
        
class ConversationCoreChatThemeUpdate(BaseModel):
    core_chat_theme: Optional[str] = None