from fastapi import APIRouter, HTTPException, Depends, Body, status
import traceback
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

router = APIRouter(
    # Prefix remains /api/messages for now, but routes below are more specific
    prefix="/api", 
    tags=["messages"]
)

# --- Helper function for conversation verification --- 
async def verify_conversation_ownership(conversation_id: int, current_user: User, db: Session) -> Conversation:
    conversation = models.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conversation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this conversation")
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
    # Verify user owns the conversation
    await verify_conversation_ownership(conversation_id, current_user, db)
    
    content = request.content
    purpose = request.purpose # Still optional
    user_id = current_user.id # Get user_id from authenticated user

    try:
        saved_message = await message_service.send_message(
            user_id=user_id,
            conversation_id=conversation_id,
            content=content,
            purpose=purpose,
            db=db
        )
        
        return {
            'success': True,
            'message': MessageData.model_validate(saved_message)
        }
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Router: Error in send_message for conversation_id: {conversation_id}. Error: {e}")
        print(f"Router: Error traceback: {error_details}")
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
    # Verify user owns the conversation
    await verify_conversation_ownership(conversation_id, current_user, db)
    user_id = current_user.id # For logging or potential use in service

    try:
        messages = await message_service.get_chat_history(
            conversation_id=conversation_id,
            db=db
        )
        return {
            'success': True,
            'messages': messages
        }
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error getting messages for conversation {conversation_id}: {e}")
        print(f"Error traceback: {error_details}")
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
    try:
        # Fetch the AI response based on the user message it replies to
        ai_response = models.get_ai_response_for_user_message(db=db, user_message_id=user_message_id)

        if ai_response:
            # Verify the user owns the conversation this AI response belongs to
            try:
                await verify_conversation_ownership(ai_response.conversation_id, current_user, db)
            except HTTPException as he:
                # If ownership fails, treat it as if the response wasn't found for this user
                print(f"Auth Error: User {current_user.id} tried to access AI response {ai_response.id} for message {user_message_id} in conversation {ai_response.conversation_id} which they don't own.")
                return None # Return None instead of 403/404 to indicate polling should continue/stop
            
            # If ownership verified, return the data
            return MessageData.model_validate(ai_response)
        else:
            return None

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error fetching AI response for user message {user_message_id}: {e}")
        print(f"Error details: {error_details}")
        raise HTTPException(status_code=500, detail="Error retrieving AI response")

# Internal route for Brain service callback
@router.post("/internal/brain_response", status_code=status.HTTP_202_ACCEPTED)
async def receive_brain_response(payload: BrainResponsePayload, db: Session = Depends(get_db)):
    """
    Receives the processed response from the Brain service and saves it 
    to the correct conversation.
    """
    try:
        # Verify the target conversation exists (optional but good practice)
        conversation = models.get_conversation(db, payload.conversation_id)
        if not conversation:
            print(f"Error: Brain response received for non-existent conversation_id: {payload.conversation_id}")
            raise HTTPException(status_code=404, detail=f"Conversation {payload.conversation_id} not found.")
            
        pipeline_data_to_save = None
        if payload.pipeline_data:
            pipeline_data_to_save = payload.pipeline_data.copy() # Create a copy to modify
            pipeline_data_to_save.pop('query', None) # Remove 'query' if it exists
            pipeline_data_to_save.pop('final_response', None) # Remove 'final_response' if it exists

        saved_response = models.save_message(
            db=db,
            conversation_id=payload.conversation_id, # Use conversation_id from payload
            content=payload.llm_response, # Use llm_response from the payload
            is_user=False,
            responds_to_message_id=payload.original_message_id,
        )
        print(f"Saved brain response with ID: {saved_response.id} to conversation ID: {payload.conversation_id}")

        if pipeline_data_to_save: # This is the filtered data from before
            models.save_message_pipeline_data(
                db=db,
                message_id=saved_response.id, 
                pipeline_data_dict=pipeline_data_to_save
            )
            print(f"Saved pipeline data for message ID: {saved_response.id}")

        return {"status": "received", "message_id": saved_response.id}

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error processing brain response for conversation {payload.conversation_id}: {e}")
        print(f"Error details: {error_details}")
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
    # Fetch the AI message to verify existence and ownership
    ai_message = db.query(models.Message).filter(
        models.Message.id == ai_message_id,
        models.Message.is_user == False  # Ensure it's an AI message
    ).first()

    if not ai_message:
        raise HTTPException(status_code=404, detail=f"AI message with ID {ai_message_id} not found.")

    # Verify that the conversation belongs to the current user
    conversation = models.get_conversation(db, ai_message.conversation_id)
    if not conversation or conversation.user_id != current_user.id:
        # This case should ideally not happen if AI message is correctly linked,
        # but good for an explicit security check.
        raise HTTPException(status_code=403, detail="Access forbidden: Conversation does not belong to the current user.")

    # Fetch the pipeline data for the AI message
    pipeline_data_entry = db.query(models.MessagePipelineData).filter(
        models.MessagePipelineData.message_id == ai_message_id
    ).first()

    if not pipeline_data_entry or not pipeline_data_entry.pipeline_data:
        # If there's no pipeline data entry or the data itself is null/empty
        return [] # Return an empty list as per requirement if steps are not found or data is missing

    # Extract the 'steps' array from the JSONB field
    # The pipeline_data is already a dict because SQLAlchemy handles JSONB deserialization
    steps = pipeline_data_entry.pipeline_data.get("steps")

    if steps is None or not isinstance(steps, list):
        # If 'steps' key doesn't exist or is not a list, return empty list
        return []
    
    return steps
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
    try:
        messages = await message_service.get_chat_history(
            conversation_id=conversation_id,
            db=db
        )
        return {
            'success': True,
            'messages': messages
        }
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error getting messages for conversation {conversation_id} (for Brain): {e}")
        print(f"Error traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error retrieving messages for Brain: {str(e)}")