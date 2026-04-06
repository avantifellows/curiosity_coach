from typing import Any

from src.core.turn_context import TurnExecutionContext
from src.schemas import ProcessQueryResponse

from src.pipelines.common import named_prompt, run_common_steps

TURN_PROMPT_POLICY = named_prompt("dinesh_single_prompt", prefer_production=False)

async def execute_turn(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
    user_input: str,
    current_curiosity_score: int,
) -> int:
    await run_common_steps(
        message=message,
        response_data=response_data,
        turn_context=turn_context,
    )
    return current_curiosity_score
