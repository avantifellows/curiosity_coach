from typing import Any

from src.core.turn_context import TurnExecutionContext
from src.pipelines.common import ensure_pipeline_metadata, named_prompt
from src.schemas import ProcessQueryResponse

TURN_PROMPT_POLICY = named_prompt("tutor_mode_base", prefer_production=False)
OPENING_PROMPT_POLICY = named_prompt("tutor_mode_base", prefer_production=False)


async def execute_turn(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
    user_input: str,
    current_curiosity_score: int,
) -> int:
    """
    Tutor mode: single DB prompt (tutor_mode_base) with CONVERSATION_HISTORY and QUERY.
    query_mode on the conversation controls QUERY rendering (include / omit / opening_only).
    """
    pipeline_metadata = ensure_pipeline_metadata(response_data)
    pipeline_metadata["async_observers_enabled"] = True
    pipeline_metadata["foreground_policy"] = (
        "single_tutor_prompt; query_mode_from_conversation; exploration_score_async"
    )
    pipeline_metadata["tutor_mode_scope"] = "tutor_mode_base"
    pipeline_metadata["query_mode"] = turn_context.query_mode
    return current_curiosity_score
