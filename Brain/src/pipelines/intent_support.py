import re
from typing import Any, Dict, Optional
import json

from src.core.prompt_renderer import build_render_context_for_turn, render_prompt_template
from src.core.turn_context import TurnExecutionContext
from src.schemas import ProcessQueryResponse
from src.services.api_service import api_service
from src.services.llm_service import LLMService
from src.utils.logger import logger

from src.pipelines.common import prepend_pipeline_step


DEFAULT_ROUTER_PROMPT_NAME = "intent_router"
DEFAULT_INTEREST_ROUTER_PROMPT_NAME = "interest_dip_router"


async def run_intent_router(
    *,
    turn_context: TurnExecutionContext,
    user_input: str,
    router_prompt_name: str = DEFAULT_ROUTER_PROMPT_NAME,
) -> Optional[Dict[str, Any]]:
    prompt_template = await api_service.get_prompt_template(
        router_prompt_name,
        prefer_production=False,
    )
    if not prompt_template:
        return None

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

    logger.info(
        "Intent router raw output for conversation_id=%s: %s",
        turn_context.conversation_id,
        router_output,
    )

    try:
        router_data = json.loads(router_output)
    except Exception as e:
        logger.warning(
            "Failed to parse intent router output for conversation_id=%s: %s. Raw output: %s",
            turn_context.conversation_id,
            e,
            router_output,
        )
        return None

    logger.info(
        "Intent router parsed output for conversation_id=%s: mode=%s, should_ask_question=%s, topic_action=%s, question_style=%s, response_goal=%s",
        turn_context.conversation_id,
        router_data.get("mode"),
        router_data.get("should_ask_question"),
        router_data.get("topic_action"),
        router_data.get("question_style"),
        router_data.get("response_goal"),
    )

    return {
        "prompt_name": router_prompt_name,
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
        "reasoning": router_data.get("reasoning"),
    }


def prepend_intent_router_step(
    response_data: ProcessQueryResponse,
    router_state: Dict[str, Any],
) -> None:
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
        "reasoning": router_state.get("reasoning"),
    }
    prepend_pipeline_step(
        response_data,
        router_step,
        pipeline_key="intent_router",
        pipeline_payload=router_state,
    )


def build_intent_guidance_block(router_state: Dict[str, Any]) -> str:
    return (
        "Turn guidance for this message (soft guidance, not a hard mode switch):\n"
        f"- mode guess: {router_state.get('mode')}\n"
        f"- response goal: {router_state.get('response_goal')}\n"
        f"- topic action: {router_state.get('topic_action')}\n"
        f"- question style: {router_state.get('question_style')}\n"
        f"- should ask question: {router_state.get('should_ask_question')}\n"
        "\n"
        "Use this as a hint, not as rigid instructions.\n"
        "Do not abruptly switch into quiz or question mode from one weak signal alone.\n"
        "Prefer smooth continuation and natural flow unless the user strongly insists.\n"
        "Stay aligned with the current topic and the actual tone of the conversation.\n"
    )


def should_apply_intent_guidance(router_state: Dict[str, Any]) -> bool:
    mode = router_state.get("mode")
    topic_action = router_state.get("topic_action")
    should_ask_question = router_state.get("should_ask_question")

    if mode == "confusion_repair":
        return True
    if should_ask_question is False and mode == "reengagement":
        return True
    if topic_action in {"repair_current_topic", "reengage_same_topic"}:
        return True
    return False


def inject_intent_guidance(
    *,
    prompt_template: str,
    router_state: Dict[str, Any],
) -> str:
    guidance_block = build_intent_guidance_block(router_state).strip()
    if "{{INTENT_ROUTING_GUIDANCE}}" in prompt_template:
        return prompt_template.replace("{{INTENT_ROUTING_GUIDANCE}}", guidance_block)
    return f"{guidance_block}\n\n{prompt_template}"


def remove_trailing_question(
    response_text: str,
) -> str:
    if "?" not in response_text:
        return response_text

    paragraphs = response_text.split("\n\n")
    updated_paragraphs = []
    changed = False

    sentence_pattern = re.compile(r"[^.!?]*[.!?](?:\s+|$)", re.DOTALL)

    for paragraph in paragraphs:
        if "?" not in paragraph:
            updated_paragraphs.append(paragraph)
            continue

        sentences = [match.group(0).strip() for match in sentence_pattern.finditer(paragraph)]
        remainder = sentence_pattern.sub("", paragraph).strip()
        if remainder:
            sentences.append(remainder)

        kept_sentences = [sentence for sentence in sentences if "?" not in sentence]
        if len(kept_sentences) != len(sentences):
            changed = True

        if kept_sentences:
            updated_paragraphs.append(" ".join(kept_sentences).strip())

    cleaned = "\n\n".join(part for part in updated_paragraphs if part).strip()
    if changed and cleaned:
        return cleaned
    return response_text


