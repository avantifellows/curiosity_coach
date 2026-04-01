from typing import Optional, Dict, Any, List, Union, Literal
from pydantic import BaseModel, Field

# Pydantic models for process_query response
class PipelineStepBase(BaseModel):
    enabled: bool
    prompt: Optional[str] = None
    prompt_name: Optional[str] = None
    prompt_version: Optional[int] = None
    prompt_template: Optional[str] = None
    formatted_prompt: Optional[str] = None
    result: Optional[Any] = None
    response_data: Optional[Dict[str, Any]] = None
    step_id: Optional[str] = None
    step_kind: Optional[str] = None

    model_config = {"extra": "allow"}


class SimplifiedConversationStepData(PipelineStepBase):
    name: Literal["simplified_conversation"]
    result: Optional[str] = None
    needs_clarification: bool = False

class CuriosityScoreEvaluationStepData(PipelineStepBase):
    name: Literal["curiosity_score_evaluation"]
    result: Optional[str] = None
    raw_response: Optional[str] = None
    curiosity_score: Optional[int] = None
    reason: Optional[str] = None
    applied: bool = False
    error: Optional[str] = None

class GenericPipelineStepData(PipelineStepBase):
    name: str


PipelineStepData = Union[
    SimplifiedConversationStepData,
    CuriosityScoreEvaluationStepData,
    GenericPipelineStepData,
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
    pipeline_data: Optional[Dict[str, Any]] = Field(None, description="Additional pipeline metadata and processing information")
    curiosity_score: Optional[int] = Field(None, description="Curiosity score generated for this response")
# --- Conversation Memory Schemas ---

class BoosterAttempted(BaseModel):
    category: str = Field(..., description="Name of the curiosity booster category")
    ai_evidence: str = Field(..., description="Quote from AI demonstrating the technique")
    kid_reception: str = Field(..., description="How the kid received it: strong / weak / not received")
    kid_evidence: str = Field(..., description="Quote from kid showing their response")

class CuriosityBoosters(BaseModel):
    boosters_attempted: List[BoosterAttempted] = Field(..., description="List of curiosity boosters the AI tried")
    not_attempted: List[str] = Field(..., description="List of categories not found in AI responses")
    comment: str = Field(..., description="Short summary of which strategies resonated most")

class InvitationToComeback(BaseModel):
    inviting_to_come_back: bool = Field(..., description="Whether the ending encourages the kid to return")
    category: str = Field(..., description="Type: cliffhanger / mini_challenge / kid_choice / none")
    evidence: str = Field(..., description="Exact quote from chat if found, else empty")
    comment: str = Field(..., description="Short explanation")

class KnowledgeJourney(BaseModel):
    initial_knowledge: Dict[str, str] = Field(..., description="Kid's starting knowledge by topic")
    ai_contributions: Dict[str, str] = Field(..., description="New knowledge added by AI by topic")
    missing_for_holistic_picture: Dict[str, Any] = Field(..., description="What's still missing for holistic understanding")

class LearningProfileAssessment(BaseModel):
    assessment: str = Field(..., description="Assessment value")
    evidence: str = Field(..., description="Quote supporting the assessment")
    comment: str = Field(..., description="Short explanation")

class KidLearningProfile(BaseModel):
    attention_span: LearningProfileAssessment = Field(..., description="Assessment of attention span")
    ability_to_grasp: LearningProfileAssessment = Field(..., description="Assessment of comprehension ability")
    processing_time: LearningProfileAssessment = Field(..., description="Assessment of processing speed")
    engagement_patterns: LearningProfileAssessment = Field(..., description="Assessment of engagement style")

class ConversationMemoryData(BaseModel):
    curiosity_boosters: Dict[str, Any] = Field(..., description="Analysis of curiosity-building techniques")
    invitation_to_come_back: Dict[str, Any] = Field(..., description="Analysis of re-engagement strategies")
    knowledge_journey: Dict[str, Any] = Field(..., description="Analysis of learning progression")
    kid_learning_profile: Dict[str, Any] = Field(..., description="Assessment of kid's learning characteristics")
    
    class Config:
        # Allow any extra fields for flexibility during testing
        extra = "allow"
    


# --- User Persona Schema ---
# Flexible schema to allow prompt experimentation without code changes
# Validates that persona_data is a valid dict, but doesn't enforce specific keys
class UserPersonaData(BaseModel):
    # Accept any key-value pairs for flexible prompt iteration
    class Config:
        extra = "allow"
    
    # Override __init__ to accept arbitrary dict structure
    def __init__(self, **data):
        # Just validate it's a dict with string values (most common case)
        # But allow any structure for flexibility during prompt experiments
        super().__init__(**data)


# --- Opening Message Request Schema ---
class OpeningMessageRequest(BaseModel):
    conversation_id: int = Field(..., description="ID of the conversation to generate opening message for")
    user_id: int = Field(..., description="ID of the user")
    visit_number: int = Field(..., description="Visit number (1, 2, 3, or 4+)")
    callback_url: str = Field(..., description="Backend callback URL to send the opening message")


# --- Class Analysis Request/Response Schemas ---
class ClassAnalysisRequest(BaseModel):
    all_conversations: str = Field(..., description="The formatted conversations text to replace {{ALL_CONVERSATIONS}} placeholder")
    call_type: Optional[str] = Field("class_analysis", description="Call type for LLM configuration")


class ClassAnalysisResponse(BaseModel):
    analysis: str = Field(..., description="The generated analysis text")
    status: str = Field("success", description="Status of the analysis generation")


# --- Student Analysis Request/Response Schemas ---
class StudentAnalysisRequest(BaseModel):
    all_conversations: str = Field(..., description="The formatted conversations text to replace {{ALL_CONVERSATIONS}} placeholder")
    call_type: Optional[str] = Field("student_analysis", description="Call type for LLM configuration")


class StudentAnalysisResponse(BaseModel):
    analysis: str = Field(..., description="The generated analysis text")
    status: str = Field("success", description="Status of the analysis generation")
