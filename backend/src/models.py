from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship, sessionmaker, Session, declarative_base
from sqlalchemy.sql import func
from src.database import Base, get_db # Assuming Base and get_db will be defined in database.py
from fastapi import Depends

# SQLAlchemy Models
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    messages = relationship("Message", back_populates="user")

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    is_user = Column(Boolean, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="messages")


# --- CRUD Helper Functions ---

def get_or_create_user(db: Session, phone_number: str) -> User:
    """Get a user by phone number or create if not exists using SQLAlchemy."""
    user = db.query(User).filter(User.phone_number == phone_number).first()
    if not user:
        user = User(phone_number=phone_number)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def save_message(db: Session, user_id: int, content: str, is_user: bool = True) -> Message:
    """Save a message to the database using SQLAlchemy."""
    message = Message(user_id=user_id, content=content, is_user=is_user)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message

def get_message_count(db: Session, user_id: int) -> int:
    """Get the count of messages sent by a user using SQLAlchemy."""
    count = db.query(func.count(Message.id)).filter(Message.user_id == user_id, Message.is_user == True).scalar()
    return count if count is not None else 0

def get_chat_history(db: Session, user_id: int, limit: int = 50) -> list[Message]:
    """Get chat history for a user using SQLAlchemy."""
    messages = db.query(Message).filter(Message.user_id == user_id).order_by(Message.timestamp.desc()).limit(limit).all()
    # Messages are fetched in descending order, reverse to get chronological
    return list(reversed(messages))