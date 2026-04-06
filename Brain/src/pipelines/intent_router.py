
from typing import Any
import json

from src.core.prompt_renderer import (
    build_render_context_for_turn,
    render_prompt_template,
    replace_extra_placeholders,
)
from src.core.turn_context import TurnExecutionContext
from src.pipelines.common import ASSIGNED_PROMPT, named_prompt, prepend_pipeline_step
from src.schemas import ProcessQueryResponse
from src.services.api_service import api_service
from src.utils.logger import logger
from src.services.llm_service import LLMService


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
    if not ROUTER_PROMPT_NAME:
        return turn_context

    prompt_template = await api_service.get_prompt_template(
        ROUTER_PROMPT_NAME,
        prefer_production=False,
    )
    if not prompt_template:
        return turn_context

    formatted_prompt = render_prompt_template(
        prompt_template,
        context=build_render_context_for_turn(turn_context, query=user_input or ""),
    )

    logger.info(
        "Prepared intent router prompt for conversation_id=%s (length=%s)",
        turn_context.conversation_id,
        len(formatted_prompt),
    )
    logger.debug("Intent router formatted prompt:\n%s", formatted_prompt)

    llm_service = LLMService()
    messages = [
        {
            "role": "system",
            "content": "You are an intent router for a curiosity coach. Return only the routing result requested in the prompt.",
        },
        {
            "role": "user",
            "content": formatted_prompt,
        },
    ]

    router_output = llm_service.get_completion(messages, call_type="intent_router")

    logger.info("Intent router raw output for conversation_id=%s: %s", turn_context.conversation_id, router_output)

    try:
        router_data = json.loads(router_output)
    except Exception as e:
        logger.warning("Failed to parse intent router output for conversation_id=%s: %s. Raw output: %s", turn_context.conversation_id, e, router_output)
        return turn_context
    
    logger.info(
        "Intent router parsed output for conversation_id=%s: mode=%s, should_ask_question=%s, topic_action=%s, question_style=%s, response_goal=%s",
        turn_context.conversation_id,
        router_data.get("mode"),
        router_data.get("should_ask_question"),
        router_data.get("topic_action"),
        router_data.get("question_style"),
        router_data.get("response_goal"),
    )

    if not turn_context.prompt_context:
        logger.warning("No prompt context found for conversation_id=%s", turn_context.conversation_id)
        return turn_context

    response_prompt_template = replace_extra_placeholders(
        turn_context.prompt_context.prompt_template,
        {
            "INTENT_MODE": router_data.get("mode") or "direct_answer",
            "INTENT_SHOULD_ASK_QUESTION": router_data.get("should_ask_question")
            if router_data.get("should_ask_question") is not None
            else False,
            "INTENT_RESPONSE_GOAL": router_data.get("response_goal")
            or "Answer clearly and stay on the current topic.",
            "INTENT_TOPIC_ACTION": router_data.get("topic_action") or "stay_deep",
            "INTENT_QUESTION_STYLE": router_data.get("question_style") or "none",
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
        "prompt_name": ROUTER_PROMPT_NAME,
        "prompt_template": prompt_template,
        "formatted_prompt": formatted_prompt,
        "raw_output": router_output,
        "parsed_output": router_data,
        "mode": router_data.get("mode") or "direct_answer",
        "should_ask_question": router_data.get("should_ask_question")
        if router_data.get("should_ask_question") is not None
        else False,
        "response_goal": router_data.get("response_goal") or "Answer clearly and stay on the current topic.",
        "topic_action": router_data.get("topic_action") or "stay_deep",
        "question_style": router_data.get("question_style") or "none",
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
        router_step = {
            "name": "intent_router",
            "enabled": True,
            "prompt_name": router_state.get("prompt_name"),
            "prompt_template": router_state.get("prompt_template"),
            "formatted_prompt": router_state.get("formatted_prompt"),
            "prompt": router_state.get("formatted_prompt"),
            "raw_result": router_state.get("raw_output"),
            "result": json.dumps(router_state.get("parsed_output", {}), ensure_ascii=True),
            "mode": router_state.get("mode"),
            "should_ask_question": router_state.get("should_ask_question"),
            "response_goal": router_state.get("response_goal"),
            "topic_action": router_state.get("topic_action"),
            "question_style": router_state.get("question_style"),
            "response_prompt_name": router_state.get("response_prompt_name"),
            "response_prompt_version": router_state.get("response_prompt_version"),
            "response_prompt_id": router_state.get("response_prompt_id"),
        }
        prepend_pipeline_step(
            response_data,
            router_step,
            pipeline_key="intent_router",
            pipeline_payload=router_state,
        )
    return current_curiosity_score
