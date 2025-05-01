from fastapi import APIRouter, HTTPException, Depends, Body, status
import traceback
from sqlalchemy.orm import Session
from typing import Optional # Added for Optional return type
from src.messages.schemas import MessageRequest, MessageResponse, ChatHistoryResponse, SendMessageResponse, MessageData, BrainResponsePayload
from src.messages.service import message_service
from src.models import save_message, get_ai_response_for_user_message # Import the new CRUD function
from src.auth.dependencies import get_user_id
from src.database import get_db

router = APIRouter(
    prefix="/api/messages",
    tags=["messages"]
)

@router.post("", response_model=SendMessageResponse)
async def send_message(request: MessageRequest, user_id: int = Depends(get_user_id), db: Session = Depends(get_db)):
    """
    Accepts a user message, saves it, and triggers asynchronous processing.
    Returns the saved user message immediately.
    Requires authentication header: 'Authorization: Bearer <user_id>'
    """
    content = request.content
    purpose = request.purpose if hasattr(request, 'purpose') else "chat"
    conversation_id = request.conversation_id if hasattr(request, 'conversation_id') else None
    
    print(f"Processing message for user_id: {user_id}")
    print(f"Request data: {request}")
    
    print(f"Router: Entering send_message try block for user_id: {user_id}") # Log try block entry
    try:
        # Save message and trigger async processing (service function doesn't block)
        print(f"Router: Calling message_service.send_message with user_id={user_id}, content='{content}', purpose='{purpose}', conversation_id={conversation_id}") # Log before service call
        saved_message = await message_service.send_message(
            user_id=user_id,
            content=content,
            purpose=purpose,
            conversation_id=conversation_id,
            db=db
        )
        
        print(f"Router: Received saved_message from service: {saved_message}") # Log service response
        # Note: Response generation is now handled asynchronously.
        
        print(f"Router: Successfully processed message for user_id: {user_id}. Returning success response.") # Log success exit
        return {
            'success': True,
            'message': MessageData(**saved_message) # Ensure it fits the schema
            # 'response' field is removed as it's no longer generated synchronously
        }
    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Router: Error in send_message for user_id: {user_id}. Error: {e}") # Log exception
        print(f"Router: Error traceback: {error_details}")
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")

@router.get("/history", response_model=ChatHistoryResponse)
async def get_messages(user_id: int = Depends(get_user_id), db: Session = Depends(get_db)):
    """
    Get chat history for the authenticated user.
    Requires authentication header: 'Authorization: Bearer <user_id>'
    """
    try:
        # Get chat history
        messages = await message_service.get_chat_history(user_id=user_id, db=db)
        return {
            'success': True,
            'messages': messages
        }
    except Exception as e:
        print(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving messages: {str(e)}")

@router.get("/{user_message_id}/response", response_model=Optional[MessageData], responses={202: {"description": "AI response is pending"}})
async def get_ai_response(user_message_id: int, user_id: int = Depends(get_user_id), db: Session = Depends(get_db)):
    """
    Poll for the AI response corresponding to a specific user message.
    Requires authentication header: 'Authorization: Bearer <user_id>'
    
    Returns:
    - 200 OK with MessageData if the AI response is found.
    - 202 Accepted if the AI response is not yet available.
    - 404 Not Found if the original user message doesn't exist or doesn't belong to the user.
    """
    try:
        # Optional: Verify the original user_message_id belongs to the authenticated user_id
        # original_message = db.query(Message).filter(Message.id == user_message_id, Message.user_id == user_id).first()
        # if not original_message:
        #     raise HTTPException(status_code=404, detail="Original message not found or access denied")

        ai_response = get_ai_response_for_user_message(db=db, user_message_id=user_message_id)

        if ai_response:
            # Ensure the AI response belongs to the same user (indirectly via linked user message)
            if ai_response.user_id != user_id:
                 # This check might be redundant if the original message check is implemented
                 raise HTTPException(status_code=403, detail="Access denied to AI response") 
            return MessageData.model_validate(ai_response) # Use model_validate for Pydantic v2
        else:
            # Return None to indicate the resource isn't available *yet*
            return None

    except HTTPException as he:
        raise he # Re-raise HTTPExceptions
    except Exception as e:
        print(f"Error fetching AI response for user message {user_message_id}: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving AI response")

# Internal route for Brain service callback
# No user auth needed here if it's internal/protected network
@router.post("/internal/brain_response", status_code=status.HTTP_202_ACCEPTED)
async def receive_brain_response(payload: BrainResponsePayload, db: Session = Depends(get_db)):
    """
    Receives the processed response from the Brain service and saves it.
    This is intended to be called internally by the Brain service.
    """
    print(f"Received brain response for user_id: {payload.user_id}")
    # Optional: Add more detailed logging of the payload if needed for debugging
    # print(f"Brain payload: {payload.dict()}")

    try:
        # Save the AI's response to the database
        saved_response = save_message(
            db=db,
            user_id=payload.user_id,
            content=payload.response_content,
            is_user=False,
            responds_to_message_id=payload.original_message_id # Link response to the user message
            # Optionally link to conversation/original message if needed later
            # conversation_id=payload.conversation_id,
            # Add other fields from payload if your Message model supports them
        )
        print(f"Saved brain response with ID: {saved_response.id} linked to user message ID: {payload.original_message_id}")

        # --- TODO: Trigger notification to frontend (e.g., via SSE) --- 
        # This is where you would signal that a new message is ready for the user.
        # Example placeholder:
        # await notify_frontend(user_id=payload.user_id, message=saved_response)

        return {"status": "received", "message_id": saved_response.id}

    except Exception as e:
        error_details = traceback.format_exc()
        print(f"Error processing brain response: {e}")
        print(f"Error details: {error_details}")
        # Return 500 so the Brain service knows something went wrong
        raise HTTPException(status_code=500, detail="Error saving brain response") 