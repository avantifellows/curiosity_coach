from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import time

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
    """
    start_time = time.time()
    
    logger.info(
        f"list_conversations_for_user endpoint called - "
        f"user_id: {current_user.id}, limit: {limit}, offset: {offset}"
    )
    
    try:
        logger.debug(f"Fetching conversations from database - user_id: {current_user.id}")
        conversations = models.list_user_conversations(
            db=db, user_id=current_user.id, limit=limit, offset=offset
        )
        
        conversation_count = len(conversations)
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
                f"First conversation: {conversations[0].id if conversations else 'N/A'}"
            )
        
        return conversations # Pydantic will automatically convert based on ConversationSummary schema
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            f"list_conversations_for_user unexpected error - "
            f"user_id: {current_user.id}, error: {str(e)}, "
            f"processing_time: {processing_time:.3f}s"
        )
        raise HTTPException(status_code=500, detail=f"Error retrieving conversations: {str(e)}")

@router.post("", response_model=schemas.Conversation, status_code=status.HTTP_201_CREATED)
async def create_new_conversation(
    conversation_data: Optional[schemas.ConversationCreate] = None, # Allow empty body to use default title
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user), # Use the new dependency here too
):
    """
    Create a new conversation for the authenticated user.
    A title can optionally be provided in the request body.
    """
    start_time = time.time()
    
    title = conversation_data.title if conversation_data else "New Chat" # Use default if body is empty or title not provided
    
    logger.info(
        f"create_new_conversation endpoint called - "
        f"user_id: {current_user.id}, title: '{title}'"
    )
    
    try:
        logger.debug(f"Creating new conversation in database - user_id: {current_user.id}, title: '{title}'")
        conversation = models.create_conversation(
            db=db, user_id=current_user.id, title=title
        )
        
        processing_time = time.time() - start_time
        logger.info(
            f"create_new_conversation completed successfully - "
            f"user_id: {current_user.id}, conversation_id: {conversation.id}, "
            f"processing_time: {processing_time:.3f}s"
        )
        
        return conversation
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            f"create_new_conversation unexpected error - "
            f"user_id: {current_user.id}, title: '{title}', error: {str(e)}, "
            f"processing_time: {processing_time:.3f}s"
        )
        raise HTTPException(status_code=500, detail=f"Error creating conversation: {str(e)}")

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
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(
            f"update_conversation_title_endpoint unexpected error - "
            f"conversation_id: {conversation_id}, user_id: {current_user.id}, "
            f"error: {str(e)}, processing_time: {processing_time:.3f}s"
        )
        raise HTTPException(status_code=500, detail=f"Error updating conversation: {str(e)}") 