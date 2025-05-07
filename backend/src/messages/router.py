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

    print(f"Processing message for conversation_id: {conversation_id}, user_id: {user_id}")
    print(f"Request data: {request}")
    
    try:
        # Service function needs modification to accept conversation_id
        print(f"Router: Calling message_service.send_message with user_id={user_id}, content='{content}', purpose='{purpose}', conversation_id={conversation_id}")
        saved_message = await message_service.send_message(
            user_id=user_id, # Keep user_id if service layer needs it for context/logging
            conversation_id=conversation_id, # Pass conversation_id explicitly
            content=content,
            purpose=purpose,
            db=db
        )
        
        print(f"Router: Received saved_message from service: {saved_message}")
        print(f"Router: Successfully processed message for conversation_id: {conversation_id}. Returning success response.")
        return {
            'success': True,
            'message': MessageData.model_validate(saved_message) # Use model_validate
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
        # Service function needs modification to accept conversation_id
        print(f"Router: Calling message_service.get_chat_history for conversation_id: {conversation_id}")
        messages = await message_service.get_chat_history(
            conversation_id=conversation_id,
            db=db
            # user_id=user_id # Pass user_id only if service strictly needs it
        )
        print(f"Router: Retrieved history for conversation_id: {conversation_id}")
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
            # AI response doesn't exist (yet)
            # Optional: Verify the original user message exists and belongs to the user's conversation
            # original_message = db.query(models.Message).get(user_message_id)
            # if original_message:
            #     try: 
            #         await verify_conversation_ownership(original_message.conversation_id, current_user, db)
            #     except HTTPException:
            #         # Original message exists but doesn't belong to user, return 404
            #         raise HTTPException(status_code=404, detail="Message not found")
            # else:
            #     # Original message doesn't exist at all
            #      raise HTTPException(status_code=404, detail="Message not found")
            
            # If original message check passed (or wasn't done), return None for pending
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
    print(f"Received brain response for conversation_id: {payload.conversation_id}, original_message_id: {payload.original_message_id}")
    # print(f"Brain payload: {payload.dict()}")

    try:
        # Verify the target conversation exists (optional but good practice)
        conversation = models.get_conversation(db, payload.conversation_id)
        if not conversation:
            # Log error and maybe return 404 if the Brain should know?
            print(f"Error: Brain response received for non-existent conversation_id: {payload.conversation_id}")
            raise HTTPException(status_code=404, detail=f"Conversation {payload.conversation_id} not found.")
            
        # # --- Save BrainResponsePayload to a JSON file ---
        # brain_responses_dir = "brain_responses"
        # os.makedirs(brain_responses_dir, exist_ok=True)

        # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        # filename = os.path.join(brain_responses_dir, f"brain_response_{payload.conversation_id}_{timestamp}.json")

        # try:
        #     with open(filename, "w") as f:
        #         json.dump(payload.dict(), f, indent=4)
        #     print(f"Saved brain response payload to {filename}")
        # except Exception as e:
        #     print(f"Error saving brain response payload to file for conversation {payload.conversation_id}: {e}")
        #     # Optionally, re-raise or handle this error appropriately if saving is critical
        #     # For now, we'll just print and continue processing the message

        # Prepare pipeline_data for saving
        pipeline_data_to_save = None
        if payload.pipeline_data:
            pipeline_data_to_save = payload.pipeline_data.copy() # Create a copy to modify
            pipeline_data_to_save.pop('query', None) # Remove 'query' if it exists
            pipeline_data_to_save.pop('final_response', None) # Remove 'final_response' if it exists

        # Save the AI's response to the database using the new model function signature
        saved_response = models.save_message(
            db=db,
            conversation_id=payload.conversation_id, # Use conversation_id from payload
            content=payload.llm_response, # Use llm_response from the payload
            is_user=False,
            responds_to_message_id=payload.original_message_id,
        )
        print(f"Saved brain response with ID: {saved_response.id} to conversation ID: {payload.conversation_id}")

        # Now, save the pipeline data to the new table if it exists
        if pipeline_data_to_save: # This is the filtered data from before
            models.save_message_pipeline_data(
                db=db,
                message_id=saved_response.id, 
                pipeline_data_dict=pipeline_data_to_save
            )
            print(f"Saved pipeline data for message ID: {saved_response.id}")

        # --- TODO: Trigger notification to frontend (e.g., via SSE) --- 
        # Signal needs conversation_id and potentially user_id (fetch from conversation object)
        # await notify_frontend(user_id=conversation.user_id, conversation_id=payload.conversation_id, message=saved_response)

        return {"status": "received", "message_id": saved_response.id}

    except HTTPException as he:
        raise he # Re-raise validation errors
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
        print(f"Router (Internal): Calling message_service.get_chat_history for conversation_id: {conversation_id} (for Brain)")
        # Assuming message_service.get_chat_history can handle calls without a user_id
        # or that the service layer can determine it's an internal call.
        # If get_chat_history strictly requires user_id for ownership, this service call might need adjustment
        # or a new service function specific for internal use.
        messages = await message_service.get_chat_history(
            conversation_id=conversation_id,
            db=db
            # user_id is intentionally omitted for this internal endpoint
        )
        print(f"Router (Internal): Retrieved history for conversation_id: {conversation_id} (for Brain)")
        return {
            'success': True,
            'messages': messages
        }
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error getting messages for conversation {conversation_id} (for Brain): {e}")
        print(f"Error traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error retrieving messages for Brain: {str(e)}")