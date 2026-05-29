import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from src.core.prompt_renderer import build_render_context_for_turn, render_prompt_template
from src.core.turn_context import PromptExecutionContext, TurnExecutionContext
from src.pipelines.common import ASSIGNED_PROMPT, prepend_pipeline_step
from src.pipelines.intent_legacy_v4 import execute_turn as execute_v4_turn
from src.schemas import ProcessQueryResponse
from src.services.api_service import api_service
from src.services.llm_service import LLMService
from src.utils.logger import logger

TURN_PROMPT_POLICY = ASSIGNED_PROMPT
OPENING_PROMPT_POLICY = ASSIGNED_PROMPT

ROUTER_PROMPT_NAME = "interest_intent_router_light"
ROUTER_CALL_TYPE = "interest_intent_router_light"
ROUTER_TIMEOUT_SECONDS = float(os.getenv("INTENT_LEGACY_V5_ROUTER_TIMEOUT_SECONDS", "5"))

INTEREST_SIGNAL_VALUES = {"high", "medium", "low", "confused", "done"}
INTEREST_CHANGE_VALUES = {"rising", "stable", "weak_dip", "strong_dip", "unclear"}
STUDENT_INTENT_VALUES = {
    "direct_answer",
    "attempted_answer",
    "deepen_current",
    "broaden_current",
    "repair_confusion",
    "switch_topic",
    "playful_chat",
    "closure",
}
TOPIC_ACTION_VALUES = {"stay", "branch", "switch"}
GUIDANCE_INTENSITY_VALUES = {"none", "light", "strong"}


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


def _default_router_state(reason: str = "Light router unavailable; use normal legacy flow.") -> Dict[str, Any]:
    return {
        "prompt_name": ROUTER_PROMPT_NAME,
        "prompt_template": None,
        "formatted_prompt": None,
        "raw_output": None,
        "parsed_output": {},
        "interest_signal": "medium",
        "interest_change": "unclear",
        "student_intent": "deepen_current",
        "topic_action": "stay",
        "guidance_intensity": "none",
        "coach_note": "Use the normal legacy prompt flow.",
        "reason_short": reason,
        "confidence": 0.0,
    }


async def _load_router_prompt() -> Optional[str]:
    prompt_template = await api_service.get_prompt_template(
        ROUTER_PROMPT_NAME,
        prefer_production=False,
    )
    if prompt_template:
        return prompt_template

    local_prompt_path = Path(__file__).with_name("interest_intent_router_light_prompt.md")
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


