from typing import Any

from src.core.turn_context import TurnExecutionContext
from src.pipelines import legacy
from src.pipelines.common import ASSIGNED_PROMPT
from src.pipelines.intent_support import (
    build_interest_check_prompt,
    inject_interest_recovery_guidance,
    prepend_interest_router_step,
    run_interest_router,
)
from src.schemas import ProcessQueryResponse
from src.utils.logger import logger

TURN_PROMPT_POLICY = ASSIGNED_PROMPT
OPENING_PROMPT_POLICY = ASSIGNED_PROMPT


async def prepare_turn(
    *,
    message: Any,
    turn_context: TurnExecutionContext,
    user_input: str,
) -> TurnExecutionContext:
    router_state = await run_interest_router(
        turn_context=turn_context,
        user_input=user_input,
    )
    if not router_state:
        return turn_context

    if not turn_context.prompt_context:
        logger.warning(
            "No prompt context found for intent_legacy conversation_id=%s",
            turn_context.conversation_id,
        )
        return turn_context

    guided_prompt_template = turn_context.prompt_context.prompt_template
    recovery_action = router_state.get("recovery_action")

    if recovery_action == "meta_check_in":
        guided_prompt_template = build_interest_check_prompt(router_state)
    elif recovery_action in {
        "backtrack_and_reground",
        "answer_directly_then_continue",
        "shift_to_adjacent_topic",
    }:
        guided_prompt_template = inject_interest_recovery_guidance(
            prompt_template=guided_prompt_template,
            router_state=router_state,
        )

    response_prompt_name = turn_context.prompt_context.prompt_name
    response_prompt_version = turn_context.prompt_context.prompt_version
    response_prompt_id = turn_context.prompt_context.prompt_id
    response_prompt_purpose = turn_context.prompt_context.prompt_purpose

    if recovery_action == "meta_check_in":
        response_prompt_name = "interest_check_in"
        response_prompt_version = None
        response_prompt_id = None
        response_prompt_purpose = "interest_check_in"

    turn_context.prompt_context = turn_context.prompt_context.__class__(
        prompt_template=guided_prompt_template,
        prompt_name=response_prompt_name,
        prompt_version=response_prompt_version,
        prompt_purpose=response_prompt_purpose,
        prompt_id=response_prompt_id,
    )

    turn_context.pipeline_state["interest_router"] = {
        **router_state,
        "response_prompt_name": response_prompt_name,
        "response_prompt_version": response_prompt_version,
        "response_prompt_id": response_prompt_id,
        "response_prompt_template": guided_prompt_template,
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
    router_state = turn_context.pipeline_state.get("interest_router")
    if router_state:
        prepend_interest_router_step(response_data, router_state)
    if router_state and router_state.get("recovery_action") == "meta_check_in":
        return current_curiosity_score

    updated_curiosity_score = await legacy.execute_turn(
        message=message,
        response_data=response_data,
        turn_context=turn_context,
        user_input=user_input,
        current_curiosity_score=current_curiosity_score,
    )

    return updated_curiosity_score
