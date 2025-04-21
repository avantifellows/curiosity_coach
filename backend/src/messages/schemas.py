from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any

class MessageRequest(BaseModel):
    content: str
    
    @field_validator('content')
    @classmethod
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v

class MessageResponse(BaseModel):
    success: bool
    message: Optional[Dict[str, Any]] = None
    response: Optional[Dict[str, Any]] = None

class ChatHistoryResponse(BaseModel):
    success: bool
    messages: List[Dict[str, Any]] 