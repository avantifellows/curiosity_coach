from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.core.turn_context import TurnExecutionContext
from src.utils.prompt_injection import (
    inject_core_theme_placeholder,
    inject_memory_placeholders,
    inject_persona_placeholders,
    inject_previous_memories_placeholder,
)


@dataclass(frozen=True)
class RenderContext:
    query: Optional[str] = None
    conversation_history: Optional[str] = None
    current_curiosity_score: Optional[int] = None
    previous_memories: Optional[list[dict[str, Any]]] = None
    user_persona: Optional[dict[str, Any]] = None
    core_theme: Optional[str] = None
    conversation_memory: Optional[dict[str, Any]] = None
    user_id: Optional[int] = None
    user_created_at: Optional[str] = None
    user_name: Optional[str] = None
    extra_vars: Optional[Dict[str, Any]] = None


def replace_extra_placeholders(
    template: str,
    extra_vars: Optional[Dict[str, Any]] = None,
) -> str:
    if not extra_vars:
        return template

    rendered = template
    for key, value in extra_vars.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", "" if value is None else str(value))
    return rendered


def render_prompt_template(
    template: str,
    *,
    context: RenderContext,
) -> str:
    rendered = template

    if context.current_curiosity_score is not None:
        bounded_score = str(max(0, min(100, context.current_curiosity_score)))
        rendered = rendered.replace("{{CURRENT_CURIOSITY_SCORE}}", bounded_score)

    rendered = rendered.replace("{{QUERY}}", context.query or "")
    rendered = rendered.replace(
        "{{CONVERSATION_HISTORY}}",
        context.conversation_history or "No previous conversation.",
    )

    if "{{PREVIOUS_CONVERSATIONS_MEMORY" in rendered:
        rendered = inject_previous_memories_placeholder(rendered, context.previous_memories)

    if "{{USER_PERSONA" in rendered:
        rendered = inject_persona_placeholders(rendered, context.user_persona)

    if "{{CORE_THEME" in rendered:
        rendered = inject_core_theme_placeholder(rendered, context.core_theme)

    if "{{CONVERSATION_MEMORY" in rendered:
        rendered = inject_memory_placeholders(rendered, context.conversation_memory)

    rendered = replace_extra_placeholders(
        rendered,
        {
            "USER_ID": context.user_id,
            "USER_CREATED_AT": context.user_created_at,
            "USER_NAME": context.user_name,
            "NAME": context.user_name,
            **(context.extra_vars or {}),
        },
    )

    return rendered


def build_render_context_for_turn(
    turn_context: TurnExecutionContext,
    *,
    query: Optional[str] = None,
    extra_vars: Optional[Dict[str, Any]] = None,
) -> RenderContext:
    return RenderContext(
        query=query,
        conversation_history=turn_context.conversation_history,
        current_curiosity_score=turn_context.current_curiosity_score,
        previous_memories=turn_context.previous_memories,
        user_persona=turn_context.user_persona,
        core_theme=turn_context.core_theme,
        conversation_memory=turn_context.conversation_memory,
        user_id=turn_context.user_id,
        user_created_at=turn_context.user_created_at,
        user_name=turn_context.user_name,
        extra_vars=extra_vars,
    )
