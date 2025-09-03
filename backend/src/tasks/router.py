from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.database import get_db
from src.queue.service import QueueService, get_queue_service
from src.models import (
    get_conversations_needing_memory,
    get_users_needing_persona_generation,
    get_conversation,
    Message,
    get_conversations_needing_memory_for_user,
)
from typing import List, Optional
import logging
import asyncio
from pydantic import BaseModel

class PersonaTaskParams(BaseModel):
    user_id: Optional[int] = None

router = APIRouter(
    prefix="/api/tasks",
    tags=["tasks"],
    responses={404: {"description": "Not found"}},
)
logger = logging.getLogger(__name__)

async def enqueue_memory_generation_task(conversation_ids: List[int], queue_service: QueueService):
    """
    Sends a batch of conversation IDs to the SQS queue or local brain for memory generation.
    """
    if not conversation_ids:
        logger.info("No conversations needed memory generation.")
        return

    message_body = {
        "task_type": "GENERATE_MEMORY_BATCH",
        "conversation_ids": conversation_ids
    }
    
    response = await queue_service.send_batch_task(message_body)
    logger.info(f"Enqueued memory generation for {len(conversation_ids)} conversations. Response: {response}")


@router.post("/generate-memory-for-conversation/{conversation_id}", status_code=202)
async def generate_memory_for_conversation(
    conversation_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    queue_service: QueueService = Depends(get_queue_service),
    sync: bool = False,
):
    """
    Generate/regenerate memory for a specific conversation.
    If sync=true, runs synchronously (primarily for local development).
    """
    # Validate conversation exists
    conversation = get_conversation(db=db, conversation_id=conversation_id)
    if not conversation:
        return {"message": f"Conversation {conversation_id} not found."}

    # Validate conversation has messages (non-empty)
    message_count = db.query(func.count(Message.id)).filter(Message.conversation_id == conversation_id).scalar()
    if not message_count or message_count == 0:
        return {"message": f"Conversation {conversation_id} has no messages. Skipping memory generation."}

    if sync:
        await enqueue_memory_generation_task([conversation_id], queue_service)
        return {"message": f"Queued and executed memory generation for conversation_id {conversation_id}"}
    else:
        background_tasks.add_task(enqueue_memory_generation_task, [conversation_id], queue_service)
        return {"message": f"Queued memory generation for conversation_id {conversation_id}"}


@router.post("/generate-memories-for-user/{user_id}", status_code=202)
async def generate_memories_for_user(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    queue_service: QueueService = Depends(get_queue_service),
    only_needing: bool = True,
    include_empty: bool = False,
    clamp: int = -1,
    sync: bool = False,
):
    """
    Generate memories for all conversations of a user.
    - only_needing: include only conversations needing memory (no memory or outdated), with inactivity threshold
    - include_empty: include conversations with zero messages
    - clamp: limit number of conversations (-1 for no limit)
    - sync: when true, run synchronously (primarily for local dev)
    """
    # Compute conversation IDs per filters
    conversation_ids = get_conversations_needing_memory_for_user(
        db=db,
        user_id=user_id,
        only_needing=only_needing,
        include_empty=include_empty,
    )

    if not conversation_ids:
        return {"message": f"No conversations selected for user {user_id} with the provided filters."}

    original_count = len(conversation_ids)
    if clamp > -1:
        conversation_ids = conversation_ids[:clamp]

    if sync:
        await enqueue_memory_generation_task(conversation_ids, queue_service)
        return {"message": f"Queued and executed memory generation for {len(conversation_ids)} conversations (user {user_id}, out of {original_count} eligible)."}
    else:
        background_tasks.add_task(enqueue_memory_generation_task, conversation_ids, queue_service)
        return {"message": f"Queued memory generation for {len(conversation_ids)} conversations (user {user_id}, out of {original_count} eligible)."}

@router.post("/trigger-memory-generation", status_code=202)
async def trigger_memory_generation(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    queue_service: QueueService = Depends(get_queue_service),
    clamp: int = 10
):
    """
    Manually triggers a task to find conversations that need a memory generated
    and enqueues them for processing.
    
    Use the 'clamp' query parameter to limit the number of conversations processed.
    Set clamp=-1 to process all eligible conversations.
    """
    conversation_ids = get_conversations_needing_memory(db=db)
    
    if not conversation_ids:
        return {"message": "No conversations found that require memory generation."}

    original_count = len(conversation_ids)
    if clamp > -1:
        conversation_ids = conversation_ids[:clamp]

    background_tasks.add_task(enqueue_memory_generation_task, conversation_ids, queue_service)
    
    return {"message": f"Task to generate memories has been queued for {len(conversation_ids)} conversations (out of {original_count} total eligible)."}

