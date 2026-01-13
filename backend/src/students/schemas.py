from __future__ import annotations

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from src.auth.schemas import StudentResponse


class ConversationMessageResponse(BaseModel):
    id: int
    content: str
    is_user: bool
    timestamp: datetime
    curiosity_score: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationTopicResponse(BaseModel):
    term: str
    weight: Optional[float] = None
    count: Optional[int] = None
    total_weight: Optional[float] = None
    conversation_count: Optional[int] = None


class ConversationEvaluationMetricsResponse(BaseModel):
    depth: Optional[float] = None
    relevant_question_count: Optional[int] = None
    topics: List[ConversationTopicResponse] = Field(default_factory=list)
    attention_span: Optional[float] = None
    avg_attention_span: Optional[float] = None
    attention_sample_size: Optional[int] = None
    total_attention_span: Optional[float] = None
    computed_at: Optional[datetime] = None
    status: Optional[str] = None
    prompt_version_id: Optional[int] = None
    depth_sample_size: Optional[int] = None
    relevant_sample_size: Optional[int] = None
    conversation_count: Optional[int] = None


class ConversationCuriositySummaryResponse(BaseModel):
    average: Optional[float] = None
    latest: Optional[int] = None
    sample_size: int = 0


class ConversationWithMessagesResponse(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[ConversationMessageResponse]
    evaluation: Optional[ConversationEvaluationMetricsResponse] = None
    curiosity_summary: Optional[ConversationCuriositySummaryResponse] = None

    model_config = ConfigDict(from_attributes=True)


class StudentWithConversationResponse(BaseModel):
    student: StudentResponse
    latest_conversation: Optional[ConversationWithMessagesResponse] = None


class PaginatedConversationsResponse(BaseModel):
    conversations: List[ConversationWithMessagesResponse]
    next_offset: Optional[int] = None


class ClassAnalysisResponse(BaseModel):
    analysis: Optional[str] = None
    status: str
    job_id: Optional[str] = None
    computed_at: Optional[datetime] = None


class AnalysisJobStatusResponse(BaseModel):
    job_id: str
    status: str
    analysis: Optional[str] = None
    computed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    analysis_status: Optional[str] = None
    metrics: Optional[dict] = None
