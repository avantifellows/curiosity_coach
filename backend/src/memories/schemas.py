from pydantic import BaseModel
from typing import Any, Dict

class MemoryBase(BaseModel):
    memory_data: Dict[str, Any]

class MemoryCreate(MemoryBase):
    conversation_id: int

class MemoryUpdate(MemoryBase):
    pass

class MemoryInDB(MemoryBase):
    id: int
    conversation_id: int
    
    class Config:
        from_attributes = True 