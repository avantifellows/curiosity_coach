from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from src.auth.schemas import PhoneNumberRequest, LoginRequest, LoginResponse, UserResponse
from src.auth.service import auth_service
from src.database import get_db # Import the dependency
from src.models import User # Import User model for potential type hinting if needed
from src.auth.dependencies import get_current_user # Import the dependency

router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"]
)

@router.post("/login", response_model=LoginResponse)
async def login_with_identifier(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user with a phone number or name.
    Creates a new user if the identifier doesn't exist.
    For names, generates a unique username with random digits.
    """
    identifier = request.identifier
    
    try:
        # Get or create user with new identifier-based method
        user: User
        generated_username: str
        user, generated_username = await auth_service.login_with_identifier(db=db, identifier=identifier)
        
        return {
            'success': True,
            'message': 'Login successful',
            'user': user,
            'generated_username': generated_username
        }
    except Exception as e:
        print(f"Login error: {e}")
        # Consider more specific error handling
        raise HTTPException(status_code=500, detail=f"Error during login: {str(e)}")

# Keep old endpoint for backward compatibility
@router.post("/login/phone", response_model=LoginResponse)
async def login_with_phone(request: PhoneNumberRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user with a phone number (backward compatibility).
    Creates a new user if the phone number doesn't exist.
    """
    phone_number = request.phone_number
    
    try:
        # Get or create user, passing the db session
        user: User = await auth_service.login(db=db, phone_number=phone_number)
        
        return {
            'success': True,
            'message': 'Login successful',
            'user': user
        }
    except Exception as e:
        print(f"Login error: {e}")
        # Consider more specific error handling
        raise HTTPException(status_code=500, detail=f"Error during login: {str(e)}")

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    Fetch the details of the currently authenticated user.
    Relies on the get_current_user dependency to validate the token 
    and retrieve the user.
    """
    # If Depends(get_current_user) succeeds, current_user is the valid User object.
    # Pydantic will automatically serialize it based on UserResponse schema.
    return current_user 