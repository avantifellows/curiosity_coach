from pydantic import BaseModel, field_validator
import re
from typing import Optional, Dict, Any

class PhoneNumberRequest(BaseModel):
    phone_number: str
    
    @field_validator('phone_number')
    @classmethod
    def validate_phone_number(cls, v):
        if not re.match(r'^\d{10,15}$', v):
            raise ValueError('Invalid phone number. Please enter a 10-15 digit number.')
        return v

class LoginResponse(BaseModel):
    success: bool
    message: str
    user: Optional[Dict[str, Any]] = None 