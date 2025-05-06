from fastapi import APIRouter, HTTPException, Depends, Body, status
import traceback
from sqlalchemy.orm import Session
from typing import Optional, List # Added List
from src.messages.schemas import MessageRequest, MessageData, ChatHistoryResponse, SendMessageResponse, BrainResponsePayload # Removed unused MessageResponse
from src.messages.service import message_service
# Import necessary models and CRUD functions
from src import models 
from src.models import User, Conversation, Message # Import User for auth, Conversation/Message for lookups
# --- TODO: Verify correct auth dependency --- 
from src.auth.dependencies import get_current_user # Changed from get_user_id
# --- End auth dependency --- 
from src.database import get_db

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
            
        # Save the AI's response to the database using the new model function signature
        saved_response = models.save_message(
            db=db,
            conversation_id=payload.conversation_id, # Use conversation_id from payload
            content=payload.response_content,
            is_user=False,
            responds_to_message_id=payload.original_message_id
        )
        print(f"Saved brain response with ID: {saved_response.id} to conversation ID: {payload.conversation_id}")

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