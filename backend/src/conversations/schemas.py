from pydantic import BaseModel, Field, constr, field_validator
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
    tags: List[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Replace orm_mode=True

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            normalized = []
            for item in v:
                if isinstance(item, str):
                    normalized.append(item)
                elif hasattr(item, "name"):
                    normalized.append(str(item.name))
                else:
                    normalized.append(str(item))
            return normalized
        return v

# For listing conversations - might want less detail or specific fields
class ConversationSummary(BaseModel):
    id: int
    title: Optional[str]
    core_chat_theme: Optional[str] = None
    visit_number: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    updated_at: datetime

    class Config:
        from_attributes = True 

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            normalized = []
            for item in v:
                if isinstance(item, str):
                    normalized.append(item)
                elif hasattr(item, "name"):
                    normalized.append(str(item.name))
                else:
                    normalized.append(str(item))
            return normalized
        return v
        
        
class ConversationCoreChatThemeUpdate(BaseModel):
    core_chat_theme: Optional[str] = None


class ConversationTagsUpdate(BaseModel):
    tags: List[str] = Field(default_factory=list)


class ConversationTagsResponse(BaseModel):
    id: int
    tags: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, v):
        if v is None:
            return []
        if isinstance(v, list):
            normalized = []
            for item in v:
                if isinstance(item, str):
                    normalized.append(item)
                elif hasattr(item, "name"):
                    normalized.append(str(item.name))
                else:
                    normalized.append(str(item))
            return normalized
        return v
