from typing import Any

from src.core.prompt_renderer import replace_extra_placeholders
from src.core.turn_context import TurnExecutionContext
from src.pipelines.common import ASSIGNED_PROMPT, named_prompt
from src.pipelines.intent_support import prepend_intent_router_step, run_intent_router
from src.schemas import ProcessQueryResponse
from src.utils.logger import logger


ROUTER_PROMPT_NAME = "intent_router"
RESPONSE_PROMPT_NAME = "intent_response"
TURN_PROMPT_POLICY = named_prompt(RESPONSE_PROMPT_NAME, prefer_production=False)
OPENING_PROMPT_POLICY = ASSIGNED_PROMPT

async def prepare_turn(
    *,
    message: Any,
    turn_context: TurnExecutionContext,
    user_input: str,
) -> TurnExecutionContext:
    router_state = await run_intent_router(
        turn_context=turn_context,
        user_input=user_input,
        router_prompt_name=ROUTER_PROMPT_NAME,
    )
    if not router_state:
        return turn_context

    if not turn_context.prompt_context:
        logger.warning("No prompt context found for conversation_id=%s", turn_context.conversation_id)
        return turn_context

    response_prompt_template = replace_extra_placeholders(
        turn_context.prompt_context.prompt_template,
        {
            "INTENT_MODE": router_state.get("mode") or "direct_answer",
            "INTENT_SHOULD_ASK_QUESTION": router_state.get("should_ask_question"),
            "INTENT_RESPONSE_GOAL": router_state.get("response_goal")
            or "Answer clearly and stay on the current topic.",
            "INTENT_TOPIC_ACTION": router_state.get("topic_action") or "stay_deep",
            "INTENT_QUESTION_STYLE": router_state.get("question_style") or "none",
        },
    )
    response_prompt_name = turn_context.prompt_context.prompt_name
    response_prompt_version = turn_context.prompt_context.prompt_version
    response_prompt_id = turn_context.prompt_context.prompt_id

    turn_context.prompt_context = turn_context.prompt_context.__class__(
        prompt_template=response_prompt_template,
        prompt_name=response_prompt_name,
        prompt_version=response_prompt_version,
        prompt_purpose=turn_context.prompt_context.prompt_purpose,
        prompt_id=response_prompt_id,
    )

    turn_context.pipeline_state["intent_router"] = {
        **router_state,
        "response_prompt_name": response_prompt_name,
        "response_prompt_version": response_prompt_version,
        "response_prompt_id": response_prompt_id,
        "response_prompt_template": response_prompt_template,
    }

    logger.info("Injected intent routing placeholders into response prompt for conversation id=%s", turn_context.conversation_id)

    return turn_context

async def execute_turn(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
    user_input: str,
    current_curiosity_score: int,
) -> int:
    router_state = turn_context.pipeline_state.get("intent_router")
    if router_state:
        prepend_intent_router_step(response_data, router_state)
    return current_curiosity_score
