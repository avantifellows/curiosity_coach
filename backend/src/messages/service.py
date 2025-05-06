import time
from sqlalchemy.orm import Session
from src.models import save_message, get_conversation_history, Message
from src.queue import queue_service
from src.database import get_db
from fastapi import Depends
from typing import List, Dict

class MessageService:
    """Service for handling message operations within conversations."""
    
    @staticmethod
    async def send_message(
        conversation_id: int, 
        content: str, 
        user_id: int,
        purpose: str = "chat", 
        db: Session = Depends(get_db)
    ) -> Dict:
        """
        Saves a user message to a specific conversation and triggers 
        asynchronous processing for a response.
        
        Args:
            conversation_id (int): The ID of the conversation
            content (str): The content of the message
            user_id (int): The ID of the user sending (for logging/queue)
            purpose (str, optional): Optional purpose of the message
            db (Session): Database session dependency
            
        Returns:
            dict: The saved user message object converted to a dictionary.
        """
        # Save user message to the specified conversation
        saved_message_obj: Message = save_message(
            db=db,
            conversation_id=conversation_id,
            content=content,
            is_user=True
        )
        
        # Convert SQLAlchemy object to dict before sending to queue or returning
        saved_message = {c.name: getattr(saved_message_obj, c.name) for c in saved_message_obj.__table__.columns}

        # Trigger asynchronous message processing via queue
        print(f"MessageService: Calling queue_service.send_message with: conversation_id={conversation_id}, message_id={saved_message['id']}, user_id={user_id}, purpose={purpose}")
        queue_response = await queue_service.send_message(
            conversation_id=conversation_id,
            message_id=saved_message['id'], 
            message_content=content,
            user_id=user_id,
            purpose=purpose
        )
        print(f"MessageService: Response from queue_service.send_message: {queue_response}")

        if isinstance(queue_response, dict) and queue_response.get('error'):
            print(f"MessageService: Warning - Queue service reported an error: {queue_response['error']}. Proceeding as message is saved.")

        print(f"MessageService: Returning saved message: {saved_message}")
        return saved_message
    
    @staticmethod
    async def get_chat_history(
        conversation_id: int,
        limit: int = 100,
        db: Session = Depends(get_db)
    ) -> List[Message]:
        """
        Get message history for a specific conversation.
        
        Args:
            conversation_id (int): The ID of the conversation
            limit (int): Maximum number of messages to return
            db (Session): Database session dependency
            
        Returns:
            list: List of Message objects (SQLAlchemy models)
        """
        print(f"MessageService: Fetching history for conversation_id: {conversation_id} with limit {limit}")
        messages = get_conversation_history(
            db=db,
            conversation_id=conversation_id,
            limit=limit
        )
        print(f"MessageService: Fetched {len(messages)} messages for conversation_id: {conversation_id}")
        return messages

message_service = MessageService() 