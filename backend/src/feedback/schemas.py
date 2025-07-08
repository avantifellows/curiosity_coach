from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class FeedbackBase(BaseModel):
    thumbs_up: bool
    feedback_text: Optional[str] = None


class FeedbackCreate(FeedbackBase):
    pass


class FeedbackRead(FeedbackBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        orm_mode = True 