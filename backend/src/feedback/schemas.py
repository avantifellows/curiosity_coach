from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any


class FeedbackBase(BaseModel):
    feedback_data: Dict[str, Any]


class FeedbackCreate(FeedbackBase):
    pass


class FeedbackRead(FeedbackBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True 