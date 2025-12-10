import time
import logging
import asyncio
from sqlalchemy.orm import Session
from src.models import save_message, get_conversation_history, Message, get_conversation, update_conversation_title
from src.queue import queue_service
from src.database import get_db
from fastapi import Depends
from typing import List, Dict

# Set up logger for this module
logger = logging.getLogger(__name__)


def generate_title_from_message(content: str, max_length: int = 50) -> str:
    """
    Generate a concise title from message content.
    Takes first sentence or first N characters.
    
    Args:
        content: The message content
        max_length: Maximum length for the title
        
    Returns:
        A title string
    """
    # Simple implementation: take first sentence up to max_length
    sentences = content.split('.')
    title = sentences[0].strip()
    
    # Truncate if too long
    if len(title) > max_length:
        title = title[:max_length].rsplit(' ', 1)[0] + "..."
    
    return title if title else "New Chat"

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
        start_time = time.time()
        
        logger.info(
            f"MessageService.send_message started - user_id: {user_id}, "
            f"conversation_id: {conversation_id}, purpose: {purpose}, "
            f"content_length: {len(content)}"
        )
        
        logger.debug(f"Message content preview: {content[:100]}{'...' if len(content) > 100 else ''}")
        
        try:
            # Save user message to the specified conversation
            logger.debug(f"Saving user message to database for conversation_id: {conversation_id}")
            saved_message_obj: Message = save_message(
                db=db,
                conversation_id=conversation_id,
                content=content,
                is_user=True
            )
            
            logger.info(f"User message saved successfully - message_id: {saved_message_obj.id}")
            
            # Auto-generate title from user's first message
            try:
                conversation = get_conversation(db, conversation_id)
                if conversation and conversation.title == "New Chat":
                    # Count user messages in this conversation
                    user_message_count = db.query(Message).filter(
                        Message.conversation_id == conversation_id,
                        Message.is_user == True
                    ).count()
                    
                    if user_message_count == 1:  # This is the first user message
                        new_title = generate_title_from_message(content)
                        logger.info(f"Auto-generating title for conversation {conversation_id}: '{new_title}'")
                        update_conversation_title(db, conversation_id, new_title, user_id)
            except Exception as title_error:
                # Don't fail the message send if title generation fails
                logger.warning(f"Failed to auto-generate title for conversation {conversation_id}: {title_error}")
            
            # Convert SQLAlchemy object to dict before sending to queue or returning
            saved_message = {c.name: getattr(saved_message_obj, c.name) for c in saved_message_obj.__table__.columns}
            
            logger.debug(f"Message object converted to dict - message_id: {saved_message['id']}")

            async def _queue_and_log():
                try:
                    logger.info(f"Calling queue_service.send_message - message_id: {saved_message['id']}")
                    queue_response = await queue_service.send_message(
                        conversation_id=conversation_id,
                        message_id=saved_message['id'], 
                        message_content=content,
                        user_id=user_id,
                        purpose=purpose
                    )
                    logger.info(f"Queue service call completed - message_id: {saved_message['id']}")

                    if isinstance(queue_response, dict) and queue_response.get('error'):
                        logger.warning(
                            f"Queue service reported an error for message_id {saved_message['id']}: "
                            f"{queue_response['error']}. Message is saved but processing may be delayed."
                        )
                    else:
                        logger.info(f"Message successfully queued for processing - message_id: {saved_message['id']}")

                except Exception as queue_error:
                    logger.error(
                        f"Queue service failed for message_id {saved_message['id']}: "
                        f"{str(queue_error)}. Message is saved but processing may be delayed."
                    )

            logger.info(f"Dispatching message to queue service in background - message_id: {saved_message['id']}")
            try:
                asyncio.get_running_loop()
                asyncio.create_task(_queue_and_log())
            except RuntimeError:
                # No running loop (e.g. during CLI scripts/tests); fall back to direct await
                await _queue_and_log()

            processing_time = time.time() - start_time
            logger.info(
                f"MessageService.send_message completed successfully - "
                f"message_id: {saved_message['id']}, processing_time: {processing_time:.3f}s"
            )
            
            return saved_message
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"MessageService.send_message failed - user_id: {user_id}, "
                f"conversation_id: {conversation_id}, error: {str(e)}, "
                f"processing_time: {processing_time:.3f}s"
            )
            raise
    
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
        start_time = time.time()
        
        logger.info(
            f"MessageService.get_chat_history started - "
            f"conversation_id: {conversation_id}, limit: {limit}"
        )
        
        try:
            logger.debug(f"Fetching conversation history from database for conversation_id: {conversation_id}")
            
            messages = get_conversation_history(
                db=db,
                conversation_id=conversation_id,
                limit=limit
            )
            
            message_count = len(messages)
            processing_time = time.time() - start_time
            
            logger.info(
                f"MessageService.get_chat_history completed successfully - "
                f"conversation_id: {conversation_id}, message_count: {message_count}, "
                f"processing_time: {processing_time:.3f}s"
            )
            
            if message_count == 0:
                logger.debug(f"No messages found for conversation_id: {conversation_id}")
            else:
                logger.debug(
                    f"Retrieved {message_count} messages for conversation_id: {conversation_id}. "
                    f"First message timestamp: {messages[0].timestamp if messages else 'N/A'}, "
                    f"Last message timestamp: {messages[-1].timestamp if messages else 'N/A'}"
                )
            
            return messages
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(
                f"MessageService.get_chat_history failed - "
                f"conversation_id: {conversation_id}, error: {str(e)}, "
                f"processing_time: {processing_time:.3f}s"
            )
            raise

message_service = MessageService() 
