from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PromptExecutionContext:
    prompt_template: str
    prompt_name: str = "simplified_conversation"
    prompt_version: Optional[int] = None
    prompt_purpose: Optional[str] = None
    prompt_id: Optional[int] = None

    @property
    def requires_conversation_memory(self) -> bool:
        return "{{CONVERSATION_MEMORY" in self.prompt_template

    @property
    def requires_previous_memories(self) -> bool:
        return "{{PREVIOUS_CONVERSATIONS_MEMORY" in self.prompt_template

    @property
    def requires_core_theme(self) -> bool:
        return "{{CORE_THEME" in self.prompt_template


@dataclass
class TurnExecutionContext:
    user_input: str
    purpose: str
    conversation_id: Optional[int] = None
    user_id: Optional[int] = None
    user_created_at: Optional[str] = None
    user_name: Optional[str] = None
    pipeline_key: str = "legacy"
    conversation_history: Optional[str] = None
    prefetched_history: List[Dict[str, Any]] = field(default_factory=list)
    user_persona: Optional[Dict[str, Any]] = None
    current_curiosity_score: int = 0
    prompt_context: Optional[PromptExecutionContext] = None
    conversation_memory: Optional[Dict[str, Any]] = None
    previous_memories: Optional[List[Dict[str, Any]]] = None
    core_theme: Optional[str] = None
    previous_exploration_directions: Optional[List[str]] = None
    pipeline_state: Dict[str, Any] = field(default_factory=dict)
