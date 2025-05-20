from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Prompt Version Schemas ---
class PromptVersionBase(BaseModel):
    prompt_text: str = Field(..., description="The text content of the prompt version.")
    version_number: Optional[int] = Field(None, description="Version number, typically auto-incremented.")

class PromptVersionCreate(PromptVersionBase):
    pass

class PromptVersionUpdate(BaseModel):
    prompt_text: Optional[str] = None
    # is_active flag is typically handled by a dedicated endpoint, not direct update here

class PromptVersionInDB(PromptVersionBase):
    id: int
    prompt_id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class PromptBase(BaseModel):
    name: str = Field(..., description="Unique name for the prompt type, e.g., 'intent_identifier'.")
    description: Optional[str] = Field(None, description="Optional description of the prompt.")

class PromptCreate(PromptBase):
    initial_version_text: Optional[str] = Field(None, description="Text for the first version of this prompt. If provided, version 1 will be created and set active.")

class PromptUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class PromptInDBBase(PromptBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PromptInDB(PromptInDBBase):
    versions: List[PromptVersionInDB] = []
    active_prompt_version: Optional[PromptVersionInDB] = None # Display the current active version

class PromptSimple(PromptInDBBase):
    # A simpler representation without all versions
    active_version_number: Optional[int] = None
    active_version_text: Optional[str] = None

# --- Schemas for specific actions ---
class SetActivePromptVersionRequest(BaseModel):
    version_id: int = Field(..., description="The ID of the PromptVersion to set as active.") 