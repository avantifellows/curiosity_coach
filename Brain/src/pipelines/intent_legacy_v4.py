import time
from typing import Any

from src.core.age_adapter import generate_response_for_13_year_old
from src.core.chat_controller import control_chat_response
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
    Prod-like legacy foreground path with async observer work.

    Foreground:
    - assigned visit / steady-state prompt
    - legacy chat_controller
    - legacy response_for_13_year_old

    Async after backend callback:
    - core theme extraction
    - exploration directions
    - curiosity score
    """
    pipeline_metadata = ensure_pipeline_metadata(response_data)
    pipeline_metadata["async_observers_enabled"] = True
    pipeline_metadata["foreground_policy"] = (
        "legacy_response_then_chat_controller_then_13yo; "
        "core_theme_exploration_score_async"
    )

    if message.conversation_id and response_data:
        try:
            started_at = time.monotonic()
            chat_controller_result = await control_chat_response(
                conversation_id=int(message.conversation_id),
                original_response=response_data.final_response,
                user_query=user_input,
                current_conversation=turn_context.conversation_history,
                exploration_directions=turn_context.previous_exploration_directions,
                core_theme=turn_context.core_theme,
            )
            time_taken = time.monotonic() - started_at
            response_data.final_response = chat_controller_result["controlled_response"]
            chat_controller_step = {
                "name": "chat_controller",
                "enabled": True,
                "prompt": chat_controller_result.get("chat_controller_prompt", ""),
                "result": chat_controller_result.get("controlled_response", ""),
                "original_response": chat_controller_result.get("original_response", ""),
                "controlled_response": chat_controller_result.get("controlled_response", ""),
                "core_theme": chat_controller_result.get("core_theme", ""),
                "chat_controller_applied": chat_controller_result.get("chat_controller_applied", False),
                "error": chat_controller_result.get("error"),
                "time_taken": time_taken,
            }
            chat_controller_result["time_taken"] = time_taken
            append_pipeline_step(
                response_data,
                chat_controller_step,
                pipeline_key="chat_controller",
                pipeline_payload=chat_controller_result,
            )
        except Exception as exc:
            logger.error(
                f"Error applying chat controller for conversation {message.conversation_id}: {exc}",
                exc_info=True,
            )

    if message.experience_mode != "try":
        try:
            started_at = time.monotonic()
            simplify_result = await generate_response_for_13_year_old(response_data.final_response)
            time_taken = time.monotonic() - started_at
            response_data.final_response = simplify_result.get(
                "simplified_response",
                response_data.final_response,
            )

            step = {
                "name": "response_for_13_year_old",
                "enabled": True,
                "prompt": simplify_result.get("prompt", ""),
                "result": simplify_result.get("simplified_response", ""),
                "original_response": simplify_result.get("original_response", ""),
                "applied": simplify_result.get("applied", False),
                "error": simplify_result.get("error", None),
                "time_taken": time_taken,
            }
            simplify_result["time_taken"] = time_taken
            append_pipeline_step(
                response_data,
                step,
                pipeline_key="response_for_13_year_old",
                pipeline_payload=simplify_result,
            )
        except Exception as exc:
            logger.error(f"Error applying 13-year-old simplification: {exc}", exc_info=True)

    return current_curiosity_score
