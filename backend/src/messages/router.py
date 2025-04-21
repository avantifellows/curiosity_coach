from fastapi import APIRouter, HTTPException, Depends
from src.messages.schemas import MessageRequest, MessageResponse, ChatHistoryResponse
from src.messages.service import message_service
from src.auth.dependencies import get_user_id

router = APIRouter(
    prefix="/api/messages",
    tags=["messages"]
)

@router.post("", response_model=MessageResponse)
async def send_message(request: MessageRequest, user_id: int = Depends(get_user_id)):
    """
    Send a new message and receive a response.
    Requires authentication header: 'Authorization: Bearer <user_id>'
    """
    content = request.content
    
    try:
        # Send message and get response
        saved_message, response_message = await message_service.send_message(user_id, content)
        
        return {
            'success': True,
            'message': saved_message,
            'response': response_message
        }
    except Exception as e:
        print(f"Error sending message: {e}")
        raise HTTPException(status_code=500, detail=f"Error sending message: {str(e)}")

@router.get("/history", response_model=ChatHistoryResponse)
async def get_messages(user_id: int = Depends(get_user_id)):
    """
    Get chat history for the authenticated user.
    Requires authentication header: 'Authorization: Bearer <user_id>'
    """
    try:
        # Get chat history
        messages = await message_service.get_chat_history(user_id)
        return {
            'success': True,
            'messages': messages
        }
    except Exception as e:
        print(f"Error getting messages: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving messages: {str(e)}") 