from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import time
import asyncio

from src.database import get_db
from src.models import User, Conversation # Assuming User model is needed for auth dependency
# TODO: Verify the correct import path and function name for auth dependency
from src.auth.dependencies import get_current_user # Use the new dependency that returns the User object
from src.conversations import schemas # Use the schemas we just created
from src import models # Import CRUD functions from models.py

# Set up logger for this module
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/conversations",
    tags=["conversations"],
    # dependencies=[Depends(get_current_active_user)], # Optional: Apply auth to all routes in this router
    responses={404: {"description": "Not found"}},
)

@router.get("", response_model=List[schemas.ConversationSummary])
async def list_conversations_for_user(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user), # Use the new dependency
    limit: int = Query(default=50, ge=1, le=200), # Add pagination
    offset: int = Query(default=0, ge=0)
):
    """
    Retrieve conversations for the authenticated user, ordered by most recently updated.
    Now includes visit_number for each conversation.
    """
    start_time = time.time()
    
    logger.info(
        f"list_conversations_for_user endpoint called - "
        f"user_id: {current_user.id}, limit: {limit}, offset: {offset}"
    )
    
    try:
        logger.debug(f"Fetching conversations with visit numbers from database - user_id: {current_user.id}")
        conversations_with_visits = models.get_user_conversations_with_visits(
            db=db, user_id=current_user.id, limit=limit, offset=offset
        )
        
        conversation_count = len(conversations_with_visits)
        processing_time = time.time() - start_time
        
        logger.info(
            f"list_conversations_for_user completed successfully - "
            f"user_id: {current_user.id}, conversation_count: {conversation_count}, "
            f"processing_time: {processing_time:.3f}s"
        )
        
        if conversation_count == 0:
            logger.debug(f"No conversations found for user_id: {current_user.id}")
        else:
            logger.debug(
                f"Retrieved {conversation_count} conversations for user_id: {current_user.id}. "
                f"First conversation: {conversations_with_visits[0]['id'] if conversations_with_visits else 'N/A'}"
            )
        
        return conversations_with_visits # Returns list of dicts with visit_number
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            f"list_conversations_for_user unexpected error - "
            f"user_id: {current_user.id}, error: {str(e)}, "
            f"processing_time: {processing_time:.3f}s"
        )
        raise HTTPException(status_code=500, detail=f"Error retrieving conversations: {str(e)}")

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_new_conversation(
    conversation_data: Optional[schemas.ConversationCreate] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks = Depends(),
):
    """
    Create a new conversation with visit tracking and onboarding preparation.
    
    Flow:
    1. Calculate visit number (conversation count + 1)
    2. Select appropriate prompt by purpose
    3. Create conversation and record visit
    4. Visit 2-3: Generate memories for all previous conversations
    5. Visit 4+: Ensure 3+ conversations with messages, generate persona if missing
    6. Generate AI opening message
    7. Return conversation with visit info and opening message
    
    On failure: Conversation is deleted and HTTP 503 is returned.
    """
    from sqlalchemy.exc import IntegrityError
    from src.onboarding.service import (
        generate_ai_first_message,
        ensure_memories_for_conversations,
        generate_persona_sync_with_retry
    )
    from src.onboarding.schemas import ConversationCreateResponse, ConversationWithVisit
    
    start_time = time.time()
    title = conversation_data.title if conversation_data else "New Chat"
    core_chat_theme = conversation_data.core_chat_theme if conversation_data else None
    print("core_chat_theme", core_chat_theme)
    preparation_status = "ready"
    ai_opening_message = None
    conversation = None
    
    try:
        # 1. Calculate visit number
        conversation_count = models.count_user_conversations(db, current_user.id)
        visit_number = conversation_count + 1
        
        logger.info(
            f"Visit {visit_number} started",
            extra={
                "user_id": current_user.id,
                "visit_number": visit_number,
                "memory_generation_required": visit_number >= 2,
                "persona_generation_required": visit_number >= 4,
                "timestamp": time.time()
            }
        )
        
        # 2. Select appropriate prompt by purpose
        prompt_purpose = models.select_prompt_purpose_for_visit(visit_number)
        logger.info(f"🎯 BACKEND: Visit {visit_number} → prompt_purpose={prompt_purpose}")
        
        prompt_version = models.get_production_prompt_by_purpose(db, prompt_purpose)
        
        if prompt_version:
            prompt = db.query(models.Prompt).get(prompt_version.prompt_id)
            logger.info(f"✅ BACKEND: Found prompt_version - id={prompt_version.id}, version_number={prompt_version.version_number}, prompt_name={prompt.name if prompt else 'Unknown'}, prompt_purpose={prompt.prompt_purpose if prompt else 'Unknown'}")
        else:
            logger.warning(f"⚠️ BACKEND: NO prompt_version found for purpose={prompt_purpose}!")
        
        # 3. Create conversation and record visit (with race condition protection)
        conversation = models.create_conversation(
            db=db,
            user_id=current_user.id,
            title=title,
            core_chat_theme=core_chat_theme,
            prompt_version_id=prompt_version.id if prompt_version else None
        )
        
        logger.info(f"📝 BACKEND: Created conversation id={conversation.id} with prompt_version_id={conversation.prompt_version_id}")
        
        # Record visit number with unique constraint protection
        try:
            models.record_conversation_visit(db, conversation.id, current_user.id, visit_number)
            db.commit()
        except IntegrityError:
            # Race condition detected: another request assigned same visit number
            db.rollback()
            logger.warning(f"Race condition detected for user {current_user.id}, retrying with updated visit number")
            
            # Recalculate and retry
            conversation_count = models.count_user_conversations(db, current_user.id)
            visit_number = conversation_count + 1
            
            # Try again with updated visit number
            models.record_conversation_visit(db, conversation.id, current_user.id, visit_number)
            db.commit()
            
            logger.info(f"Race condition resolved, assigned visit_number: {visit_number}")
        
        # 4. Handle visit-specific requirements (OUTSIDE transaction for long operations)
        if visit_number >= 2 and visit_number <= 3:
            preparation_status = "ready"
            logger.info(f"Queuing memory generation for all previous conversations (visit {visit_number})")

            # Queue memory generation as background task - don't block the endpoint
            # Memory will be ready for follow-up messages even if not for opening message
            background_tasks.add_task(
                ensure_memories_for_conversations,
                db=db,
                user_id=current_user.id,
                exclude_conversation_id=conversation.id
            )
            logger.info("Memory generation queued as background task")
        
        elif visit_number >= 4:
            preparation_status = "generating_persona"
            logger.info(f"Visit {visit_number}: Checking persona requirements")
            
            # FIRST: Ensure memories exist for at least 3 conversations with messages
            all_conversations = models.get_user_conversations_list(db, current_user.id)
            previous_conversations = [c for c in all_conversations if c.id != conversation.id]
            
            conversations_with_messages = [
                c for c in previous_conversations
                if models.has_messages(db, c.id)
            ]
            
            if len(conversations_with_messages) < 3:
                logger.error(
                    f"User {current_user.id} has only {len(conversations_with_messages)} conversations with messages. "
                    f"Persona requires at least 3."
                )
                raise HTTPException(
                    status_code=503,
                    detail="Unable to prepare your personalized experience. Please ensure you have completed at least 3 conversations with messages."
                )
            
            # Queue memory generation as background task
            logger.info(f"Queuing memory generation for visit {visit_number}")
            background_tasks.add_task(
                ensure_memories_for_conversations,
                db=db,
                user_id=current_user.id,
                exclude_conversation_id=conversation.id
            )

            # Check if persona exists, generate if needed
            persona = db.query(models.UserPersona).filter(
                models.UserPersona.user_id == current_user.id
            ).first()

            if not persona:
                logger.info(f"Queuing persona generation for user {current_user.id}")
                # Queue persona generation as background task
                background_tasks.add_task(
                    generate_persona_sync_with_retry,
                    user_id=current_user.id,
                    db=db,
                    max_retries=2
                )
            else:
                logger.info(f"Persona already exists for user {current_user.id}")
        
        # 6. Generate AI's opening message
        preparation_status = "ready"
        logger.info(f"Generating opening message for conversation {conversation.id}")
        
        ai_opening_message = await generate_ai_first_message(
            conversation_id=conversation.id,
            user_id=current_user.id,
            visit_number=visit_number,
            db=db
        )
        
        logger.info(f"Opening message generated successfully")
        
        # 7. Return conversation with visit info
        processing_time = time.time() - start_time
        logger.info(
            f"Conversation creation completed successfully",
            extra={
                "conversation_id": conversation.id,
                "user_id": current_user.id,
                "visit_number": visit_number,
                "total_duration_ms": processing_time * 1000,
                "success": True
            }
        )
        
        # Build response with visit number
        conversation_with_visit = ConversationWithVisit(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            visit_number=visit_number,
            prompt_version_id=conversation.prompt_version_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )
        
        response = ConversationCreateResponse(
            conversation=conversation_with_visit,
            visit_number=visit_number,
            ai_opening_message=ai_opening_message,
            preparation_status="ready",
            requires_opening_message=True
        )
        
        return response
        
    except (TimeoutError, HTTPException) as e:
        # Clean up: delete the conversation if preparation fails
        processing_time = time.time() - start_time
        
        if conversation:
            try:
                logger.warning(f"Cleaning up conversation {conversation.id} due to preparation failure")
                db.delete(conversation)
                db.commit()
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up conversation: {cleanup_error}")
                db.rollback()
        
        if isinstance(e, HTTPException):
            logger.error(
                f"Conversation preparation failed with HTTP error",
                extra={
                    "user_id": current_user.id,
                    "status_code": e.status_code,
                    "detail": e.detail,
                    "processing_time_ms": processing_time * 1000
                }
            )
            raise e
        
        # TimeoutError
        logger.error(
            f"Conversation preparation timed out",
            extra={
                "user_id": current_user.id,
                "error": str(e),
                "processing_time_ms": processing_time * 1000
            }
        )
        raise HTTPException(
            status_code=503,
            detail="Unable to prepare your conversation at this time. Please try again in a moment."
        )
        
    except Exception as e:
        # Unexpected error - also clean up
        processing_time = time.time() - start_time
        
        if conversation:
            try:
                logger.warning(f"Cleaning up conversation {conversation.id} due to unexpected error")
                db.delete(conversation)
                db.commit()
            except Exception as cleanup_error:
                logger.error(f"Error cleaning up conversation: {cleanup_error}")
                db.rollback()
        
        logger.error(
            f"create_new_conversation unexpected error",
            extra={
                "user_id": current_user.id,
                "title": title,
                "error": str(e),
                "processing_time_ms": processing_time * 1000
            }
        )
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

