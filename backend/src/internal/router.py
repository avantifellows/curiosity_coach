from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from src.database import get_db
from typing import List, Optional
from src.internal import crud
from src.memories.schemas import MemoryInDB
from src.memories import crud as memories_crud
from src.user_personas.schemas import UserPersona as UserPersonaSchema
from src.models import (
    UserPersona, Conversation, ConversationMemory, 
    Prompt, PromptVersion, get_conversation, save_message,
    save_message_pipeline_data
)
from src.onboarding.schemas import OpeningMessageCallbackPayload
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/internal",
    tags=["internal"],
    # These endpoints should not be exposed in public docs
    include_in_schema=False,
)

@router.get("/users/{user_id}/memories", response_model=List[MemoryInDB])
def get_user_conversation_memories(user_id: int, db: Session = Depends(get_db)):
    """
    Get all conversation memories for a specific user.
    This is an internal endpoint for the Brain service.
    """
    memories = crud.get_conversation_memories_by_user_id(db=db, user_id=user_id)
    if not memories:
        # It's better to return an empty list than a 404
        # if the user exists but has no memories.
        # A 404 could imply the user or the endpoint itself was not found.
        return []
    return memories 

@router.get("/conversations/{conversation_id}/memory", response_model=MemoryInDB)
def get_conversation_memory(conversation_id: int, db: Session = Depends(get_db)):
    """
    Get the memory for a specific conversation. Returns 404 if not found.
    This is an internal endpoint for the Brain service.
    """
    memory = memories_crud.get_memory_by_conversation_id(db=db, conversation_id=conversation_id)
    if not memory:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found for conversation")
    return memory


@router.get("/users/{user_id}/persona", response_model=UserPersonaSchema)
def get_user_persona(user_id: int, db: Session = Depends(get_db)):
    """
    Get the user persona by user_id. Returns 404 if not found.
    This is an internal endpoint for the Brain service.
    """
    persona: UserPersona | None = db.query(UserPersona).filter(UserPersona.user_id == user_id).first()
    if not persona:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found for user")
    return persona

@router.get("/users/{user_id}/previous-memories")
def get_user_previous_memories(
    user_id: int,
    exclude_conversation_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Internal endpoint: Return all conversation memories for a user.
    Optionally exclude a specific conversation (typically the current one).
    Used by Brain for {{PREVIOUS_CONVERSATIONS_MEMORY}} placeholder injection.
    """
    query = (
        db.query(ConversationMemory)
        .join(Conversation)
        .filter(Conversation.user_id == user_id)
    )
    if exclude_conversation_id:
        query = query.filter(Conversation.id != exclude_conversation_id)
    
    memories = query.order_by(Conversation.created_at.asc()).all()
    
    return {
        "user_id": user_id,
        "count": len(memories),
        "memories": [
            {
                "conversation_id": mem.conversation_id,
                "memory_data": mem.memory_data,
                "created_at": mem.created_at.isoformat()
            }
            for mem in memories
        ]
    }

@router.get("/conversations/{conversation_id}/prompt")
def get_conversation_prompt(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Internal endpoint: Return prompt text for a conversation's assigned prompt version.
    Used by Brain for opening message generation.
    """
    logger.info(f"🔍 get_conversation_prompt called for conversation_id={conversation_id}")
    
    conversation = get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    logger.info(f"📋 Conversation {conversation_id} has prompt_version_id={conversation.prompt_version_id}")
    
    if not conversation.prompt_version_id:
        logger.warning(f"⚠️ Conversation {conversation_id} has NO prompt_version_id assigned! Falling back to simplified_conversation")
        # Fallback to simplified_conversation if no prompt assigned
        prompt = db.query(Prompt).filter(Prompt.name == "simplified_conversation").first()
        if not prompt:
            raise HTTPException(status_code=500, detail="No valid prompt found")
        prompt_version = db.query(PromptVersion).filter(
            PromptVersion.prompt_id == prompt.id,
            PromptVersion.is_production == True
        ).first()
    else:
        logger.info(f"✅ Fetching prompt_version with id={conversation.prompt_version_id}")
        prompt_version = db.query(PromptVersion).get(conversation.prompt_version_id)
    
    if not prompt_version:
        raise HTTPException(status_code=404, detail="Prompt version not found")
    
    # Get the prompt to fetch its purpose
    prompt = db.query(Prompt).get(prompt_version.prompt_id)
    prompt_purpose = prompt.prompt_purpose if prompt else None
    prompt_name = prompt.name if prompt else None
    
    logger.info(f"🎯 Returning prompt: name={prompt_name}, purpose={prompt_purpose}, version={prompt_version.version_number}, prompt_id={prompt_version.prompt_id}, text_length={len(prompt_version.prompt_text)}")
    
    return {
        "prompt_text": prompt_version.prompt_text,
        "version_number": prompt_version.version_number,
        "prompt_id": prompt_version.prompt_id,
        "prompt_purpose": prompt_purpose  # Include the prompt purpose (visit_1, visit_2, etc.)
    }

@router.get("/users/{user_id}/conversations")
def get_user_conversations_internal(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Internal endpoint: Return list of conversation IDs for a user.
    Used by Brain to check conversation count.
    """
    conversations = db.query(Conversation).filter(
        Conversation.user_id == user_id
    ).order_by(Conversation.created_at.asc()).all()
    
    return {
        "user_id": user_id,
        "conversation_count": len(conversations),
        "conversation_ids": [c.id for c in conversations]
    }

@router.post("/opening_message")
async def receive_opening_message(
    payload: OpeningMessageCallbackPayload,
    db: Session = Depends(get_db)
):
    """
    Receive AI opening message from Brain and save to DB.
    Includes pipeline data for debugging and metrics.
    """
    # Create AI message (is_user=False)
    message = save_message(
        db=db,
        conversation_id=payload.conversation_id,
        content=payload.ai_message,
        is_user=False,
        responds_to_message_id=None
    )
    
    # Save pipeline data if provided
    if payload.pipeline_data:
        logger.info(f"Saving pipeline data for opening message {message.id}", extra={
            "message_id": message.id,
            "has_steps": "steps" in payload.pipeline_data,
            "steps_count": len(payload.pipeline_data.get("steps", [])) if isinstance(payload.pipeline_data.get("steps"), list) else 0
        })
        save_message_pipeline_data(
            db=db,
            message_id=message.id,
            pipeline_data_dict=payload.pipeline_data
        )
    else:
        logger.warning(f"No pipeline data provided for opening message {message.id}")
    
    logger.info(f"Opening message saved for conversation {payload.conversation_id}", extra={
        "conversation_id": payload.conversation_id,
        "message_id": message.id,
        "is_opening_message": True,
        "has_pipeline_data": payload.pipeline_data is not None
    })
    
    return {"status": "success", "message_id": message.id}