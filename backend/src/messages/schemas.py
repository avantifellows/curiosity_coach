from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any
from datetime import datetime
from typing_extensions import Annotated

class MessageRequest(BaseModel):
    """Schema for sending a message."""
    content: str = Field(..., description="Content of the message")
    purpose: Optional[str] = Field("chat", description="Purpose of the message (chat, test_generation, doubt_solver)")
    conversation_id: Optional[str] = Field(None, description="ID of the conversation this message belongs to")
    
    @field_validator('content')
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v

class MessageData(BaseModel):
    """Schema for message data."""
    id: int = Field(..., description="Message ID")
    content: str = Field(..., description="Content of the message")
    is_user: bool = Field(..., description="Whether the message is from the user")
    timestamp: datetime = Field(..., description="Timestamp of the message")
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
        "json_encoders": {
            datetime: lambda dt: dt.isoformat()
        }
    }

class MessageResponse(BaseModel):
    """Schema for the message response."""
    success: bool = Field(..., description="Whether the message was sent successfully")
    message: MessageData = Field(..., description="The message that was sent")
    response: Optional[MessageData] = Field(None, description="The response message from the AI")

class ChatHistoryResponse(BaseModel):
    """Schema for chat history response."""
    success: bool = Field(..., description="Whether the request was successful")
    messages: List[MessageData] = Field(..., description="List of messages in the chat history") 