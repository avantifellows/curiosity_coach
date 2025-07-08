from sqlalchemy.orm import Session
from src.models import Conversation, ConversationMemory, User
from typing import List

def get_conversation_memories_by_user_id(db: Session, user_id: int) -> List[ConversationMemory]:
    """
    Retrieves all conversation memories for a given user ID.
    """
    return (
        db.query(ConversationMemory)
        .join(Conversation, ConversationMemory.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user_id)
        .all()
    ) 