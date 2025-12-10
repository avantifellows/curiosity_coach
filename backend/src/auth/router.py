from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from src.auth.schemas import (
    PhoneNumberRequest, LoginRequest, LoginResponse, UserResponse,
    StudentLoginRequest, StudentLoginResponse, StudentResponse
)
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
    For names, generates a unique name with random digits.
    """
    identifier = request.identifier
    
    try:
        # Get or create user with new identifier-based method
        user: User
        generated_name: str
        user, generated_name = await auth_service.login_with_identifier(db=db, identifier=identifier)
        
        return {
            'success': True,
            'message': 'Login successful',
            'user': user,
            'generated_name': generated_name
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
async def read_users_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Fetch the details of the currently authenticated user.
    Relies on the get_current_user dependency to validate the token
    and retrieve the user. Includes student profile if user is a student.
    """
    from src.models import get_student_by_user_id

    # Fetch student profile if exists
    student = get_student_by_user_id(db, current_user.id)

    # Create response dict
    user_data = {
        "id": current_user.id,
        "phone_number": current_user.phone_number,
        "name": current_user.name,
        "created_at": current_user.created_at,
        "student": student
    }

    return user_data

@router.post("/student/login", response_model=StudentLoginResponse)
async def login_with_student(request: StudentLoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a student with their school, grade, section, roll number, and first name.
    Creates a new user and student profile if the student doesn't exist.
    """
    try:
        # Get or create student
        user, student = await auth_service.login_with_student(
            db=db,
            school=request.school,
            grade=request.grade,
            section=request.section,
            roll_number=request.roll_number,
            first_name=request.first_name
        )

        return {
            'success': True,
            'message': 'Student login successful',
            'user': user,
            'student': student
        }
    except Exception as e:
        print(f"Student login error: {e}")
        raise HTTPException(status_code=500, detail=f"Error during student login: {str(e)}") 