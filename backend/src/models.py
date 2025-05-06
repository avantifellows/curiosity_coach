from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, sessionmaker, Session, declarative_base
from sqlalchemy.sql import func
from src.database import Base, get_db # Assuming Base and get_db will be defined in database.py
from fastapi import Depends
from typing import Optional, List

# SQLAlchemy Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=True, default="New Chat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.timestamp")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    is_user = Column(Boolean, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    responds_to_message_id = Column(Integer, ForeignKey("messages.id"), nullable=True)

    conversation = relationship("Conversation", back_populates="messages")


# --- CRUD Helper Functions ---

def get_or_create_user(db: Session, phone_number: str) -> User:
    """Get a user by phone number or create if not exists."""
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        user = User(phone_number=phone_number)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def create_conversation(db: Session, user_id: int, title: Optional[str] = "New Chat") -> Conversation:
    """Creates a new conversation for a user."""
    conversation = Conversation(user_id=user_id, title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def get_conversation(db: Session, conversation_id: int) -> Optional[Conversation]:
    """Gets a specific conversation by its ID."""
    return db.query(Conversation).filter(Conversation.id == conversation_id).first()

def update_conversation_title(db: Session, conversation_id: int, new_title: str, user_id: int) -> Optional[Conversation]:
    """Updates the title of a specific conversation for a user."""
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()

    if not conversation:
        return None # Or raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.user_id != user_id:
        # Or raise HTTPException(status_code=403, detail="Not authorized to update this conversation")
        return None # Indicate authorization failure or handle in router

    if not new_title.strip():
        # Or raise HTTPException(status_code=400, detail="Title cannot be empty")
        return None # Indicate validation failure or handle in router

    conversation.title = new_title.strip()
    # conversation.updated_at = func.now() # This is handled by onupdate=func.now() in the model
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation

def list_user_conversations(db: Session, user_id: int, limit: int = 50, offset: int = 0) -> List[Conversation]:
    """Lists conversations for a given user, most recent first."""
    return db.query(Conversation).filter(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).offset(offset).limit(limit).all()

def save_message(db: Session, conversation_id: int, content: str, is_user: bool, responds_to_message_id: Optional[int] = None) -> Message:
    """Save a message to a specific conversation."""
    conversation = get_conversation(db, conversation_id)
    if not conversation:
        raise ValueError(f"Conversation with ID {conversation_id} not found.")

    message = Message(
        conversation_id=conversation_id,
        content=content,
        is_user=is_user,
        responds_to_message_id=responds_to_message_id
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    conversation.updated_at = func.now()
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return message

def get_message_count_for_user(db: Session, user_id: int) -> int:
    """Get the total count of messages sent *by the user* across all their conversations."""
    count = db.query(func.count(Message.id))\
              .join(Conversation)\
              .filter(Conversation.user_id == user_id, Message.is_user == True)\
              .scalar()
    return count if count is not None else 0

def get_conversation_history(db: Session, conversation_id: int, limit: int = 100) -> List[Message]:
    """Get message history for a specific conversation, ordered chronologically."""
    messages = db.query(Message)\
                 .filter(Message.conversation_id == conversation_id)\
                 .order_by(Message.timestamp.asc())\
                 .limit(limit)\
                 .all()
    return messages

def get_ai_response_for_user_message(db: Session, user_message_id: int) -> Optional[Message]:
    """Get the AI response message that corresponds to a specific user message ID."""
    ai_response = db.query(Message).filter(
        Message.responds_to_message_id == user_message_id,
        Message.is_user == False
    ).first()
    return ai_response