from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from src.database import get_db
from src.queue.service import QueueService, get_queue_service
from src.models import get_conversations_needing_memory
from typing import List
import logging
import asyncio

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