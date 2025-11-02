from src.models import (
    get_or_create_user, get_or_create_user_by_identifier,
    get_or_create_student, get_student_by_user_id,
    User, Student
)
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

    @staticmethod
    async def login_with_student(
        db: Session,
        school: str,
        grade: int,
        section: Optional[str],
        roll_number: int,
        first_name: str
    ) -> Tuple[User, Student]:
        """
        Authenticate a student with their credentials.
        Creates a new user and student profile if they don't exist.

        Args:
            db (Session): The database session.
            school (str): School name
            grade (int): Grade (3-10)
            section (Optional[str]): Section (A, B, C, etc.)
            roll_number (int): Roll number in class
            first_name (str): Student's first name

        Returns:
            Tuple[User, Student]: User and Student objects
        """
        user = get_or_create_student(db, school, grade, section, roll_number, first_name)
        student = get_student_by_user_id(db, user.id)
        return user, student

auth_service = AuthService() 