@router.get("/{conversation_id}", response_model=schemas.Conversation)
async def get_conversation_by_id(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve a specific conversation by its ID for the authenticated user.
    Now includes visit_number.
    """
    logger.info(
        f"get_conversation_by_id endpoint called - "
        f"user_id: {current_user.id}, conversation_id: {conversation_id}"
    )
    
    conversation_with_visit = models.get_conversation_with_visit(db=db, conversation_id=conversation_id)

    if conversation_with_visit is None:
        logger.warning(f"Conversation not found - conversation_id: {conversation_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conversation_with_visit["user_id"] != current_user.id:
        logger.error(
            f"User {current_user.id} not authorized to view conversation {conversation_id} "
            f"owned by user {conversation_with_visit['user_id']}"
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this conversation")
    
    logger.info(
        f"get_conversation_by_id completed successfully - "
        f"user_id: {current_user.id}, conversation_id: {conversation_with_visit['id']}"
    )
    return conversation_with_visit

@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation_by_id(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a conversation by its ID for the authenticated user.
    """
    logger.info(
        f"delete_conversation_by_id endpoint called - "
        f"user_id: {current_user.id}, conversation_id: {conversation_id}"
    )

    success = models.delete_conversation(
        db=db, conversation_id=conversation_id, user_id=current_user.id
    )

    if not success:
        logger.warning(
            f"Failed to delete conversation. It might not exist or user does not have permission - "
            f"user_id: {current_user.id}, conversation_id: {conversation_id}"
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found or not authorized to delete")

    logger.info(
        f"delete_conversation_by_id completed successfully - "
        f"user_id: {current_user.id}, conversation_id: {conversation_id}"
    )
    return

@router.put("/{conversation_id}/title", response_model=schemas.Conversation)
async def update_conversation_title_endpoint(
    conversation_id: int,
    payload: schemas.ConversationTitleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the title of a specific conversation for the authenticated user.
    """
    start_time = time.time()
    
    logger.info(
        f"update_conversation_title_endpoint called - "
        f"user_id: {current_user.id}, conversation_id: {conversation_id}, "
        f"new_title: '{payload.title}'"
    )
    
    try:
        logger.debug(f"Updating conversation title in database - conversation_id: {conversation_id}")
        updated_conversation = models.update_conversation_title(
            db=db,
            conversation_id=conversation_id,
            new_title=payload.title,
            user_id=current_user.id
        )

        if updated_conversation is None:
            logger.warning(
                f"Failed to update conversation title - conversation_id: {conversation_id}, "
                f"user_id: {current_user.id}, title: '{payload.title}'"
            )
            
            # Attempt to fetch the conversation to see if it exists but belongs to another user or if title was invalid
            logger.debug(f"Checking if conversation exists - conversation_id: {conversation_id}")
            conversation_check = models.get_conversation(db, conversation_id)
            if not conversation_check:
                logger.error(f"Conversation not found - conversation_id: {conversation_id}")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
            # If it exists, but update_conversation_title returned None, it means it was an auth issue or invalid title
            # The models.update_conversation_title has checks for empty title and user_id match
            # We can refine this error reporting if needed, e.g. by having update_conversation_title raise specific exceptions.
            # For now, a generic 403 or 400 depending on what we assume failed.
            # If title was empty, pydantic model constr should catch it, but as a fallback:
            if not payload.title.strip(): # This check is also in ConversationTitleUpdate via constr
                logger.error(f"Empty title provided - conversation_id: {conversation_id}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title cannot be empty")
            # If it got here, it's likely an authorization issue or an unexpected None from the update function
            logger.error(
                f"Authorization or input error - conversation_id: {conversation_id}, "
                f"user_id: {current_user.id}"
            )
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this conversation or invalid input")

        processing_time = time.time() - start_time
        logger.info(
            f"update_conversation_title_endpoint completed successfully - "
            f"conversation_id: {conversation_id}, new_title: '{payload.title}', "
            f"processing_time: {processing_time:.3f}s"
        )

        return updated_conversation
        
    except HTTPException as he:
        processing_time = time.time() - start_time
        logger.warning(
            f"update_conversation_title_endpoint HTTP error - "
            f"conversation_id: {conversation_id}, user_id: {current_user.id}, "
            f"status_code: {he.status_code}, detail: {he.detail}, "
            f"processing_time: {processing_time:.3f}s"
        )
        raise he
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            f"update_conversation_title_endpoint unexpected error - "
            f"conversation_id: {conversation_id}, user_id: {current_user.id}, "
            f"error: {str(e)}, "
            f"processing_time: {processing_time:.3f}s"
        )
        raise HTTPException(status_code=500, detail=f"Error updating conversation title: {str(e)}")

@router.get("/{conversation_id}/memory", response_model=dict)
async def get_conversation_memory_endpoint(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the AI-generated memory for a specific conversation.
    """
    logger.info(
        f"get_conversation_memory_endpoint called - "
        f"user_id: {current_user.id}, conversation_id: {conversation_id}"
    )

    # First, verify the user has access to the conversation
    conversation = models.get_conversation(db=db, conversation_id=conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this conversation")

    # Fetch the memory
    memory = models.get_memory_for_conversation(db=db, conversation_id=conversation_id)

    if not memory:
        logger.warning(f"No memory found for conversation_id: {conversation_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found for this conversation")

    logger.info(
        f"get_conversation_memory_endpoint completed successfully - "
        f"conversation_id: {conversation_id}"
    )
    return memory.memory_data 


@router.put("/{conversation_id}/core-chat-theme", response_model=schemas.Conversation)
async def update_conversation_core_chat_theme(
    conversation_id: int,
    payload: schemas.ConversationCoreChatThemeUpdate,  # You'd need to create this schema
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the core chat theme of a specific conversation for the authenticated user.
    """
    start_time = time.time()
    
    logger.info(
        f"update_conversation_core_chat_theme called - "
        f"user_id: {current_user.id}, conversation_id: {conversation_id}, "
        f"new_core_chat_theme: '{payload.core_chat_theme}'"
    )
    
    try:
        logger.debug(f"Updating conversation core chat theme in database - conversation_id: {conversation_id}")
        updated_conversation = models.update_conversation_core_chat_theme(
            db=db,
            conversation_id=conversation_id,
            new_core_chat_theme=payload.core_chat_theme,
            user_id=current_user.id
        )
        
        if updated_conversation is None:
            logger.warning(
                f"Failed to update conversation core chat theme - conversation_id: {conversation_id}, "
                f"user_id: {current_user.id}, core_chat_theme: '{payload.core_chat_theme}'"
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        
        processing_time = time.time() - start_time
        logger.info(
            f"update_conversation_core_chat_theme completed successfully - "
            f"conversation_id: {conversation_id}, new_core_chat_theme: '{payload.core_chat_theme}', "
            f"processing_time: {processing_time:.3f}s"
        )   
        return updated_conversation
    except HTTPException as he:
        processing_time = time.time() - start_time
        logger.warning(
            f"update_conversation_core_chat_theme HTTP error - "
            f"conversation_id: {conversation_id}, user_id: {current_user.id}, "
            f"status_code: {he.status_code}, detail: {he.detail}, "
            f"processing_time: {processing_time:.3f}s"
        )
        raise he
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            f"update_conversation_core_chat_theme unexpected error - "
            f"conversation_id: {conversation_id}, user_id: {current_user.id}, "
            f"error: {str(e)}, "
            f"processing_time: {processing_time:.3f}s"
        )
        raise HTTPException(status_code=500, detail=f"Error updating conversation core chat theme: {str(e)}")