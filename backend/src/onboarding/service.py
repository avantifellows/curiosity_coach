"""
Onboarding service with sync memory/persona generation and retry logic.
"""
import time
import asyncio
import logging
import httpx
from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.config.settings import settings
from src.models import (
    get_memory_for_conversation,
    UserPersona,
    get_user_conversations_list,
    has_messages
)

logger = logging.getLogger(__name__)


async def generate_memory_sync(conversation_id: int, db: Session):
    """
    Asynchronously generate memory for a conversation.
    Calls Brain's /tasks endpoint with GENERATE_MEMORY_BATCH task.
    Polls until memory is generated or timeout (120s).
    Raises TimeoutError on timeout, HTTPException on other errors.
    """
    brain_endpoint = (
        settings.LOCAL_BRAIN_ENDPOINT_URL 
        if settings.APP_ENV == "development" 
        else settings.BRAIN_ENDPOINT_URL
    )
    timeout = settings.MEMORY_GENERATION_TIMEOUT
    
    logger.info(f"Starting async memory generation for conversation {conversation_id}")
    
    # 1. Trigger Brain task
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{brain_endpoint}/tasks",
                json={
                    "task_type": "GENERATE_MEMORY_BATCH",
                    "conversation_ids": [conversation_id]
                },
                timeout=timeout
            )
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Error calling Brain for memory generation: {e}")
        raise HTTPException(status_code=503, detail=f"Memory generation request failed: {e}")
    
    # 2. Poll for memory with timeout (using asyncio.sleep to avoid blocking)
    start_time = time.time()
    while time.time() - start_time < timeout:
        memory = get_memory_for_conversation(db, conversation_id)
        if memory:
            logger.info(f"Memory generated successfully for conversation {conversation_id}")
            return memory
        await asyncio.sleep(1)  # Non-blocking sleep
        db.expire_all()  # Refresh DB session
    
    raise TimeoutError(f"Memory generation timed out after {timeout}s for conversation {conversation_id}")


