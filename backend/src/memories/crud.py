from typing import Optional
from sqlalchemy.orm import Session
from src.models import ConversationMemory
from src.memories.schemas import MemoryCreate, MemoryUpdate

def get_memory_by_conversation_id(db: Session, conversation_id: int) -> Optional[ConversationMemory]:
    """
    Get a conversation memory by conversation_id.
    """
    return db.query(ConversationMemory).filter(ConversationMemory.conversation_id == conversation_id).first()

def create_memory(db: Session, memory: MemoryCreate) -> ConversationMemory:
    """
    Create a new conversation memory.
    """
    db_memory = ConversationMemory(
        conversation_id=memory.conversation_id,
        memory_data=memory.memory_data
    )
    db.add(db_memory)
    db.commit()
    db.refresh(db_memory)
    return db_memory

def update_memory(db: Session, db_memory: ConversationMemory, memory_update: MemoryUpdate) -> ConversationMemory:
    """
    Update an existing conversation memory.
    """
    db_memory.memory_data = memory_update.memory_data
    db.commit()
    db.refresh(db_memory)
    return db_memory

def upsert_memory(db: Session, memory: MemoryCreate) -> ConversationMemory:
    """
    Update a memory if it exists, otherwise create it.
    """
    db_memory = get_memory_by_conversation_id(db, conversation_id=memory.conversation_id)
    if db_memory:
        return update_memory(db, db_memory, MemoryUpdate(**memory.model_dump()))
    else:
        return create_memory(db, memory) 