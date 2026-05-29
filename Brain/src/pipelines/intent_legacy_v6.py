from typing import Any, Dict, List, Optional

from src.core.turn_context import PromptExecutionContext, TurnExecutionContext
from src.pipelines.common import ASSIGNED_PROMPT, ensure_pipeline_metadata
from src.pipelines.intent_legacy_v4 import execute_turn as execute_v4_turn
from src.schemas import ProcessQueryResponse

TURN_PROMPT_POLICY = ASSIGNED_PROMPT
OPENING_PROMPT_POLICY = ASSIGNED_PROMPT


def format_async_prior_history(
    messages: List[Dict[str, Any]],
    *,
    original_message_id: Optional[Any],
    saved_message_id: int,
) -> str:
    """
    Build the history the latest-turn observer should see.

    The latest user message is supplied separately as QUERY, and the just-saved
    AI response is not useful for classifying that user turn. Keeping both out
    of CONVERSATION_HISTORY makes the async router match the old foreground
    router's point of view.
    """
    try:
        original_id_int = int(original_message_id) if original_message_id is not None else None
    except (TypeError, ValueError):
        original_id_int = None

    rows = []
    for message in messages:
        message_id = message.get("id")
        if message_id == saved_message_id:
            continue
        if original_id_int is not None and message_id == original_id_int:
            continue

        content = message.get("content")
        if content is None:
            continue

        sender = "User" if message.get("is_user", False) else "AI"
        rows.append(f"{sender}: {content}")

    return "\n".join(rows) if rows else "No previous conversation."


def build_previous_interest_guidance(router_state: Dict[str, Any]) -> str:
    interest_signal = router_state.get("interest_signal") or "unknown"
    interest_change = router_state.get("interest_change") or "unknown"
    student_intent = router_state.get("student_intent") or "unknown"
    topic_action = router_state.get("topic_action") or "stay"
    guidance_intensity = router_state.get("guidance_intensity") or "none"
    coach_note = router_state.get("coach_note") or "Continue naturally."
    reason_short = router_state.get("reason_short") or "No previous evidence available."

    return (
        "Previous-turn async interest signal. Use this as a soft continuity hint for the next reply.\n"
        f"- interest: {interest_signal} / {interest_change}\n"
        f"- previous-turn intent: {student_intent}\n"
        f"- topic action: {topic_action}\n"
        f"- guidance intensity: {guidance_intensity}\n"
        f"- note: {coach_note}\n"
        f"- evidence: {reason_short}\n\n"
        "Do not mention these labels. Do not overfit to them if the current user message points elsewhere.\n"
    )


def inject_previous_interest_guidance(prompt_template: str, router_state: Dict[str, Any]) -> str:
    guidance = build_previous_interest_guidance(router_state).strip()
    if "{{PREVIOUS_INTEREST_GUIDANCE}}" in prompt_template:
        return prompt_template.replace("{{PREVIOUS_INTEREST_GUIDANCE}}", guidance)
    return f"{guidance}\n\n{prompt_template}"


async def prepare_turn(
    *,
    message: Any,
    turn_context: TurnExecutionContext,
    user_input: str,
) -> TurnExecutionContext:
    router_state = turn_context.previous_interest_router
    if not router_state or not turn_context.prompt_context:
        return turn_context

    guided_prompt_template = inject_previous_interest_guidance(
        turn_context.prompt_context.prompt_template,
        router_state,
    )
    turn_context.prompt_context = PromptExecutionContext(
        prompt_template=guided_prompt_template,
        prompt_name=turn_context.prompt_context.prompt_name,
        prompt_version=turn_context.prompt_context.prompt_version,
        prompt_purpose=turn_context.prompt_context.prompt_purpose,
        prompt_id=turn_context.prompt_context.prompt_id,
    )
    turn_context.pipeline_state["previous_interest_guidance"] = {
        "prompt_name": "previous_interest_guidance",
        "source": "previous_async_interest_intent_router_light",
        "guidance_injected": True,
        "foreground_blocking": False,
        "router_state": router_state,
        "formatted_guidance": build_previous_interest_guidance(router_state),
    }
    return turn_context


async def execute_turn(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
    user_input: str,
    current_curiosity_score: int,
) -> int:
    """
    Fast legacy experiment:

    Foreground:
    - assigned visit / steady-state prompt
    - legacy chat_controller
    - legacy response_for_13_year_old

    Async after backend callback:
    - light interest intent router
    - core theme extraction
    - exploration directions
    - curiosity score

    This keeps the interest signal for analytics and next-turn context without
    making the current response wait for the router.
    """
    updated_score = await execute_v4_turn(
        message=message,
        response_data=response_data,
        turn_context=turn_context,
        user_input=user_input,
        current_curiosity_score=current_curiosity_score,
    )

    pipeline_metadata = ensure_pipeline_metadata(response_data)
    pipeline_metadata["async_observers_enabled"] = True
    pipeline_metadata["async_interest_router_enabled"] = True
    if "previous_interest_guidance" in turn_context.pipeline_state:
        pipeline_metadata["previous_interest_guidance"] = turn_context.pipeline_state[
            "previous_interest_guidance"
        ]
    pipeline_metadata["foreground_policy"] = (
        "legacy_response_then_chat_controller_then_13yo; "
        "interest_core_theme_exploration_score_async"
    )
    return updated_score