async def run_light_interest_router(
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
            "content": "You are a lightweight interest observer for a curiosity coach. Return only compact JSON.",
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
            f"Light router timed out after {ROUTER_TIMEOUT_SECONDS:.1f}s; used normal legacy flow."
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
    except Exception as exc:
        time_taken = time.monotonic() - started
        logger.warning(
            "%s failed for conversation_id=%s; using fallback router state: %s",
            ROUTER_PROMPT_NAME,
            turn_context.conversation_id,
            exc,
            exc_info=True,
        )
        state = _default_router_state("Light router failed; used normal legacy flow.")
        state.update(
            {
                "prompt_template": prompt_template,
                "formatted_prompt": formatted_prompt,
                "time_taken": time_taken,
                "timed_out": False,
                "error": str(exc),
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
        state = _default_router_state("Light router JSON parsing failed; used normal legacy flow.")
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
        "timeout_seconds": None,
        "parsed_output": parsed,
        "interest_signal": _clean_enum(parsed.get("interest_signal"), INTEREST_SIGNAL_VALUES, "medium"),
        "interest_change": _clean_enum(parsed.get("interest_change"), INTEREST_CHANGE_VALUES, "unclear"),
        "student_intent": _clean_enum(parsed.get("student_intent"), STUDENT_INTENT_VALUES, "deepen_current"),
        "topic_action": _clean_enum(parsed.get("topic_action"), TOPIC_ACTION_VALUES, "stay"),
        "guidance_intensity": _clean_enum(parsed.get("guidance_intensity"), GUIDANCE_INTENSITY_VALUES, "none"),
        "coach_note": _clean_text(parsed.get("coach_note"), "Use the normal legacy prompt flow."),
        "reason_short": _clean_text(parsed.get("reason_short"), "No reason provided."),
        "confidence": _clean_confidence(parsed.get("confidence")),
    }

    logger.info(
        "%s parsed for conversation_id=%s: interest=%s, change=%s, intent=%s, topic_action=%s, intensity=%s, confidence=%s",
        ROUTER_PROMPT_NAME,
        turn_context.conversation_id,
        state["interest_signal"],
        state["interest_change"],
        state["student_intent"],
        state["topic_action"],
        state["guidance_intensity"],
        state["confidence"],
    )
    return state


def build_light_generation_guidance(router_state: Dict[str, Any]) -> str:
    return (
        "Light interest guidance for this turn. Use this only as a soft hint; the main prompt still controls the response.\n"
        f"- interest: {router_state.get('interest_signal')} / {router_state.get('interest_change')}\n"
        f"- latest-turn intent: {router_state.get('student_intent')}\n"
        f"- topic action: {router_state.get('topic_action')}\n"
        f"- guidance intensity: {router_state.get('guidance_intensity')}\n"
        f"- note: {router_state.get('coach_note')}\n"
        f"- evidence: {router_state.get('reason_short')}\n\n"
        "Do not mention these labels. Do not turn this into a menu or procedural check.\n"
        "Let the later chat_controller handle detailed alignment; this hint is only for tone, pressure, and whether to answer/reground/continue.\n"
    )


def should_inject_light_guidance(router_state: Dict[str, Any]) -> bool:
    if router_state.get("timed_out"):
        return False
    if router_state.get("guidance_intensity") in {"light", "strong"}:
        return True
    return router_state.get("student_intent") in {"attempted_answer", "repair_confusion", "closure", "switch_topic"}


def inject_light_generation_guidance(
    prompt_template: str,
    router_state: Dict[str, Any],
) -> str:
    guidance = build_light_generation_guidance(router_state).strip()
    if "{{INTEREST_INTENT_LIGHT_GUIDANCE}}" in prompt_template:
        return prompt_template.replace("{{INTEREST_INTENT_LIGHT_GUIDANCE}}", guidance)
    return f"{guidance}\n\n{prompt_template}"


async def prepare_turn(
    *,
    message: Any,
    turn_context: TurnExecutionContext,
    user_input: str,
) -> TurnExecutionContext:
    router_state = await run_light_interest_router(
        turn_context=turn_context,
        user_input=user_input,
    )

    if turn_context.prompt_context and should_inject_light_guidance(router_state):
        guided_prompt_template = inject_light_generation_guidance(
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
        router_state = {
            **router_state,
            "guidance_injected": True,
            "response_prompt_name": turn_context.prompt_context.prompt_name,
            "response_prompt_version": turn_context.prompt_context.prompt_version,
            "response_prompt_id": turn_context.prompt_context.prompt_id,
            "response_prompt_template": guided_prompt_template,
        }
    else:
        router_state = {
            **router_state,
            "guidance_injected": False,
            "response_prompt_name": getattr(turn_context.prompt_context, "prompt_name", None),
            "response_prompt_version": getattr(turn_context.prompt_context, "prompt_version", None),
            "response_prompt_id": getattr(turn_context.prompt_context, "prompt_id", None),
        }

    turn_context.pipeline_state[ROUTER_PROMPT_NAME] = router_state
    return turn_context


def build_light_interest_step(router_state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "name": ROUTER_PROMPT_NAME,
        "enabled": True,
        "prompt_name": router_state.get("prompt_name"),
        "result": json.dumps(
            {
                "interest_signal": router_state.get("interest_signal"),
                "interest_change": router_state.get("interest_change"),
                "student_intent": router_state.get("student_intent"),
                "topic_action": router_state.get("topic_action"),
                "guidance_intensity": router_state.get("guidance_intensity"),
                "coach_note": router_state.get("coach_note"),
                "reason_short": router_state.get("reason_short"),
                "confidence": router_state.get("confidence"),
                "guidance_injected": router_state.get("guidance_injected", False),
                "timed_out": router_state.get("timed_out", False),
                "timeout_seconds": router_state.get("timeout_seconds"),
            },
            ensure_ascii=True,
        ),
        "interest_signal": router_state.get("interest_signal"),
        "interest_change": router_state.get("interest_change"),
        "student_intent": router_state.get("student_intent"),
        "topic_action": router_state.get("topic_action"),
        "guidance_intensity": router_state.get("guidance_intensity"),
        "coach_note": router_state.get("coach_note"),
        "reason_short": router_state.get("reason_short"),
        "confidence": router_state.get("confidence"),
        "guidance_injected": router_state.get("guidance_injected", False),
        "time_taken": router_state.get("time_taken"),
        "timed_out": router_state.get("timed_out", False),
        "timeout_seconds": router_state.get("timeout_seconds"),
    }


def prepend_light_interest_step(
    response_data: ProcessQueryResponse,
    router_state: Dict[str, Any],
) -> None:
    router_step = build_light_interest_step(router_state)
    prepend_pipeline_step(
        response_data,
        router_step,
        pipeline_key=ROUTER_PROMPT_NAME,
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
    updated_score = await execute_v4_turn(
        message=message,
        response_data=response_data,
        turn_context=turn_context,
        user_input=user_input,
        current_curiosity_score=current_curiosity_score,
    )

    router_state = turn_context.pipeline_state.get(ROUTER_PROMPT_NAME)
    if router_state:
        prepend_light_interest_step(response_data, router_state)

    return updated_score
