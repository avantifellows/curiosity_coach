from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Any
from datetime import datetime
from typing_extensions import Annotated

class MessageRequest(BaseModel):
    """Schema for sending a message to a specific conversation."""
    content: str = Field(..., description="Content of the message")
    # conversation_id is now part of the path parameter, removed from here
    purpose: Optional[str] = Field("chat", description="Optional purpose field (e.g., chat, test_generation)")
    
    @field_validator('content')
    def content_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Message content cannot be empty')
        return v

class MessageData(BaseModel):
    """Schema for message data representation."""
    id: int = Field(..., description="Message ID")
    # We could add conversation_id here if the frontend ever needs it per message
    # conversation_id: int = Field(..., description="Conversation ID this message belongs to") 
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

# Removed MessageResponse as SendMessageResponse covers the initial return
# and polling covers the AI response.

class SendMessageResponse(BaseModel):
    """Schema for the initial response after sending a message (before AI response)."""
    success: bool = Field(..., description="Whether the message was accepted and processing started successfully")
    message: MessageData = Field(..., description="The user message that was saved")

class ChatHistoryResponse(BaseModel):
    """Schema for chat history response for a conversation."""
    success: bool = Field(..., description="Whether the request was successful")
    messages: List[MessageData] = Field(..., description="List of messages in the conversation history")

class BrainResponsePayload(BaseModel):
    """Schema for the payload received from the Brain service callback."""
    user_id: int # Keep user_id for potential validation/logging if needed by Brain
    conversation_id: int = Field(..., description="ID of the conversation this response belongs to")
    original_message_id: Optional[int] = Field(None, description="ID of the user message this is a response to")
    llm_response: str = Field(..., description="The final content of the AI's response")
    pipeline_data: Dict[str, Any] = Field(..., description="Detailed data from the Brain pipeline")
    prompt_version_id: Optional[int] = Field(None, description="ID of the prompt version used for this conversation") 