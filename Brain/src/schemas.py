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
    intent_category: Optional[str] = Field(None, description="The category of intent: 'educational', 'clarification', 'greeting', 'administrative', etc.")

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

# Add SimplifiedConversationStepData model
class SimplifiedConversationStepData(BaseModel):
    name: Literal["simplified_conversation"]
    enabled: bool
    prompt: Optional[str] = None
    result: Optional[str] = None
    response_data: Optional[Dict[str, Any]] = None
    needs_clarification: bool = False

PipelineStepData = Union[
    IntentGatheringStepData, 
    FollowUpProcessingStepData,
    KnowledgeStepData, 
    InitialResponseStepData, 
    LearningEnhancementStepData,
    SimplifiedConversationStepData  # Add to the union
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

# --- Conversation Memory Schemas ---

class TopicDiscussed(BaseModel):
    topic: str = Field(..., description="The main educational topic.")
    keywords: List[str] = Field(..., description="List of key technical or conceptual terms.")
    student_initial_knowledge: str = Field(..., description="What the student knew or believed at the start.")
    key_learnings: List[str] = Field(..., description="Main concepts the student learned.")

class InferredInterest(BaseModel):
    interest: str = Field(..., description="Inferred underlying interest of the student.")
    confidence_score: float = Field(..., description="Confidence score (0.0 to 1.0) for the inference.")
    evidence: str = Field(..., description="Evidence from the conversation supporting the inference.")

class StudentProfileInsights(BaseModel):
    inferred_interests: List[InferredInterest]
    learning_patterns: List[str] = Field(..., description="Observations about the student's learning style.")
    personality_traits: List[str] = Field(..., description="Observed personality traits relevant to learning.")

class FutureConversationHook(BaseModel):
    hook_question: str = Field(..., description="An engaging question to ask in a future conversation.")
    related_topic: str = Field(..., description="The broader topic related to the hook question.")

class ConversationMemoryData(BaseModel):
    main_topics: List[str] = Field(..., description="List of topics that are discussed in the discussion")
    action: List[str] = Field(..., description="List of actions suggested by the AI to explore to kid")
    typical_observation: str = Field(..., description="Typical and in-depth observation about the kid")