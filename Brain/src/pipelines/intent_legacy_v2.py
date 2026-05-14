import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from src.core.prompt_renderer import build_render_context_for_turn, render_prompt_template
from src.core.turn_context import PromptExecutionContext, TurnExecutionContext
from src.pipelines.common import ASSIGNED_PROMPT, prepend_pipeline_step
from src.schemas import ProcessQueryResponse
from src.services.api_service import api_service
from src.services.llm_service import LLMService
from src.utils.logger import logger


TURN_PROMPT_POLICY = ASSIGNED_PROMPT
OPENING_PROMPT_POLICY = ASSIGNED_PROMPT

ROUTER_PROMPT_NAME = "interest_intent_router_v2"
ROUTER_CALL_TYPE = "interest_intent_router_v2"
ROUTER_TIMEOUT_SECONDS = float(os.getenv("INTENT_LEGACY_V2_ROUTER_TIMEOUT_SECONDS", "5"))

INTEREST_SIGNAL_VALUES = {"high", "medium", "low", "confused", "done"}
INTEREST_CHANGE_VALUES = {"rising", "stable", "weak_dip", "strong_dip", "unclear"}
STUDENT_INTENT_VALUES = {
    "direct_answer",
    "attempted_answer",
    "deepen_current",
    "broaden_current",
    "repair_confusion",
    "switch_topic",
    "quiz_or_game",
    "playful_chat",
    "meta_check_in",
    "closure",
}
DEPTH_BREADTH_VALUES = {
    "go_deeper",
    "go_broader",
    "reground",
    "switch",
    "answer_only",
    "check_in",
}
TOPIC_ACTION_VALUES = {"stay", "branch", "switch"}
QUESTION_POLICY_VALUES = {"ask_one", "optional_question", "no_question"}


def _default_router_state(reason: str = "Router unavailable; continue normal coaching.") -> Dict[str, Any]:
    return {
        "prompt_name": ROUTER_PROMPT_NAME,
        "prompt_template": None,
        "formatted_prompt": None,
        "raw_output": None,
        "parsed_output": {},
        "interest_signal": "medium",
        "interest_change": "unclear",
        "student_intent": "deepen_current",
        "depth_breadth": "go_deeper",
        "topic_action": "stay",
        "question_policy": "ask_one",
        "response_contract": "Continue the conversation naturally and follow the student's latest message.",
        "coach_adjustment": "Keep the response short, concrete, and easy to answer.",
        "reason_short": reason,
        "check_in_question": "",
        "confidence": 0.0,
    }


def _clean_enum(value: Any, allowed: set[str], fallback: str) -> str:
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in allowed:
            return normalized
    return fallback


def _clean_text(value: Any, fallback: str = "") -> str:
    if isinstance(value, str):
        return value.strip()
    return fallback


