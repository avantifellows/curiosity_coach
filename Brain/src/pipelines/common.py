from typing import Any, Dict, List, Optional

from src.core.core_theme_config import (
    CORE_THEME_EXTRACTION_ENABLED,
    CORE_THEME_TRIGGER_MESSAGE_COUNT,
)
from src.core.core_theme_extractor import (
    extract_core_theme_from_conversation,
    update_conversation_theme,
)
from src.core.turn_context import TurnExecutionContext
from src.schemas import ProcessQueryResponse
from src.services.api_service import api_service
from src.utils.logger import logger

DEFAULT_PIPELINE_KEY = "legacy"


def normalize_pipeline_key(pipeline_key: Optional[str]) -> str:
    if not pipeline_key:
        return DEFAULT_PIPELINE_KEY

    normalized = pipeline_key.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized or DEFAULT_PIPELINE_KEY


def ensure_pipeline_metadata(response_data: ProcessQueryResponse) -> Dict[str, Any]:
    if not isinstance(response_data.pipeline_data, dict):
        response_data.pipeline_data = {}
    return response_data.pipeline_data


def append_pipeline_step(
    response_data: ProcessQueryResponse,
    step: Dict[str, Any],
    *,
    pipeline_key: Optional[str] = None,
    pipeline_payload: Optional[Dict[str, Any]] = None,
) -> None:
    response_data.steps.append(step)
    pipeline_data = ensure_pipeline_metadata(response_data)
    pipeline_data.setdefault("steps", []).append(step)
    if pipeline_key:
        pipeline_data[pipeline_key] = pipeline_payload if pipeline_payload is not None else step


def build_history_with_latest_turn(
    prefetched_history: List[Dict[str, Any]],
    user_input: str,
    assistant_response: str,
) -> List[Dict[str, Any]]:
    history = [
        {
            "is_user": message.get("is_user", False),
            "content": message.get("content"),
        }
        for message in prefetched_history
        if message.get("content") is not None
    ]

    if not history or not (
        history[-1].get("is_user", False)
        and history[-1].get("content") == user_input
    ):
        history.append({"is_user": True, "content": user_input})

    if not history or not (
        history[-1].get("is_user") is False
        and history[-1].get("content") == assistant_response
    ):
        history.append({"is_user": False, "content": assistant_response})

    return history


async def run_common_steps(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
) -> None:
    if not (
        message.conversation_id
        and message.purpose in ["chat", "test-prompt"]
        and CORE_THEME_EXTRACTION_ENABLED
    ):
        return

    try:
        conversation_history = turn_context.prefetched_history or []
        if not conversation_history and message.conversation_id:
            conversation_history = await api_service.get_conversation_history(int(message.conversation_id)) or []

        if not conversation_history:
            return

        user_message_count = len(
            [msg for msg in conversation_history if msg.get("is_user", False)]
        )
        if user_message_count != CORE_THEME_TRIGGER_MESSAGE_COUNT:
            return

        logger.info(
            f"{CORE_THEME_TRIGGER_MESSAGE_COUNT}th user message detected for conversation "
            f"{message.conversation_id}. Triggering core theme extraction."
        )

        core_theme, core_theme_prompt = await extract_core_theme_from_conversation(
            int(message.conversation_id),
            conversation_history=turn_context.prefetched_history,
        )

        core_theme_step = {
            "name": "core_theme_extraction",
            "enabled": True,
            "prompt": core_theme_prompt if core_theme_prompt else "Core theme extraction prompt not available",
            "result": core_theme if core_theme else "No core theme extracted",
            "core_theme": core_theme,
            "extraction_successful": core_theme is not None,
        }
        append_pipeline_step(response_data, core_theme_step)

        if core_theme:
            success = await update_conversation_theme(int(message.conversation_id), core_theme)
            if success:
                turn_context.core_theme = core_theme
                logger.info(
                    f"Successfully updated conversation {message.conversation_id} with core theme: '{core_theme}'"
                )
    except Exception as exc:
        logger.error(
            f"Error in core theme extraction for conversation {message.conversation_id}: {exc}",
            exc_info=True,
        )