def should_strip_trailing_question(router_state: Dict[str, Any]) -> bool:
    mode = router_state.get("mode")
    topic_action = router_state.get("topic_action")
    return mode == "confusion_repair" or topic_action == "repair_current_topic"


async def run_interest_router(
    *,
    turn_context: TurnExecutionContext,
    user_input: str,
    router_prompt_name: str = DEFAULT_INTEREST_ROUTER_PROMPT_NAME,
) -> Optional[Dict[str, Any]]:
    prompt_template = await api_service.get_prompt_template(
        router_prompt_name,
        prefer_production=False,
    )
    if not prompt_template:
        return None

    formatted_prompt = render_prompt_template(
        prompt_template,
        context=build_render_context_for_turn(turn_context, query=user_input or ""),
    )

    logger.info(
        "Prepared interest router prompt for conversation_id=%s (length=%s)",
        turn_context.conversation_id,
        len(formatted_prompt),
    )

    llm_service = LLMService()
    messages = [
        {
            "role": "system",
            "content": "You detect significant dips in student interest. Return only the JSON requested in the prompt.",
        },
        {
            "role": "user",
            "content": formatted_prompt,
        },
    ]

    router_output = llm_service.get_completion(messages, call_type="intent_router")

    logger.info(
        "Interest router raw output for conversation_id=%s: %s",
        turn_context.conversation_id,
        router_output,
    )

    try:
        router_data = json.loads(router_output)
    except Exception as exc:
        logger.warning(
            "Failed to parse interest router output for conversation_id=%s: %s. Raw output: %s",
            turn_context.conversation_id,
            exc,
            router_output,
        )
        return None

    has_significant_dip = bool(router_data.get("has_significant_dip"))
    switch_away_from_legacy = router_data.get("switch_away_from_legacy")
    if switch_away_from_legacy is None:
        switch_away_from_legacy = has_significant_dip
    else:
        switch_away_from_legacy = bool(switch_away_from_legacy)

    logger.info(
        "Interest router parsed output for conversation_id=%s: has_significant_dip=%s, switch_away_from_legacy=%s, reason=%s",
        turn_context.conversation_id,
        has_significant_dip,
        switch_away_from_legacy,
        router_data.get("reason"),
    )

    return {
        "prompt_name": router_prompt_name,
        "prompt_template": prompt_template,
        "formatted_prompt": formatted_prompt,
        "raw_output": router_output,
        "parsed_output": router_data,
        "has_significant_dip": has_significant_dip,
        "switch_away_from_legacy": switch_away_from_legacy,
        "reason": router_data.get("reason") or "unclear",
        "reasoning": router_data.get("reasoning"),
        "signals": router_data.get("signals"),
        "check_in_question": router_data.get("check_in_question")
        or "Feels like I may be losing you a bit — what’s not working right now?",
    }


def prepend_interest_router_step(
    response_data: ProcessQueryResponse,
    router_state: Dict[str, Any],
) -> None:
    router_step = {
        "name": "interest_router",
        "enabled": True,
        "prompt_name": router_state.get("prompt_name"),
        "prompt_template": router_state.get("prompt_template"),
        "formatted_prompt": router_state.get("formatted_prompt"),
        "prompt": router_state.get("formatted_prompt"),
        "raw_result": router_state.get("raw_output"),
        "result": json.dumps(router_state.get("parsed_output", {}), ensure_ascii=True),
        "has_significant_dip": router_state.get("has_significant_dip"),
        "switch_away_from_legacy": router_state.get("switch_away_from_legacy"),
        "reason": router_state.get("reason"),
        "reasoning": router_state.get("reasoning"),
        "signals": router_state.get("signals"),
        "check_in_question": router_state.get("check_in_question"),
    }
    prepend_pipeline_step(
        response_data,
        router_step,
        pipeline_key="interest_router",
        pipeline_payload=router_state,
    )


def build_interest_check_prompt(
    router_state: Dict[str, Any],
) -> str:
    return (
        "You are a curiosity coach.\n"
        "For this one turn, do not continue the teaching flow.\n"
        "The student seems to have significantly lost interest.\n\n"
        f"Likely reason: {router_state.get('reason')}\n"
        f"Why: {router_state.get('reasoning') or 'Not specified.'}\n"
        f"Signals: {router_state.get('signals') or 'Not specified.'}\n"
        f"Suggested question: {router_state.get('check_in_question')}\n\n"
        "Write exactly one short, low-pressure, contextual question to understand why.\n"
        "Do not explain the topic.\n"
        "Do not quiz.\n"
        "Do not ask more than one question.\n"
        "Do not say the student lost interest.\n"
        "Return only the question.\n"
    )
