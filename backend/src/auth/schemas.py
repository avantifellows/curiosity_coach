from pydantic import BaseModel, field_validator, ConfigDict
import re
from typing import Optional
from datetime import datetime

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
    phone_number: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[UserResponse] = None 