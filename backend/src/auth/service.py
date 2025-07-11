from src.models import get_or_create_user, get_or_create_user_by_identifier, User
from sqlalchemy.orm import Session
from typing import Tuple, Optional

class AuthService:
    """Service for handling authentication and user operations."""
    
    @staticmethod
    async def login_with_identifier(db: Session, identifier: str) -> Tuple[User, Optional[str]]:
        """
        Authenticate a user with an identifier (phone number or name).
        
        Args:
            db (Session): The database session.
            identifier (str): The user's phone number or name
            
        Returns:
            Tuple[User, Optional[str]]: User object and generated name (if any)
        """
        return get_or_create_user_by_identifier(db, identifier)
    
    @staticmethod
    async def login(db: Session, phone_number: str) -> User:
        """
        Authenticate a user with a phone number using SQLAlchemy session.
        (Backward compatibility method)
        
        Args:
            db (Session): The database session.
            phone_number (str): The user's phone number
            
        Returns:
            User: SQLAlchemy User object
        """
        # Use the refactored function from models.py
        return get_or_create_user(db, phone_number)

auth_service = AuthService() 