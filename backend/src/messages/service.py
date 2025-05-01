import time
from sqlalchemy.orm import Session
from src.models import save_message, get_message_count, get_chat_history
from src.queue import queue_service
from src.database import get_db
from fastapi import Depends

class MessageService:
    """Service for handling message operations."""
    
    @staticmethod
    async def send_message(user_id: int, content: str, purpose: str = "chat", conversation_id: str = None, db: Session = Depends(get_db)):
        """
        Saves a user message and triggers asynchronous processing for a response.
        
        Args:
            user_id (int): The ID of the user sending the message
            content (str): The content of the message
            purpose (str, optional): Purpose of the message (chat, test_generation, doubt_solver)
            conversation_id (str, optional): ID of the conversation this message belongs to
            db (Session): Database session dependency
            
        Returns:
            dict: The saved user message object as a dictionary.
        """
        # Save user message to database
        saved_message_obj = save_message(db, user_id, content, is_user=True)
        
        # Convert SQLAlchemy object to dict before sending to queue or returning
        saved_message = {c.name: getattr(saved_message_obj, c.name) for c in saved_message_obj.__table__.columns}

        # Trigger asynchronous message processing (e.g., send to Brain via queue/HTTP)
        # Now awaiting the call to ensure it completes before proceeding (if necessary)
        # or at least doesn't raise a warning.
        
        print(f"MessageService: Calling queue_service.send_message with: user_id={user_id}, message_id={saved_message['id']}, purpose={purpose}, conversation_id={conversation_id}") # Log before call
        queue_response = await queue_service.send_message(
            user_id=user_id,
            message_content=content,
            message_id=saved_message['id'],
            purpose=purpose,
            conversation_id=conversation_id
        )
        print(f"MessageService: Response from queue_service.send_message: {queue_response}") # Log after call

        # Check if the queue service reported an error
        if isinstance(queue_response, dict) and queue_response.get('error'):
            print(f"MessageService: Warning - Queue service reported an error: {queue_response['error']}. Proceeding as message is saved.")
            # Decide if you want to raise an exception here or just log the warning
            # For now, we log and proceed, as the user message *is* saved.

        # Return only the user's saved message
        print(f"MessageService: Returning saved message: {saved_message}") # Log return
        return saved_message
    
    @staticmethod
    async def get_chat_history(user_id: int, limit: int = 50, db: Session = Depends(get_db)):
        """
        Get chat history for a user.
        
        Args:
            user_id (int): The ID of the user
            limit (int): Maximum number of messages to return
            db (Session): Database session dependency
            
        Returns:
            list: List of messages
        """
        return get_chat_history(db, user_id, limit)

message_service = MessageService() 