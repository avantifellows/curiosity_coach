from src.models import get_or_create_user

class AuthService:
    """Service for handling authentication and user operations."""
    
    @staticmethod
    async def login(phone_number: str):
        """
        Authenticate a user with a phone number.
        
        Args:
            phone_number (str): The user's phone number
            
        Returns:
            dict: User information
        """
        return get_or_create_user(phone_number)

auth_service = AuthService() 