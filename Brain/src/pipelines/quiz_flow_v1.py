from typing import Any

from src.core.turn_context import TurnExecutionContext
from src.pipelines.common import ensure_pipeline_metadata, named_prompt
from src.schemas import ProcessQueryResponse

TURN_PROMPT_POLICY = named_prompt("section_quiz_master", prefer_production=False)
OPENING_PROMPT_POLICY = named_prompt("section_quiz_master", prefer_production=False)


async def execute_turn(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
    user_input: str,
    current_curiosity_score: int,
) -> int:
    """
    Section quiz mode.

    The section_quiz_master prompt owns quiz pacing and scoring behavior.
    This pipeline keeps the foreground path to one prompt and lets async
    observers run after the student gets a reply.
    """
    pipeline_metadata = ensure_pipeline_metadata(response_data)
    pipeline_metadata["async_observers_enabled"] = True
    pipeline_metadata["foreground_policy"] = (
        "single_quiz_prompt; section_core_theme_provided; "
        "exploration_score_async"
    )
    pipeline_metadata["quiz_flow_scope"] = "project_section_quiz_time"
    return current_curiosity_score
