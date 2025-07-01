from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any

class UserPersonaBase(BaseModel):
    user_id: int
    persona_data: Dict[str, Any]

class UserPersonaCreate(UserPersonaBase):
    pass

class UserPersona(UserPersonaBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True 