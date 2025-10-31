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
    save_message_pipeline_data, update_conversation_core_chat_theme,
    Message, MessagePipelineData, LMHomework
)
from src.onboarding.schemas import OpeningMessageCallbackPayload
import logging
from src.analytics_agent.schemas import HomeworkItemsPayload, AnalyticsTriggerPayload
from src.analytics_agent.registry import MEMORY_GENERATION_EVENT, flows_for_event
from src.analytics_agent.scheduler import enqueue_flows
from src.analytics_agent.schemas import KnowledgeItemsPayload
from src.models import LMUserKnowledge, Conversation
    
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


@router.put("/conversations/{conversation_id}/core-chat-theme")
async def update_conversation_core_theme_internal(
    conversation_id: int,
    payload: dict,
    db: Session = Depends(get_db)
):
    """
    Internal endpoint to update conversation core theme.
    Used by Brain service - no authentication required.
    """
    try:
        core_theme = payload.get("core_chat_theme")
        if not core_theme:
            raise HTTPException(status_code=400, detail="core_chat_theme is required")
        
        # Get the conversation to find the user_id
        conversation = get_conversation(db, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        # Update conversation with extracted theme
        updated_conversation = update_conversation_core_chat_theme(
            db=db,
            conversation_id=conversation_id,
            new_core_chat_theme=core_theme,
            user_id=conversation.user_id  # Use the conversation's user_id
        )
        
        if updated_conversation:
            logger.info(f"Successfully updated conversation {conversation_id} with core theme: '{core_theme}'")
            return {"success": True, "message": "Core theme updated successfully"}
        else:
            logger.error(f"Failed to update conversation {conversation_id} with core theme")
            raise HTTPException(status_code=404, detail="Conversation not found")
            
    except Exception as e:
        logger.error(f"Error updating core theme for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating core theme: {str(e)}")
    

@router.get("/conversations/{conversation_id}/core-theme")
async def get_conversation_core_theme_internal(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Internal endpoint to get conversation core theme.
    Used by Brain service - no authentication required.
    """
    try:
        conversation = get_conversation(db, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {
            "conversation_id": conversation_id,
            "core_theme": conversation.core_chat_theme
        }
        
    except Exception as e:
        logger.error(f"Error fetching core theme for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching core theme: {str(e)}")
    

@router.get("/conversations/{conversation_id}/messages_with_pipeline")
def get_conversation_messages_with_pipeline(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Internal endpoint: Return messages with their pipeline data for Brain service.
    Used to retrieve previous exploration directions.
    """
    logger.info(f"get_conversation_messages_with_pipeline called for conversation_id={conversation_id}")
    
    # Get messages with their pipeline data
    messages_with_pipeline = (
        db.query(Message, MessagePipelineData)
        .outerjoin(MessagePipelineData, Message.id == MessagePipelineData.message_id)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp.asc())
        .all()
    )
    
    result = []
    for message, pipeline_data in messages_with_pipeline:
        message_dict = {
            "id": message.id,
            "content": message.content,
            "is_user": message.is_user,
            "timestamp": message.timestamp.isoformat(),
            "pipeline_data": pipeline_data.pipeline_data if pipeline_data else None
        }
        result.append(message_dict)
    
    logger.info(f"Retrieved {len(result)} messages with pipeline data for conversation {conversation_id}")
    return {"success": True, "messages": result}


@router.post("/analytics/homework/{conversation_id}", status_code=204)
def save_homework_items(conversation_id: int, payload: HomeworkItemsPayload, db: Session = Depends(get_db)):
    conv = db.query(Conversation).get(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    try:
        for item in payload.items:
            content = item.content
            if not content:
                continue
            db.add(LMHomework(
                user_id=conv.user_id,
                conversation_id_generated=conversation_id,
                content=content,
                status=(item.status or "Active")
            ))
        db.commit()
        return
    except Exception as e:
        logger.error(f"Error saving homework items for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving homework items: {str(e)}")


@router.post("/analytics/run-flows", status_code=202)
async def trigger_analytics_flows(payload: AnalyticsTriggerPayload):
    flow_list = payload.flows or flows_for_event(payload.event or MEMORY_GENERATION_EVENT)
    await enqueue_flows(payload.conversation_id, payload.event or MEMORY_GENERATION_EVENT, flow_list)
    return {"scheduled": flow_list}

@router.post("/analytics/knowledge-updater/{conversation_id}", status_code=204)
def save_knowledge_updates(conversation_id: int, payload: KnowledgeItemsPayload, db: Session = Depends(get_db)):
    conv = db.query(Conversation).get(conversation_id)
    print(payload)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    try:
        for item in payload.items:
            summary = item.summary
            if not summary:
                continue
            db.add(LMUserKnowledge(
                user_id=conv.user_id,
                conversation_id=conversation_id,
                summary=summary
            ))
        db.commit()
        return
    except Exception as e:
        logger.error(f"Error saving knowledge updates for conversation {conversation_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving knowledge updates: {str(e)}")