import time
from typing import Any

from src.core.chat_controller_13yo import control_and_adapt_response_for_13_year_old
from src.core.turn_context import TurnExecutionContext
from src.pipelines.common import (
    ASSIGNED_PROMPT,
    append_pipeline_step,
    ensure_pipeline_metadata,
)
from src.schemas import ProcessQueryResponse
from src.utils.logger import logger

TURN_PROMPT_POLICY = ASSIGNED_PROMPT
OPENING_PROMPT_POLICY = ASSIGNED_PROMPT


async def execute_turn(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
    user_input: str,
    current_curiosity_score: int,
) -> int:
    """
    Legacy-quality foreground path with v2-style async observers.

    Keep the foundational response prompt unchanged, then run one combined
    response-shaping pass:
    - assigned visit/steady-state prompt
    - combined chat_controller + response_for_13_year_old

    Core theme extraction, exploration directions, and curiosity score are
    patched after the backend callback by main.py so they do not block the reply.
    """
    updated_curiosity_score = current_curiosity_score
    pipeline_metadata = ensure_pipeline_metadata(response_data)
    pipeline_metadata["async_observers_enabled"] = True
    pipeline_metadata["foreground_policy"] = (
        "legacy_response_then_combined_chat_controller_13yo; "
        "core_theme_exploration_score_async"
    )

    if message.conversation_id and response_data:
        try:
            started_at = time.monotonic()
            combined_result = await control_and_adapt_response_for_13_year_old(
                conversation_id=int(message.conversation_id),
                original_response=response_data.final_response,
                user_query=user_input,
                current_conversation=turn_context.conversation_history,
                exploration_directions=turn_context.previous_exploration_directions,
                core_theme=turn_context.core_theme,
            )
            time_taken = time.monotonic() - started_at
            response_data.final_response = combined_result["combined_response"]
            combined_step = {
                "name": "chat_controller_13yo",
                "enabled": True,
                "prompt": combined_result.get("combined_prompt", ""),
                "result": combined_result.get("combined_response", ""),
                "original_response": combined_result.get("original_response", ""),
                "controlled_response": combined_result.get("controlled_response", ""),
                "core_theme": combined_result.get("core_theme", ""),
                "chat_controller_applied": combined_result.get("chat_controller_applied", False),
                "age_adapter_applied": combined_result.get("age_adapter_applied", False),
                "combined_controller_applied": combined_result.get("combined_controller_applied", False),
                "error": combined_result.get("error"),
                "time_taken": time_taken,
            }
            combined_result["time_taken"] = time_taken
            append_pipeline_step(
                response_data,
                combined_step,
                pipeline_key="chat_controller_13yo",
                pipeline_payload=combined_result,
            )
        except Exception as exc:
            logger.error(
                f"Error applying combined chat controller / 13yo for conversation {message.conversation_id}: {exc}",
                exc_info=True,
            )

    return updated_curiosity_score
