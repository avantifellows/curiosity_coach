from fastapi import APIRouter, HTTPException, Depends, Body, status
import traceback
import logging
import time
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any # Added List and Dict
from src.messages.schemas import MessageRequest, MessageData, ChatHistoryResponse, SendMessageResponse, BrainResponsePayload # Removed unused MessageResponse
from src.messages.service import message_service
# Import necessary models and CRUD functions
from src import models 
from src.models import User, Conversation, Message # Import User for auth, Conversation/Message for lookups
# --- TODO: Verify correct auth dependency --- 
from src.auth.dependencies import get_current_user # Changed from get_user_id
# --- End auth dependency --- 
from src.database import get_db
import json
from datetime import datetime
import os

logger = logging.getLogger(__name__)

router = APIRouter(
    # Prefix remains /api/messages for now, but routes below are more specific
    prefix="/api", 
    tags=["messages"]
)

# --- Helper function for conversation verification --- 
async def verify_conversation_ownership(conversation_id: int, current_user: User, db: Session) -> Conversation:
    logger.debug(f"verify_conversation_ownership called - conversation_id: {conversation_id}, user_id: {current_user.id}")
    
    conversation = models.get_conversation(db, conversation_id)
    if not conversation:
        logger.warning(f"Conversation not found during ownership verification - conversation_id: {conversation_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    
    if conversation.user_id != current_user.id:
        logger.warning(
            f"Unauthorized conversation access attempt - conversation_id: {conversation_id}, "
            f"requesting_user_id: {current_user.id}, owner_user_id: {conversation.user_id}"
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this conversation")
    
    logger.debug(f"Conversation ownership verified successfully - conversation_id: {conversation_id}")
    return conversation
# --- End helper --- 

@router.post("/conversations/{conversation_id}/messages", response_model=SendMessageResponse)
async def send_message_to_conversation(
    conversation_id: int, # Added conversation_id path parameter
    request: MessageRequest, # Body now only contains content and optional purpose
    current_user: User = Depends(get_current_user), # Changed to get_current_user
    db: Session = Depends(get_db)
):
    """
    Accepts a user message for a specific conversation, saves it, 
    and triggers asynchronous AI response generation.
    Returns the saved user message immediately.
    """
    start_time = time.time()
    
    logger.info(
        f"send_message_to_conversation endpoint called - "
        f"user_id: {current_user.id}, conversation_id: {conversation_id}, "
        f"purpose: {request.purpose}, content_length: {len(request.content)}"
    )
    
    logger.debug(f"Request content preview: {request.content[:100]}{'...' if len(request.content) > 100 else ''}")
    
    try:
        # Verify user owns the conversation
        logger.debug(f"Verifying conversation ownership - conversation_id: {conversation_id}, user_id: {current_user.id}")
        await verify_conversation_ownership(conversation_id, current_user, db)
        logger.info(f"Conversation ownership verified successfully - conversation_id: {conversation_id}")
        
        content = request.content
        purpose = request.purpose # Still optional
        user_id = current_user.id # Get user_id from authenticated user

        logger.debug(f"Calling message service to send message - conversation_id: {conversation_id}")
        saved_message = await message_service.send_message(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
            purpose=purpose,
            db=db
        )
        
        processing_time = time.time() - start_time
        logger.info(
            f"send_message_to_conversation completed successfully - "
            f"message_id: {saved_message.get('id')}, processing_time: {processing_time:.3f}s"
        )
        
        return {
            'success': True,
            'message': MessageData.model_validate(saved_message)
        }
    except HTTPException as he:
        processing_time = time.time() - start_time
        logger.warning(
            f"send_message_to_conversation HTTP error - conversation_id: {conversation_id}, "
            f"user_id: {current_user.id}, status_code: {he.status_code}, "
            f"detail: {he.detail}, processing_time: {processing_time:.3f}s"
        )
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        error_details = traceback.format_exc()
        logger.error(
            f"send_message_to_conversation unexpected error - conversation_id: {conversation_id}, "
            f"user_id: {current_user.id}, error: {str(e)}, processing_time: {processing_time:.3f}s"
        )
        logger.error(f"Error traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")

@router.get("/conversations/{conversation_id}/messages", response_model=ChatHistoryResponse)
async def get_conversation_messages(
    conversation_id: int, # Added conversation_id path parameter
    current_user: User = Depends(get_current_user), # Changed to get_current_user
    db: Session = Depends(get_db)
):
    """
    Get message history for a specific conversation owned by the authenticated user.
    """
    start_time = time.time()
    
    logger.info(
        f"get_conversation_messages endpoint called - "
        f"user_id: {current_user.id}, conversation_id: {conversation_id}"
    )
    
    try:
        # Verify user owns the conversation
        logger.debug(f"Verifying conversation ownership - conversation_id: {conversation_id}, user_id: {current_user.id}")
        await verify_conversation_ownership(conversation_id, current_user, db)
        logger.info(f"Conversation ownership verified successfully - conversation_id: {conversation_id}")
        
        user_id = current_user.id # For logging or potential use in service

        logger.debug(f"Calling message service to get chat history - conversation_id: {conversation_id}")
        messages = await message_service.get_chat_history(
            conversation_id=conversation_id,
            db=db
        )
        
        processing_time = time.time() - start_time
        logger.info(
            f"get_conversation_messages completed successfully - "
            f"conversation_id: {conversation_id}, message_count: {len(messages)}, "
            f"processing_time: {processing_time:.3f}s"
        )
        
        return {
            'success': True,
            'messages': messages
        }
    except HTTPException as he:
        processing_time = time.time() - start_time
        logger.warning(
            f"get_conversation_messages HTTP error - conversation_id: {conversation_id}, "
            f"user_id: {current_user.id}, status_code: {he.status_code}, "
            f"detail: {he.detail}, processing_time: {processing_time:.3f}s"
        )
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        error_details = traceback.format_exc()
        logger.error(
            f"get_conversation_messages unexpected error - conversation_id: {conversation_id}, "
            f"user_id: {current_user.id}, error: {str(e)}, processing_time: {processing_time:.3f}s"
        )
        logger.error(f"Error traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error retrieving messages: {str(e)}")

@router.get("/messages/{user_message_id}/response", response_model=Optional[MessageData], responses={202: {"description": "AI response is pending"}})
async def get_ai_response(
    user_message_id: int,
    current_user: User = Depends(get_current_user), # Changed to get_current_user
    db: Session = Depends(get_db)
):
    """
    Poll for the AI response corresponding to a specific user message.
    Verifies the user owns the conversation the message belongs to.
    """
    start_time = time.time()
    
    logger.info(
        f"get_ai_response endpoint called - "
        f"user_id: {current_user.id}, user_message_id: {user_message_id}"
    )
    
    try:
        # Fetch the AI response based on the user message it replies to
        logger.debug(f"Fetching AI response for user_message_id: {user_message_id}")
        ai_response = models.get_ai_response_for_user_message(db=db, user_message_id=user_message_id)

        if ai_response:
            logger.debug(f"AI response found - response_id: {ai_response.id}, conversation_id: {ai_response.conversation_id}")
            
            # Verify the user owns the conversation this AI response belongs to
            try:
                logger.debug(f"Verifying conversation ownership for AI response - conversation_id: {ai_response.conversation_id}")
                await verify_conversation_ownership(ai_response.conversation_id, current_user, db)
                logger.info(f"AI response access authorized - response_id: {ai_response.id}")
            except HTTPException as he:
                # If ownership fails, treat it as if the response wasn't found for this user
                logger.warning(
                    f"Unauthorized AI response access attempt - user_id: {current_user.id}, "
                    f"response_id: {ai_response.id}, user_message_id: {user_message_id}, "
                    f"conversation_id: {ai_response.conversation_id}"
                )
                return None # Return None instead of 403/404 to indicate polling should continue/stop
            
            # If ownership verified, return the data
            processing_time = time.time() - start_time
            logger.info(
                f"get_ai_response completed successfully - response_id: {ai_response.id}, "
                f"processing_time: {processing_time:.3f}s"
            )
            return MessageData.model_validate(ai_response)
        else:
            processing_time = time.time() - start_time
            logger.debug(
                f"No AI response found yet for user_message_id: {user_message_id}, "
                f"processing_time: {processing_time:.3f}s"
            )
            return None

    except Exception as e:
        processing_time = time.time() - start_time
        error_details = traceback.format_exc()
        logger.error(
            f"get_ai_response unexpected error - user_message_id: {user_message_id}, "
            f"user_id: {current_user.id}, error: {str(e)}, processing_time: {processing_time:.3f}s"
        )
        logger.error(f"Error traceback: {error_details}")
        raise HTTPException(status_code=500, detail="Error retrieving AI response")

# Internal route for Brain service callback
@router.post("/internal/brain_response", status_code=status.HTTP_202_ACCEPTED)
async def receive_brain_response(payload: BrainResponsePayload, db: Session = Depends(get_db)):
    """
    Receives the processed response from the Brain service and saves it 
    to the correct conversation.
    """
    start_time = time.time()
    
    logger.info(
        f"receive_brain_response endpoint called - "
        f"conversation_id: {payload.conversation_id}, user_id: {payload.user_id}, "
        f"original_message_id: {payload.original_message_id}, "
        f"response_length: {len(payload.llm_response) if payload.llm_response else 0}"
    )
    
    logger.debug(f"Brain response preview: {payload.llm_response[:100] if payload.llm_response else 'None'}{'...' if payload.llm_response and len(payload.llm_response) > 100 else ''}")
    
    try:
        # Verify the target conversation exists (optional but good practice)
        logger.debug(f"Verifying conversation exists - conversation_id: {payload.conversation_id}")
        conversation = models.get_conversation(db, payload.conversation_id)
        if not conversation:
            logger.error(f"Brain response received for non-existent conversation_id: {payload.conversation_id}")
            raise HTTPException(status_code=404, detail=f"Conversation {payload.conversation_id} not found.")
        
        logger.info(f"Conversation verified successfully - conversation_id: {payload.conversation_id}")
        
        # Update conversation's prompt_version_id if provided
        if payload.prompt_version_id is not None:
            logger.info(f"🔄 BACKEND: Brain wants to update prompt_version_id from {conversation.prompt_version_id} to {payload.prompt_version_id}")
            conversation.prompt_version_id = payload.prompt_version_id
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            logger.info(f"✅ BACKEND: Updated conversation with prompt_version_id: {payload.prompt_version_id}")
        else:
            logger.info(f"✅ BACKEND: Keeping existing prompt_version_id={conversation.prompt_version_id} (Brain didn't request update)")
            
        pipeline_data_to_save = None
        if payload.pipeline_data:
            logger.debug(f"Processing pipeline data - keys: {list(payload.pipeline_data.keys())}")
            pipeline_data_to_save = payload.pipeline_data.copy() # Create a copy to modify
            pipeline_data_to_save.pop('query', None) # Remove 'query' if it exists

        logger.debug(f"Saving brain response message - conversation_id: {payload.conversation_id}")
        saved_response = models.save_message(
            db=db,
            conversation_id=payload.conversation_id, # Use conversation_id from payload
            content=payload.llm_response, # Use llm_response from the payload
            is_user=False,
            responds_to_message_id=payload.original_message_id,
            curiosity_score=payload.curiosity_score,
        )
        logger.info(f"Brain response message saved successfully - message_id: {saved_response.id}")

        if pipeline_data_to_save: # This is the filtered data from before
            logger.debug(f"Saving pipeline data for message_id: {saved_response.id}")
            models.save_message_pipeline_data(
                db=db,
                message_id=saved_response.id, 
                pipeline_data_dict=pipeline_data_to_save
            )
            logger.info(f"Pipeline data saved successfully for message_id: {saved_response.id}")

        processing_time = time.time() - start_time
        logger.info(
            f"receive_brain_response completed successfully - "
            f"message_id: {saved_response.id}, processing_time: {processing_time:.3f}s"
        )

        return {"status": "received", "message_id": saved_response.id}

    except HTTPException as he:
        processing_time = time.time() - start_time
        logger.warning(
            f"receive_brain_response HTTP error - conversation_id: {payload.conversation_id}, "
            f"status_code: {he.status_code}, detail: {he.detail}, "
            f"processing_time: {processing_time:.3f}s"
        )
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        error_details = traceback.format_exc()
        logger.error(
            f"receive_brain_response unexpected error - conversation_id: {payload.conversation_id}, "
            f"error: {str(e)}, processing_time: {processing_time:.3f}s"
        )
        logger.error(f"Error traceback: {error_details}")
        raise HTTPException(status_code=500, detail="Error saving brain response")

# ---- New Endpoint for AI Response Pipeline Steps ----
@router.get("/messages/{ai_message_id}/pipeline_steps",
            response_model=List[Dict[str, Any]], # Assuming steps are a list of dictionaries
            summary="Get AI response pipeline steps",
            tags=["messages"])
async def get_ai_response_pipeline_steps(
    ai_message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user) # Ensure user is authenticated
):
    """
    Retrieves the pipeline steps for a given AI message ID.
    The message must be an AI response and belong to one of the current user's conversations.
    """
    start_time = time.time()
    
    logger.info(
        f"get_ai_response_pipeline_steps endpoint called - "
        f"user_id: {current_user.id}, ai_message_id: {ai_message_id}"
    )
    
    try:
        # Fetch the AI message to verify existence and ownership
        logger.debug(f"Fetching AI message - ai_message_id: {ai_message_id}")
        ai_message = db.query(models.Message).filter(
            models.Message.id == ai_message_id,
            models.Message.is_user == False  # Ensure it's an AI message
        ).first()

        if not ai_message:
            logger.warning(f"AI message not found - ai_message_id: {ai_message_id}")
            raise HTTPException(status_code=404, detail=f"AI message with ID {ai_message_id} not found.")

        logger.debug(f"AI message found - ai_message_id: {ai_message_id}, conversation_id: {ai_message.conversation_id}")

        # Verify that the conversation belongs to the current user
        logger.debug(f"Verifying conversation ownership for pipeline steps - conversation_id: {ai_message.conversation_id}")
        conversation = models.get_conversation(db, ai_message.conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            # This case should ideally not happen if AI message is correctly linked,
            # but good for an explicit security check.
            logger.warning(
                f"Unauthorized pipeline steps access attempt - user_id: {current_user.id}, "
                f"ai_message_id: {ai_message_id}, conversation_id: {ai_message.conversation_id}"
            )
            raise HTTPException(status_code=403, detail="Access forbidden: Conversation does not belong to the current user.")

        logger.info(f"Pipeline steps access authorized - ai_message_id: {ai_message_id}")

        # Fetch the pipeline data for the AI message
        logger.debug(f"Fetching pipeline data - ai_message_id: {ai_message_id}")
        pipeline_data_entry = db.query(models.MessagePipelineData).filter(
            models.MessagePipelineData.message_id == ai_message_id
        ).first()

        if not pipeline_data_entry or not pipeline_data_entry.pipeline_data:
            # If there's no pipeline data entry or the data itself is null/empty
            logger.debug(f"No pipeline data found for ai_message_id: {ai_message_id}")
            processing_time = time.time() - start_time
            logger.info(
                f"get_ai_response_pipeline_steps completed (empty result) - "
                f"ai_message_id: {ai_message_id}, processing_time: {processing_time:.3f}s"
            )
            return [] # Return an empty list as per requirement if steps are not found or data is missing

        # Extract the 'steps' array from the JSONB field
        # The pipeline_data is already a dict because SQLAlchemy handles JSONB deserialization
        steps = pipeline_data_entry.pipeline_data.get("steps")

        if steps is None or not isinstance(steps, list):
            # If 'steps' key doesn't exist or is not a list, return empty list
            logger.debug(f"Pipeline data exists but no valid steps array - ai_message_id: {ai_message_id}")
            processing_time = time.time() - start_time
            logger.info(
                f"get_ai_response_pipeline_steps completed (no valid steps) - "
                f"ai_message_id: {ai_message_id}, processing_time: {processing_time:.3f}s"
            )
            return []
        
        processing_time = time.time() - start_time
        step_count = len(steps) if isinstance(steps, list) else 0
        logger.info(
            f"get_ai_response_pipeline_steps completed successfully - "
            f"ai_message_id: {ai_message_id}, step_count: {step_count}, "
            f"processing_time: {processing_time:.3f}s"
        )
        
        return steps
        
    except HTTPException as he:
        processing_time = time.time() - start_time
        logger.warning(
            f"get_ai_response_pipeline_steps HTTP error - ai_message_id: {ai_message_id}, "
            f"user_id: {current_user.id}, status_code: {he.status_code}, "
            f"detail: {he.detail}, processing_time: {processing_time:.3f}s"
        )
        raise
    except Exception as e:
        processing_time = time.time() - start_time
        error_details = traceback.format_exc()
        logger.error(
            f"get_ai_response_pipeline_steps unexpected error - ai_message_id: {ai_message_id}, "
            f"user_id: {current_user.id}, error: {str(e)}, processing_time: {processing_time:.3f}s"
        )
        logger.error(f"Error traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error retrieving pipeline steps: {str(e)}")
# ---- End of New Endpoint ----

# New internal endpoint for Brain service
@router.get("/internal/conversations/{conversation_id}/messages_for_brain", response_model=ChatHistoryResponse, tags=["internal"])
async def get_conversation_messages_for_brain(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    Internal endpoint for the Brain service to get message history for a specific conversation.
    This endpoint does not perform user ownership checks.
    """
    start_time = time.time()
    
    logger.info(
        f"get_conversation_messages_for_brain (internal) endpoint called - "
        f"conversation_id: {conversation_id}"
    )
    
    try:
        logger.debug(f"Calling message service for brain - conversation_id: {conversation_id}")
        messages = await message_service.get_chat_history(
            conversation_id=conversation_id,
            db=db
        )
        
        processing_time = time.time() - start_time
        logger.info(
            f"get_conversation_messages_for_brain completed successfully - "
            f"conversation_id: {conversation_id}, message_count: {len(messages)}, "
            f"processing_time: {processing_time:.3f}s"
        )
        
        return {
            'success': True,
            'messages': messages
        }
    except Exception as e:
        processing_time = time.time() - start_time
        error_details = traceback.format_exc()
        logger.error(
            f"get_conversation_messages_for_brain unexpected error - "
            f"conversation_id: {conversation_id}, error: {str(e)}, "
            f"processing_time: {processing_time:.3f}s"
        )
        logger.error(f"Error traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error retrieving messages for Brain: {str(e)}")
