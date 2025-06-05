import time
import logging
from sqlalchemy.orm import Session
from src.models import save_message, get_conversation_history, Message
from src.queue import queue_service
from src.database import get_db
from fastapi import Depends
from typing import List, Dict

# Set up logger for this module
logger = logging.getLogger(__name__)

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
            
            # Convert SQLAlchemy object to dict before sending to queue or returning
            saved_message = {c.name: getattr(saved_message_obj, c.name) for c in saved_message_obj.__table__.columns}
            
            logger.debug(f"Message object converted to dict - message_id: {saved_message['id']}")

            # Trigger asynchronous message processing via queue
            logger.info(f"About to send message to queue service - message_id: {saved_message['id']}")
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
                # Continue execution even if queue fails - user message is already saved

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