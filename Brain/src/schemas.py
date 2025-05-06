from typing import Optional, Dict, Any, List, Union, Literal
from pydantic import BaseModel

# Pydantic models for process_query response
class IntentSubject(BaseModel):
    main_topic: Optional[str]
    related_topics: List[str]

class IntentRawResult(BaseModel):
    subject: IntentSubject
    intents: Dict[str, Optional[Any]]

class IntentStepData(BaseModel):
    name: Literal["intent_identification"]
    enabled: bool
    prompt: str
    raw_result: IntentRawResult
    main_topic: Optional[str]
    related_topics: List[str]

class KnowledgeStepData(BaseModel):
    name: Literal["knowledge_retrieval"]
    enabled: bool
    prompt: str
    result: str # Assuming context_info is a string

class InitialResponseStepData(BaseModel):
    name: Literal["initial_response_generation"]
    enabled: bool
    prompt: str
    result: str # Assuming initial_response is a string

class LearningEnhancementStepData(BaseModel):
    name: Literal["learning_enhancement"]
    enabled: bool
    prompt: Optional[str]
    result: Optional[str] # Assuming enhanced_response_val is a string

PipelineStepData = Union[IntentStepData, KnowledgeStepData, InitialResponseStepData, LearningEnhancementStepData]

class PipelineData(BaseModel):
    query: str
    config_used: Dict[str, Any] # Assuming FlowConfig().model_dump() is Dict[str, Any]
    steps: List[PipelineStepData]
    final_response: str # Assuming final_response is a string

class ProcessQueryResponse(BaseModel):
    response: str
    pipeline_data: PipelineData 