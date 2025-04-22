import time
from src.models import save_message, get_message_count, get_chat_history
from queue_service import queue_service

class MessageService:
    """Service for handling message operations."""
    
    @staticmethod
    async def send_message(user_id: int, content: str, purpose: str = "chat", conversation_id: str = None):
        """
        Send a new message and get a response.
        
        Args:
            user_id (int): The ID of the user sending the message
            content (str): The content of the message
            purpose (str, optional): Purpose of the message (chat, test_generation, doubt_solver)
            conversation_id (str, optional): ID of the conversation this message belongs to
            
        Returns:
            tuple: A tuple containing the saved message and the response message
        """
        # Save user message to database
        saved_message = save_message(user_id, content, is_user=True)
        
        # Send message to SQS queue for Lambda processing
        queue_service.send_message(
            user_id=user_id,
            message_content=content,
            message_id=saved_message['id'],
            purpose=purpose,
            conversation_id=conversation_id
        )
        
        # Simulate a response from Lambda
        # In a real app, this would be handled asynchronously
        time.sleep(0.5)  # Simulate processing time
        
        # Get message count
        message_count = get_message_count(user_id)
        
        # Generate a response (simulating Lambda)
        response_text = f"You have sent {message_count} message{'s' if message_count != 1 else ''}. This is a placeholder response from the backend."
        
        # Save the response
        response_message = save_message(user_id, response_text, is_user=False)
        
        return saved_message, response_message
    
    @staticmethod
    async def get_chat_history(user_id: int, limit: int = 50):
        """
        Get chat history for a user.
        
        Args:
            user_id (int): The ID of the user
            limit (int): Maximum number of messages to return
            
        Returns:
            list: List of messages
        """
        return get_chat_history(user_id, limit)

message_service = MessageService() 