def _clean_confidence(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    return 0.0


async def _load_router_prompt() -> Optional[str]:
    prompt_template = await api_service.get_prompt_template(
        ROUTER_PROMPT_NAME,
        prefer_production=False,
    )
    if prompt_template:
        return prompt_template

    local_prompt_path = Path(__file__).with_name("interest_intent_router_v2_prompt.md")
    try:
        return local_prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Could not load local %s prompt: %s", ROUTER_PROMPT_NAME, exc)
        return None


def _router_render_context(turn_context: TurnExecutionContext, user_input: str):
    previous_directions = turn_context.previous_exploration_directions or []
    return build_render_context_for_turn(
        turn_context,
        query=user_input or "",
        extra_vars={
            "PREVIOUS_EXPLORATION_DIRECTIONS": (
                "\n".join(f"- {direction}" for direction in previous_directions)
                if previous_directions
                else "No previous exploration directions available."
            )
        },
    )


async def run_interest_intent_router(
    *,
    turn_context: TurnExecutionContext,
    user_input: str,
) -> Dict[str, Any]:
    prompt_template = await _load_router_prompt()
    if not prompt_template:
        return _default_router_state()

    formatted_prompt = render_prompt_template(
        prompt_template,
        context=_router_render_context(turn_context, user_input),
    )

    llm_service = LLMService()
    messages = [
        {
            "role": "system",
            "content": "You route interest and intent for a curiosity coach. Return only compact JSON.",
        },
        {
            "role": "user",
            "content": formatted_prompt,
        },
    ]

    started = time.monotonic()
    try:
        raw_output = await asyncio.wait_for(
            asyncio.to_thread(llm_service.get_completion, messages, call_type=ROUTER_CALL_TYPE),
            timeout=ROUTER_TIMEOUT_SECONDS,
        )
        time_taken = time.monotonic() - started
    except asyncio.TimeoutError:
        time_taken = time.monotonic() - started
        logger.warning(
            "%s timed out after %.2fs for conversation_id=%s; using fallback router state",
            ROUTER_PROMPT_NAME,
            ROUTER_TIMEOUT_SECONDS,
            turn_context.conversation_id,
        )
        state = _default_router_state(
            f"Router timed out after {ROUTER_TIMEOUT_SECONDS:.1f}s; used safe default guidance."
        )
        state.update(
            {
                "prompt_template": prompt_template,
                "formatted_prompt": formatted_prompt,
                "time_taken": time_taken,
                "timed_out": True,
                "timeout_seconds": ROUTER_TIMEOUT_SECONDS,
            }
        )
        return state

    try:
        parsed = json.loads(raw_output)
    except Exception as exc:
        logger.warning(
            "Failed to parse %s output for conversation_id=%s: %s. Raw output: %s",
            ROUTER_PROMPT_NAME,
            turn_context.conversation_id,
            exc,
            raw_output,
        )
        state = _default_router_state("Router JSON parsing failed; continue normal coaching.")
        state.update(
            {
                "prompt_template": prompt_template,
                "formatted_prompt": formatted_prompt,
                "raw_output": raw_output,
                "time_taken": time_taken,
                "timed_out": False,
            }
        )
        return state

    state = {
        "prompt_name": ROUTER_PROMPT_NAME,
        "prompt_template": prompt_template,
        "formatted_prompt": formatted_prompt,
        "raw_output": raw_output,
        "time_taken": time_taken,
        "timed_out": False,
        "parsed_output": parsed,
        "interest_signal": _clean_enum(parsed.get("interest_signal"), INTEREST_SIGNAL_VALUES, "medium"),
        "interest_change": _clean_enum(parsed.get("interest_change"), INTEREST_CHANGE_VALUES, "unclear"),
        "student_intent": _clean_enum(parsed.get("student_intent"), STUDENT_INTENT_VALUES, "deepen_current"),
        "depth_breadth": _clean_enum(parsed.get("depth_breadth"), DEPTH_BREADTH_VALUES, "go_deeper"),
        "topic_action": _clean_enum(parsed.get("topic_action"), TOPIC_ACTION_VALUES, "stay"),
        "question_policy": _clean_enum(parsed.get("question_policy"), QUESTION_POLICY_VALUES, "ask_one"),
        "response_contract": _clean_text(
            parsed.get("response_contract"),
            "Continue naturally and follow the student's latest message.",
        ),
        "coach_adjustment": _clean_text(
            parsed.get("coach_adjustment"),
            "Keep the response short, concrete, and easy to answer.",
        ),
        "reason_short": _clean_text(parsed.get("reason_short"), "No reason provided."),
        "check_in_question": _clean_text(parsed.get("check_in_question")),
        "confidence": _clean_confidence(parsed.get("confidence")),
    }

    logger.info(
        "%s parsed for conversation_id=%s: interest=%s, change=%s, intent=%s, depth_breadth=%s, question_policy=%s, confidence=%s",
        ROUTER_PROMPT_NAME,
        turn_context.conversation_id,
        state["interest_signal"],
        state["interest_change"],
        state["student_intent"],
        state["depth_breadth"],
        state["question_policy"],
        state["confidence"],
    )
    return state


def build_generation_guidance(router_state: Dict[str, Any]) -> str:
    return (
        "Interest and intent guidance for this turn:\n"
        f"- interest signal: {router_state.get('interest_signal')}\n"
        f"- interest change: {router_state.get('interest_change')}\n"
        f"- student intent: {router_state.get('student_intent')}\n"
        f"- depth/breadth move: {router_state.get('depth_breadth')}\n"
        f"- topic action: {router_state.get('topic_action')}\n"
        f"- question policy: {router_state.get('question_policy')}\n"
        f"- response contract: {router_state.get('response_contract')}\n"
        f"- coach adjustment: {router_state.get('coach_adjustment')}\n"
        f"- evidence: {router_state.get('reason_short')}\n\n"
        "Follow this guidance as the control layer for the next answer.\n"
        "Never mention internal labels like response contract, coach adjustment, router, guidance, or curiosity hook.\n"
        "If question policy is no_question, do not end with a question.\n"
        "If question policy is optional_question, ask one natural follow-up question when the student seems medium/high interest and it follows the answer.\n"
        "If the intent is direct_answer, answer plainly first, then usually add one natural same-topic question unless question policy is no_question.\n"
        "If the intent is attempted_answer, treat the student as thinking aloud: preserve the useful idea, gently correct only what is wrong, then advance the mechanism.\n"
        "If the intent is repair_confusion, answer plainly before any curiosity move and usually avoid branching.\n"
        "If the student asks you to ask something, ask a thinking question that opens the topic deeper, not a generic recall check.\n"
        "If interest is low or the intent is meta_check_in, reduce teaching pressure and scaffold one tiny next step; ask a stop/continue check-in only if the student explicitly signals they may be done.\n"
        "Do not offer 'versions' of an answer unless the student explicitly asked for versions, choices, subtopics, or a menu.\n"
        "Do not ask the student to choose between two broad paths unless they explicitly asked for options; pick the strongest next step yourself.\n"
        "Avoid A/B questions like 'soil or air?' or 'this or that?' unless the student is confused, low-interest, or explicitly asked for choices.\n"
        "Do not use procedural phrases like 'mechanism check', 'thread hanging', 'response contract', 'curiosity hook', or 'let us drop that analogy'.\n"
        "Do not say 'are you done', 'is your brain done', or similar checkout language unless the student explicitly asks to stop.\n"
        "Do not frame a student's rough answer as a correction unless they explicitly say you were wrong.\n"
        "The curiosity move should be a natural contrast, prediction, why-question, mechanism, real-world implication, or two meaningful paths.\n"
        "Speak in a way a smart 13-year-old can understand while preserving useful subject terms.\n"
        "Prefer vivid, specific phrasing over generic GPT-ish wording. A helpful analogy is welcome when it clarifies the idea.\n"
        "Use a small warm conversational beat before the explanation when it fits; avoid sounding like a worksheet or menu.\n"
    )


def inject_generation_guidance(
    prompt_template: str,
    router_state: Dict[str, Any],
) -> str:
    guidance = build_generation_guidance(router_state).strip()
    if "{{INTEREST_INTENT_GUIDANCE}}" in prompt_template:
        return prompt_template.replace("{{INTEREST_INTENT_GUIDANCE}}", guidance)
    return f"{guidance}\n\n{prompt_template}"


async def prepare_turn(
    *,
    message: Any,
    turn_context: TurnExecutionContext,
    user_input: str,
) -> TurnExecutionContext:
    router_state = await run_interest_intent_router(
        turn_context=turn_context,
        user_input=user_input,
    )

    if not turn_context.prompt_context:
        logger.warning(
            "No prompt context found for intent_legacy_v2 conversation_id=%s",
            turn_context.conversation_id,
        )
        turn_context.pipeline_state["interest_intent_router_v2"] = router_state
        return turn_context

    guided_prompt_template = inject_generation_guidance(
        turn_context.prompt_context.prompt_template,
        router_state,
    )

    turn_context.prompt_context = PromptExecutionContext(
        prompt_template=guided_prompt_template,
        prompt_name=turn_context.prompt_context.prompt_name,
        prompt_version=turn_context.prompt_context.prompt_version,
        prompt_purpose=turn_context.prompt_context.prompt_purpose,
        prompt_id=turn_context.prompt_context.prompt_id,
    )

    turn_context.pipeline_state["interest_intent_router_v2"] = {
        **router_state,
        "response_prompt_name": turn_context.prompt_context.prompt_name,
        "response_prompt_version": turn_context.prompt_context.prompt_version,
        "response_prompt_id": turn_context.prompt_context.prompt_id,
        "response_prompt_template": guided_prompt_template,
    }
    return turn_context


def prepend_interest_intent_step(
    response_data: ProcessQueryResponse,
    router_state: Dict[str, Any],
) -> None:
    router_step = {
        "name": "interest_intent_router_v2",
        "enabled": True,
        "prompt_name": router_state.get("prompt_name"),
        "result": json.dumps(
            {
                "interest_signal": router_state.get("interest_signal"),
                "interest_change": router_state.get("interest_change"),
                "student_intent": router_state.get("student_intent"),
                "depth_breadth": router_state.get("depth_breadth"),
                "topic_action": router_state.get("topic_action"),
                "question_policy": router_state.get("question_policy"),
                "response_contract": router_state.get("response_contract"),
                "coach_adjustment": router_state.get("coach_adjustment"),
                "reason_short": router_state.get("reason_short"),
                "confidence": router_state.get("confidence"),
                "timed_out": router_state.get("timed_out", False),
                "timeout_seconds": router_state.get("timeout_seconds"),
            },
            ensure_ascii=True,
        ),
        "interest_signal": router_state.get("interest_signal"),
        "interest_change": router_state.get("interest_change"),
        "student_intent": router_state.get("student_intent"),
        "depth_breadth": router_state.get("depth_breadth"),
        "topic_action": router_state.get("topic_action"),
        "question_policy": router_state.get("question_policy"),
        "response_contract": router_state.get("response_contract"),
        "coach_adjustment": router_state.get("coach_adjustment"),
        "reason_short": router_state.get("reason_short"),
        "check_in_question": router_state.get("check_in_question"),
        "confidence": router_state.get("confidence"),
        "time_taken": router_state.get("time_taken"),
        "timed_out": router_state.get("timed_out", False),
        "timeout_seconds": router_state.get("timeout_seconds"),
    }
    prepend_pipeline_step(
        response_data,
        router_step,
        pipeline_key="interest_intent_router_v2",
        pipeline_payload=router_state,
    )


async def execute_turn(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
    user_input: str,
    current_curiosity_score: int,
) -> int:
    router_state = turn_context.pipeline_state.get("interest_intent_router_v2")
    if router_state:
        prepend_interest_intent_step(response_data, router_state)
    return current_curiosity_score
