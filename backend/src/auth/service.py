from src.models import get_or_create_user, User
from sqlalchemy.orm import Session

class AuthService:
    """Service for handling authentication and user operations."""
    
    @staticmethod
    async def login(db: Session, phone_number: str) -> User:
        """
        Authenticate a user with a phone number using SQLAlchemy session.
        
        Args:
            db (Session): The database session.
            phone_number (str): The user's phone number
            
        Returns:
            User: SQLAlchemy User object
        """
        # Use the refactored function from models.py
        return get_or_create_user(db, phone_number)

auth_service = AuthService() 