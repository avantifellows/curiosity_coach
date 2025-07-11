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