@router.post("/trigger-memory-generation-sync", status_code=200)
async def trigger_memory_generation_sync(
    db: Session = Depends(get_db),
    queue_service: QueueService = Depends(get_queue_service),
    clamp: int = 10
):
    """
    Manually triggers a synchronous task to generate memories.
    
    Use the 'clamp' query parameter to limit the number of conversations processed.
    Set clamp=-1 to process all eligible conversations.
    """
    conversation_ids = get_conversations_needing_memory(db=db)
    
    if not conversation_ids:
        return {"message": "No conversations found that require memory generation."}

    original_count = len(conversation_ids)
    if clamp > -1:
        conversation_ids = conversation_ids[:clamp]

    await enqueue_memory_generation_task(conversation_ids, queue_service)
    
    return {"message": f"Task completed for {len(conversation_ids)} conversations (out of {original_count} total eligible)."}

@router.post("/trigger-user-persona-generation", status_code=202)
async def trigger_user_persona_generation(
    params: PersonaTaskParams,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    queue_service: QueueService = Depends(get_queue_service),
    clamp: int = 10
):
    """
    Triggers a task to generate or update user personas.
    - If user_id is provided, it triggers the task for that specific user.
    - If user_id is not provided, it finds all users who have new conversation
      memories since their last persona update and triggers tasks for them.
    - Use the 'clamp' query parameter to limit the number of users processed.
    """
    if params.user_id:
        user_ids = [params.user_id]
        source = f"user ID {params.user_id}"
        original_count = 1
    else:
        user_ids = get_users_needing_persona_generation(db=db)
        source = "all eligible users"
        original_count = len(user_ids)
        if clamp > -1:
            user_ids = user_ids[:clamp]

    if not user_ids:
        return {"message": f"No users found that require persona generation based on the criteria for {source}."}

    for user_id in user_ids:
        background_tasks.add_task(queue_service.send_user_persona_generation_task, user_id)
    
    return {"message": f"Task to generate user personas has been queued for {len(user_ids)} users from {source} (out of {original_count} total eligible)."}

@router.post("/trigger-user-persona-generation-sync", status_code=200)
async def trigger_user_persona_generation_sync(
    params: PersonaTaskParams,
    db: Session = Depends(get_db),
    queue_service: QueueService = Depends(get_queue_service),
    clamp: int = 2
):
    """
    Manually triggers a synchronous task to generate user personas.
    - If user_id is provided, it triggers the task for that specific user.
    - If user_id is not provided, it finds all users who have new conversation
      memories since their last persona update and triggers tasks for them.
    - Use the 'clamp' query parameter to limit the number of users processed.
      Set clamp to -1 to process all eligible users.
    """
    if params.user_id:
        user_ids = [params.user_id]
        source = f"user ID {params.user_id}"
    else:
        user_ids = get_users_needing_persona_generation(db=db)
        source = "all eligible users"

    if not user_ids:
        return {"message": f"No users found that require persona generation based on the criteria for {source}."}

    original_count = len(user_ids)
    if clamp > -1:
        user_ids_to_process = user_ids[:clamp]
    else:
        user_ids_to_process = user_ids

    tasks = [queue_service.send_user_persona_generation_task(user_id) for user_id in user_ids_to_process]
    results = await asyncio.gather(*tasks)

    # Optional: Check results for errors
    # This is a simple check; you might want to log more details
    successful_tasks = [res for res in results if res and not res.get("error")]
    
    return {
        "message": f"Sync task completed for {len(successful_tasks)} out of {len(user_ids_to_process)} selected users. (Total eligible: {original_count})",
        "results": results
    } 


@router.post("/generate-persona-for-user/{user_id}", status_code=202)
async def generate_persona_for_user(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    queue_service: QueueService = Depends(get_queue_service),
    generate_conversation_memories_if_not_found: bool = True,
    only_needing: bool = True,
    include_empty: bool = False,
    clamp: int = -1,
    sync: bool = False,
):
    """
    Generate/regenerate a persona for a specific user.
    Optionally refresh conversation memories first for that user.
    """
    refreshed_count = 0

    if generate_conversation_memories_if_not_found:
        conversation_ids = get_conversations_needing_memory_for_user(
            db=db,
            user_id=user_id,
            only_needing=only_needing,
            include_empty=include_empty,
        )
        if conversation_ids:
            original_count = len(conversation_ids)
            if clamp > -1:
                conversation_ids = conversation_ids[:clamp]

            if conversation_ids:
                if sync:
                    await enqueue_memory_generation_task(conversation_ids, queue_service)
                else:
                    background_tasks.add_task(enqueue_memory_generation_task, conversation_ids, queue_service)
                refreshed_count = len(conversation_ids)

    if sync:
        result = await queue_service.send_user_persona_generation_task(user_id)
        return {"message": f"Completed persona generation for user {user_id} (refreshed {refreshed_count} conversations first).", "result": result}
    else:
        background_tasks.add_task(queue_service.send_user_persona_generation_task, user_id)
        return {"message": f"Queued persona generation for user {user_id} (refreshed {refreshed_count} conversations first)."}