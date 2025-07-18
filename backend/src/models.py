from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, ForeignKeyConstraint, UniqueConstraint, CheckConstraint, and_
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
from src.database import Base
from typing import Optional, List
from datetime import datetime, timedelta
import random
import time
from src.config.settings import settings

# SQLAlchemy Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=True)
    name = Column(String(50), unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    persona = relationship("UserPersona", back_populates="user", uselist=False, cascade="all, delete-orphan")
    feedbacks = relationship("UserFeedback", back_populates="user", cascade="all, delete-orphan")

class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="feedbacks")

    __table_args__ = (
        CheckConstraint(
            'phone_number IS NOT NULL OR name IS NOT NULL', 
            name='check_user_has_identifier'
        ),
    )

class UserPersona(Base):
    __tablename__ = "user_personas"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    persona_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="persona")

class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String, nullable=True, default="New Chat")
    prompt_version_id = Column(Integer, ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.timestamp")
    prompt_version = relationship("PromptVersion")
    memory = relationship("ConversationMemory", back_populates="conversation", uselist=False, cascade="all, delete-orphan")

class ConversationMemory(Base):
    __tablename__ = "conversation_memories"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    memory_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    conversation = relationship("Conversation", back_populates="memory")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    is_user = Column(Boolean, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    responds_to_message_id = Column(Integer, ForeignKey("messages.id", ondelete="SET NULL"), nullable=True)

    conversation = relationship("Conversation", back_populates="messages")
    pipeline_info = relationship("MessagePipelineData", back_populates="message", uselist=False, cascade="all, delete-orphan")

# New Table for Pipeline Data
class MessagePipelineData(Base):
    __tablename__ = "message_pipeline_data"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("messages.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    pipeline_data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    message = relationship("Message", back_populates="pipeline_info")

# --- Prompt Versioning Models ---

class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    versions = relationship("PromptVersion", back_populates="prompt", cascade="all, delete-orphan")
    
    active_prompt_version = relationship(
        "PromptVersion",
        primaryjoin="and_(Prompt.id == PromptVersion.prompt_id, PromptVersion.is_active == True)",
        uselist=False,
        viewonly=True
    )

    def __repr__(self):
        return f"<Prompt(id={self.id}, name='{self.name}')>"

class PromptVersion(Base):
    __tablename__ = "prompt_versions"

    id = Column(Integer, primary_key=True, index=True)
    prompt_id = Column(Integer, ForeignKey("prompts.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    version_number = Column(Integer, nullable=False)
    prompt_text = Column(Text, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False, index=True)
    is_production = Column(Boolean, default=False, nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    prompt = relationship("Prompt", back_populates="versions")
    user = relationship("User")

    __table_args__ = (
        # Ensure version_number is unique per prompt_id
        ForeignKeyConstraint(["prompt_id"], ["prompts.id"], name="fk_prompt_version_prompt_id"),
        UniqueConstraint("prompt_id", "version_number", name="uq_prompt_id_version_number"),
        # Note: The constraint for a single active version (is_active=True per prompt_id)
        # will be handled by a partial unique index created via Alembic.
    )

    def __repr__(self):
        return f"<PromptVersion(id={self.id}, prompt_id={self.prompt_id}, version={self.version_number}, active={self.is_active}, production={self.is_production}, user_id={self.user_id})>"

# --- CRUD Helper Functions ---

def generate_unique_name(db: Session, base_name: str) -> str:
    """Generate a unique name by appending 3 random digits to the base name."""
    base_name = base_name.strip().title()  # "surya" -> "Surya"
    
    # Try 5 times to find a unique name
    for _ in range(5):
        suffix = random.randint(100, 999)  # 3 digits: 100-999
        candidate_name = f"{base_name}{suffix}"
        if not db.query(User).filter(User.name == candidate_name).first():
            return candidate_name
    
    # Fallback to timestamp if all attempts fail
    timestamp = int(time.time()) % 1000
    return f"{base_name}{timestamp}"

def get_or_create_user_by_phone(db: Session, phone_number: str) -> User:
    """Get a user by phone number or create if not exists."""
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        user = User(phone_number=phone_number)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def get_or_create_user_by_name(db: Session, name: str) -> User:
    """Get a user by name or create if not exists."""
    user = db.query(User).filter(User.name == name).first()
    if not user:
        user = User(name=name)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def determine_identifier_type(identifier: str) -> str:
    """Determine if identifier is a phone number or name."""
    # If it's all digits and 10-15 characters, treat as phone
    if identifier.isdigit() and 10 <= len(identifier) <= 15:
        return "phone"
    return "name"

def get_or_create_user_by_identifier(db: Session, identifier: str) -> tuple[User, Optional[str]]:
    """
    Get or create user by identifier (phone or name).
    Returns tuple of (user, generated_name) where generated_name is None for phone logins.
    """
    identifier_type = determine_identifier_type(identifier)
    
    if identifier_type == "phone":
        user = get_or_create_user_by_phone(db, identifier)
        return user, None
    else:
        # Generate unique name for name-based login
        unique_name = generate_unique_name(db, identifier)
        user = get_or_create_user_by_name(db, unique_name)
        return user, unique_name

# Keep old function for backward compatibility
def get_or_create_user(db: Session, phone_number: str) -> User:
    """Get a user by phone number or create if not exists. (Backward compatibility)"""
    return get_or_create_user_by_phone(db, phone_number)

def create_conversation(db: Session, user_id: int, title: Optional[str] = "New Chat", prompt_version_id: Optional[int] = None) -> Conversation:
    """Creates a new conversation for a user."""
    conversation = Conversation(user_id=user_id, title=title, prompt_version_id=prompt_version_id)
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

def delete_conversation(db: Session, conversation_id: int, user_id: int) -> bool:
    """Deletes a conversation by its ID, ensuring user ownership."""
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == user_id
    ).first()

    if not conversation:
        # Conversation not found or user does not have permission
        return False

    db.delete(conversation)
    db.commit()
    return True

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

def get_memory_for_conversation(db: Session, conversation_id: int) -> Optional[ConversationMemory]:
    """Get the memory for a specific conversation by its ID."""
    return db.query(ConversationMemory).filter(ConversationMemory.conversation_id == conversation_id).first()

def get_conversations_needing_memory(db: Session) -> List[int]:
    """
    Get IDs of conversations that have been inactive for a certain period
    and either don't have a memory or their memory is older than their last update.
    """
    inactivity_threshold = datetime.utcnow() - timedelta(hours=settings.MEMORY_INACTIVITY_THRESHOLD_HOURS)

    # Find conversations that were updated before the threshold
    # and either have no memory or the memory is older than the last conversation update.
    conversations_to_process = (
        db.query(Conversation)
        .outerjoin(ConversationMemory, Conversation.id == ConversationMemory.conversation_id)
        .filter(
            Conversation.updated_at < inactivity_threshold,
            and_(Conversation.updated_at > Conversation.created_at), # Exclude new, empty conversations
            (ConversationMemory.id == None) | (ConversationMemory.updated_at < Conversation.updated_at)
        )
        .all()
    )
    
    return [c.id for c in conversations_to_process]

def get_users_needing_persona_generation(db: Session) -> List[int]:
    """
    Returns a list of user IDs who need their persona generated or updated.
    """
    # 1. Users with an existing persona but newer memories
    users_to_update = (
        db.query(User.id)
        .join(UserPersona)
        .join(Conversation, User.id == Conversation.user_id)
        .join(ConversationMemory, Conversation.id == ConversationMemory.conversation_id)
        .group_by(User.id, UserPersona.updated_at)
        .having(func.max(ConversationMemory.created_at) > UserPersona.updated_at)
        .all()
    )

    # 2. Users with memories but no persona
    users_to_create = (
        db.query(User.id)
        .join(Conversation, User.id == Conversation.user_id)
        .join(ConversationMemory, Conversation.id == ConversationMemory.conversation_id)
        .outerjoin(UserPersona, User.id == UserPersona.user_id)
        .filter(UserPersona.id == None)
        .group_by(User.id)
        .all()
    )

    # Combine and get unique user IDs
    user_ids_to_update = {u[0] for u in users_to_update}
    user_ids_to_create = {u[0] for u in users_to_create}
    
    return list(user_ids_to_update.union(user_ids_to_create))

def save_message_pipeline_data(db: Session, message_id: int, pipeline_data_dict: dict) -> MessagePipelineData:
    """Saves pipeline data for a specific message."""
    db_pipeline_data = MessagePipelineData(message_id=message_id, pipeline_data=pipeline_data_dict)
    db.add(db_pipeline_data)
    db.commit()
    db.refresh(db_pipeline_data)
    return db_pipeline_data