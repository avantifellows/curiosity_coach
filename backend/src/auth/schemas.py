from pydantic import BaseModel, field_validator, ConfigDict
import re
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    identifier: str
    
    @field_validator('identifier')
    @classmethod
    def validate_identifier(cls, v):
        if not v or not v.strip():
            raise ValueError('Identifier cannot be empty')
        
        # If it looks like a phone number, validate it
        if v.isdigit() and 10 <= len(v) <= 15:
            if not re.match(r'^\d{10,15}$', v):
                raise ValueError('Invalid phone number. Please enter a 10-15 digit number.')
        
        return v.strip()

# Keep old schema for backward compatibility
class PhoneNumberRequest(BaseModel):
    phone_number: str
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        if not re.match(r'^\d{10,15}$', v):
            raise ValueError('Invalid phone number. Please enter a 10-15 digit number.')
        return v

class UserResponse(BaseModel):
    id: int
    phone_number: Optional[str] = None
    name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[UserResponse] = None
    generated_name: Optional[str] = None  # For name-based logins to show the generated ID

class StudentLoginRequest(BaseModel):
    school: str
    grade: int
    section: Optional[str] = None
    roll_number: int
    first_name: str

    @field_validator('school')
    @classmethod
    def validate_school(cls, v):
        if not v or not v.strip():
            raise ValueError('School cannot be empty')
        return v.strip()

    @field_validator('grade')
    @classmethod
    def validate_grade(cls, v):
        if v < 3 or v > 10:
            raise ValueError('Grade must be between 3 and 10')
        return v

    @field_validator('section')
    @classmethod
    def validate_section(cls, v):
        if v is not None:
            v = v.strip().upper()
            if not v:
                return None
            if len(v) > 10:
                raise ValueError('Section must be 10 characters or less')
        return v

    @field_validator('roll_number')
    @classmethod
    def validate_roll_number(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Roll number must be between 1 and 100')
        return v

    @field_validator('first_name')
    @classmethod
    def validate_first_name(cls, v):
        if not v or not v.strip():
            raise ValueError('First name cannot be empty')
        return v.strip().title()

class StudentResponse(BaseModel):
    id: int
    user_id: int
    school: str
    grade: int
    section: Optional[str] = None
    roll_number: int
    first_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class StudentLoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[UserResponse] = None
    student: Optional[StudentResponse] = None 