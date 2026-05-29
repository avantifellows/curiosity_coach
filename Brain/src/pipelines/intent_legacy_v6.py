from typing import Any, Dict, List, Optional

from src.core.turn_context import TurnExecutionContext
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
    pipeline_metadata["foreground_policy"] = (
        "legacy_response_then_chat_controller_then_13yo; "
        "interest_core_theme_exploration_score_async"
    )
    return updated_score
