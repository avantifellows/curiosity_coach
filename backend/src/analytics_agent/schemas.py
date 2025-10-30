from pydantic import BaseModel, constr
from datetime import datetime
from typing import List, Optional


class HomeworkItemIn(BaseModel):
    content: str
    status: Optional[str] = None
    remark: Optional[str] = None

class HomeworkItemsPayload(BaseModel):
    items: List[HomeworkItemIn]
    
class AnalyticsTriggerPayload(BaseModel):
    conversation_id: int
    flows: Optional[List[str]] = None
    event: Optional[str] = None  # e.g. "memory_generation"
