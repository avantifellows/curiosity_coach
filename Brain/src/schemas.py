from typing import Optional, Dict, Any, List, Union, Literal
from pydantic import BaseModel, Field

# Pydantic models for process_query response
class IntentSubject(BaseModel):
    main_topic: Optional[str]
    related_topics: List[str]

class IntentContext(BaseModel):
    known_information: Optional[str] = None
    motivation: Optional[str] = None
    learning_goal: Optional[str] = None

class IntentDetails(BaseModel):
    category: Optional[str] = None
    specific_type: Optional[str] = None
    confidence: Optional[float] = None

class IntentData(BaseModel):
    subject: IntentSubject
    intents: Dict[str, Optional[IntentDetails]]
    context: Optional[IntentContext] = None

class IntentGatheringStepData(BaseModel):
    name: Literal["intent_gathering"]
    enabled: bool
    result: Optional[Dict[str, Any]] = None
    main_topic: Optional[str] = None
    related_topics: Optional[List[str]] = None
    needs_clarification: bool = False

class FollowUpProcessingStepData(BaseModel):
    name: Literal["follow_up_processing"]
    enabled: bool
    result: Optional[Dict[str, Any]] = None
    main_topic: Optional[str] = None
    related_topics: Optional[List[str]] = None
    needs_clarification: bool = False

class KnowledgeStepData(BaseModel):
    name: Literal["knowledge_retrieval"]
    enabled: bool
    prompt: Optional[str] = None
    result: Optional[str] = None # Assuming context_info is a string

class InitialResponseStepData(BaseModel):
    name: Literal["initial_response_generation"]
    enabled: bool
    prompt: Optional[str] = None
    result: Optional[str] = None # Assuming initial_response is a string

class LearningEnhancementStepData(BaseModel):
    name: Literal["learning_enhancement"]
    enabled: bool
    prompt: Optional[str] = None
    result: Optional[str] = None # Assuming enhanced_response_val is a string

PipelineStepData = Union[
    IntentGatheringStepData, 
    FollowUpProcessingStepData,
    KnowledgeStepData, 
    InitialResponseStepData, 
    LearningEnhancementStepData
]

class PipelineData(BaseModel):
    query: str
    config_used: Dict[str, Any] 
    steps: List[PipelineStepData]
    final_response: Optional[str] = None
    follow_up_questions: Optional[List[str]] = None
    needs_clarification: bool = False
    partial_understanding: Optional[str] = None

class ProcessQueryResponse(BaseModel):
    query: str = Field(..., description="The original query that was processed")
    config_used: Dict[str, Any] = Field(..., description="Configuration used during processing")
    steps: List[PipelineStepData] = Field(..., description="Pipeline steps that were executed")
    final_response: Optional[str] = Field(None, description="The final response or follow-up questions")
    follow_up_questions: Optional[List[str]] = Field(None, description="List of follow-up questions if clarification is needed")
    needs_clarification: bool = Field(False, description="Whether clarification is needed from the user")
    partial_understanding: Optional[str] = Field(None, description="Partial understanding of the query when clarification is needed") 