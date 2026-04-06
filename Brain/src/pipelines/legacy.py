from typing import Any

from src.core.age_adapter import generate_response_for_13_year_old
from src.core.chat_controller import control_chat_response
from src.core.exploration_directions_config import EXPLORATION_DIRECTIONS_ENABLED
from src.core.exploration_directions_evaluator import evaluate_exploration_directions
from src.core.turn_context import TurnExecutionContext
from src.schemas import ProcessQueryResponse
from src.utils.logger import logger

from src.pipelines.common import (
    ASSIGNED_PROMPT,
    append_pipeline_step,
    build_history_with_latest_turn,
    ensure_pipeline_metadata,
    run_common_steps,
)

TURN_PROMPT_POLICY = ASSIGNED_PROMPT


async def execute_turn(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
    user_input: str,
    current_curiosity_score: int,
) -> int:
    updated_curiosity_score = current_curiosity_score

    await run_common_steps(
        message=message,
        response_data=response_data,
        turn_context=turn_context,
    )

    if message.conversation_id and response_data:
        try:
            chat_controller_result = await control_chat_response(
                conversation_id=int(message.conversation_id),
                original_response=response_data.final_response,
                user_query=user_input,
                current_conversation=turn_context.conversation_history,
                exploration_directions=turn_context.previous_exploration_directions,
                core_theme=turn_context.core_theme,
            )
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
            }
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
            simplify_result = await generate_response_for_13_year_old(response_data.final_response)
            response_data.final_response = simplify_result.get("simplified_response", response_data.final_response)

            step = {
                "name": "response_for_13_year_old",
                "enabled": True,
                "prompt": simplify_result.get("prompt", ""),
                "result": simplify_result.get("simplified_response", ""),
                "original_response": simplify_result.get("original_response", ""),
                "applied": simplify_result.get("applied", False),
                "error": simplify_result.get("error", None),
            }
            append_pipeline_step(
                response_data,
                step,
                pipeline_key="response_for_13_year_old",
                pipeline_payload=simplify_result,
            )
        except Exception as exc:
            logger.error(f"Error applying 13-year-old simplification: {exc}", exc_info=True)

    if (
        message.conversation_id
        and message.purpose in ["chat", "test-prompt"]
        and EXPLORATION_DIRECTIONS_ENABLED
    ):
        try:
            conversation_history_with_latest = build_history_with_latest_turn(
                turn_context.prefetched_history,
                user_input,
                response_data.final_response,
            )
            user_message_count = sum(
                1 for msg in conversation_history_with_latest if msg.get("is_user", False)
            )

            if user_message_count >= 2:
                exploration_data = await evaluate_exploration_directions(
                    conversation_id=int(message.conversation_id),
                    core_theme=turn_context.core_theme,
                    conversation_history=conversation_history_with_latest,
                    current_query=user_input,
                    current_curiosity_score=current_curiosity_score,
                )

                if exploration_data and (
                    exploration_data.get("directions")
                    or exploration_data.get("curiosity_score") is not None
                ):
                    exploration_directions_list = exploration_data.get("directions", [])
                    exploration_step = {
                        "name": "exploration_directions_evaluation",
                        "enabled": True,
                        "prompt": exploration_data.get("prompt", ""),
                        "result": ", ".join(exploration_directions_list or []),
                        "directions": exploration_directions_list or [],
                        "core_theme": exploration_data.get("core_theme", turn_context.core_theme or ""),
                        "evaluation_successful": exploration_data.get("evaluation_successful", False),
                        "curiosity_score": exploration_data.get("curiosity_score"),
                        "curiosity_reason": exploration_data.get("curiosity_reason"),
                        "curiosity_tip": exploration_data.get("curiosity_tip"),
                        "curiosity_error": exploration_data.get("curiosity_error"),
                    }
                    curiosity_score_step = {
                        "prompt": exploration_data.get("prompt"),
                        "raw_response": exploration_data.get("raw_response"),
                        "curiosity_score": exploration_data.get("curiosity_score"),
                        "reason": exploration_data.get("curiosity_reason"),
                        "applied": exploration_data.get("curiosity_score") is not None,
                        "error": exploration_data.get("curiosity_error"),
                    }
                    append_pipeline_step(
                        response_data,
                        exploration_step,
                        pipeline_key="exploration_directions_evaluation",
                        pipeline_payload=exploration_data,
                    )
                    ensure_pipeline_metadata(response_data)["curiosity_score_evaluation"] = curiosity_score_step

                    curiosity_score = exploration_data.get("curiosity_score")
                    if isinstance(curiosity_score, int):
                        response_data.curiosity_score = curiosity_score
                        updated_curiosity_score = curiosity_score
        except Exception as exc:
            logger.error(
                f"Error in exploration directions evaluation for conversation {message.conversation_id}: {exc}",
                exc_info=True,
            )

    return updated_curiosity_score
