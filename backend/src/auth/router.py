from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from src.auth.schemas import PhoneNumberRequest, LoginResponse, UserResponse
from src.auth.service import auth_service
from src.database import get_db # Import the dependency
from src.models import User # Import User model for potential type hinting if needed

router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"]
)

@router.post("/login", response_model=LoginResponse)
async def login(request: PhoneNumberRequest, db: Session = Depends(get_db)):
    """
    Authenticate a user with a phone number.
    Creates a new user if the phone number doesn't exist.
    Injects SQLAlchemy Session using Depends(get_db).
    """
    phone_number = request.phone_number
    print(f"Received phone number: {phone_number}")
    
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