async def generate_memory_sync_with_retry(
    conversation_id: int, 
    db: Session, 
    max_retries: int = 2
):
    """
    Asynchronously generate memory with retry logic.
    Retries up to max_retries times with exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            return await generate_memory_sync(conversation_id, db)
        except TimeoutError:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s...
            await asyncio.sleep(wait_time)  # Non-blocking sleep
            logger.info(f"Retrying memory generation for conversation {conversation_id}, attempt {attempt + 2}/{max_retries}")


async def generate_persona_sync(user_id: int, db: Session):
    """
    Asynchronously generate persona for a user.
    Calls Brain's /tasks endpoint with USER_PERSONA_GENERATION task.
    Polls until persona is generated or timeout (120s).
    """
    brain_endpoint = (
        settings.LOCAL_BRAIN_ENDPOINT_URL 
        if settings.APP_ENV == "development" 
        else settings.BRAIN_ENDPOINT_URL
    )
    timeout = settings.PERSONA_GENERATION_TIMEOUT
    
    logger.info(f"Starting async persona generation for user {user_id}")
    
    # 1. Trigger Brain task
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{brain_endpoint}/tasks",
                json={
                    "task_type": "USER_PERSONA_GENERATION",
                    "user_id": user_id  # Brain expects singular user_id, not user_ids list
                },
                timeout=timeout
            )
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.error(f"Error calling Brain for persona generation: {e}")
        raise HTTPException(status_code=503, detail=f"Persona generation request failed: {e}")
    
    # 2. Poll for persona with timeout (using asyncio.sleep to avoid blocking)
    start_time = time.time()
    while time.time() - start_time < timeout:
        persona = db.query(UserPersona).filter(UserPersona.user_id == user_id).first()
        if persona:
            logger.info(f"Persona generated successfully for user {user_id}")
            return persona
        await asyncio.sleep(1)  # Non-blocking sleep
        db.expire_all()  # Refresh DB session
    
    raise TimeoutError(f"Persona generation timed out after {timeout}s for user {user_id}")


async def generate_persona_sync_with_retry(
    user_id: int, 
    db: Session, 
    max_retries: int = 2
):
    """
    Asynchronously generate persona with retry logic.
    Retries up to max_retries times with exponential backoff.
    """
    for attempt in range(max_retries):
        try:
            return await generate_persona_sync(user_id, db)
        except TimeoutError:
            if attempt == max_retries - 1:
                raise
            wait_time = 2 ** attempt  # Exponential backoff
            await asyncio.sleep(wait_time)  # Non-blocking sleep
            logger.info(f"Retrying persona generation for user {user_id}, attempt {attempt + 2}/{max_retries}")


async def generate_ai_first_message(
    conversation_id: int,
    user_id: int,
    visit_number: int,
    db: Session
) -> str:
    """
    Trigger Brain to generate opening message and wait for it.
    Raises TimeoutError if generation fails.
    
    IMPORTANT: Opening messages MUST be synchronous (user is waiting during 
    conversation creation), so we use direct HTTP to Brain even in production.
    """
    from src.models import get_conversation_history
    
    callback_url = f"{settings.BACKEND_CALLBACK_BASE_URL}/api/internal/opening_message"
    
    # ALWAYS use direct HTTP for opening messages (synchronous requirement)
    brain_endpoint = (
        settings.LOCAL_BRAIN_ENDPOINT_URL 
        if settings.APP_ENV == "development" 
        else settings.BRAIN_ENDPOINT_URL
    )
    
    timeout = settings.OPENING_MESSAGE_TIMEOUT
    
    logger.info(f"Requesting opening message for conversation {conversation_id}, visit {visit_number}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{brain_endpoint}/generate-opening-message",
                json={
                    "conversation_id": conversation_id,
                    "user_id": user_id,
                    "visit_number": visit_number,
                    "callback_url": callback_url
                },
                timeout=timeout
            )
            response.raise_for_status()
    except (httpx.TimeoutException, httpx.HTTPError) as e:
        logger.error(f"Error calling Brain for opening message: {e}")
        raise TimeoutError(f"Failed to request opening message generation: {e}")
    
    # Poll for message (with timeout)
    import asyncio
    start_time = time.time()
    while time.time() - start_time < timeout:
        await asyncio.sleep(1)
        messages = get_conversation_history(db, conversation_id)
        if messages and not messages[0].is_user:
            logger.info(f"Opening message generated successfully for conversation {conversation_id}")
            return messages[0].content
        db.expire_all()  # Refresh DB session
    
    # Timeout - raise error
    logger.error(f"Opening message timeout for conversation {conversation_id} after {timeout}s")
    raise TimeoutError(f"Opening message generation timed out after {timeout}s")


async def ensure_memories_for_conversations(
    db: Session,
    user_id: int,
    exclude_conversation_id: int
) -> None:
    """
    Ensure all previous conversations (excluding current) have memories.
    Generates memories asynchronously for any conversations that don't have them.
    Skips empty conversations (no messages).
    """
    from src.models import get_user_conversations_list, get_memory_for_conversation
    
    all_conversations = get_user_conversations_list(db, user_id)
    previous_conversations = [c for c in all_conversations if c.id != exclude_conversation_id]
    
    logger.info(f"Checking memories for {len(previous_conversations)} previous conversations")
    
    for conv in previous_conversations:
        # Check if conversation has messages before generating memory
        if has_messages(db, conv.id):
            memory = get_memory_for_conversation(db, conv.id)
            if not memory:
                logger.info(f"Generating missing memory for conversation {conv.id}")
                # Async memory generation with retry - NON-BLOCKING
                await generate_memory_sync_with_retry(
                    conversation_id=conv.id,
                    db=db,
                    max_retries=2
                )
        else:
            logger.info(f"Skipping memory generation for empty conversation {conv.id}")

