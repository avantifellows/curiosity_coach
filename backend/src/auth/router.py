from fastapi import APIRouter, HTTPException
from src.auth.schemas import PhoneNumberRequest, LoginResponse
from src.auth.service import auth_service

router = APIRouter(
    prefix="/api/auth",
    tags=["authentication"]
)

@router.post("/login", response_model=LoginResponse)
async def login(request: PhoneNumberRequest):
    """
    Authenticate a user with a phone number.
    Creates a new user if the phone number doesn't exist.
    """
    phone_number = request.phone_number
    print(f"Received phone number: {phone_number}")
    
    try:
        # Get or create user
        user = await auth_service.login(phone_number)
        
        return {
            'success': True,
            'message': 'Login successful',
            'user': user
        }
    except Exception as e:
        print(f"Login error: {e}")
        raise HTTPException(status_code=500, detail=f"Error during login: {str(e)}") 