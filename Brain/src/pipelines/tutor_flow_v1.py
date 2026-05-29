from typing import Any

from src.core.turn_context import TurnExecutionContext
from src.pipelines.common import ensure_pipeline_metadata, named_prompt
from src.schemas import ProcessQueryResponse

TURN_PROMPT_POLICY = named_prompt("tutor_flow_v1", prefer_production=False)
OPENING_PROMPT_POLICY = named_prompt("tutor_flow_v1", prefer_production=False)


async def execute_turn(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
    user_input: str,
    current_curiosity_score: int,
) -> int:
    """
    Section-scoped tutor mode.

    The prompt is responsible for pacing, scope, and topic-completion behavior.
    This pipeline keeps the visible path simple:
    - tutor_flow_v1 prompt response
    - async exploration / curiosity observer after callback

    Core theme extraction is intentionally skipped because project-section
    conversations already store the selected section context as core_theme.
    """
    pipeline_metadata = ensure_pipeline_metadata(response_data)
    pipeline_metadata["async_observers_enabled"] = True
    pipeline_metadata["foreground_policy"] = (
        "single_tutor_prompt; section_core_theme_provided; "
        "exploration_score_async"
    )
    pipeline_metadata["tutor_flow_scope"] = "project_section_timed_topic_completion"
    return current_curiosity_score
