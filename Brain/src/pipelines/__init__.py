import importlib
from types import ModuleType
from typing import Any, Optional

from src.core.turn_context import PromptExecutionContext, TurnExecutionContext
from src.schemas import ProcessQueryResponse
from src.utils.logger import logger

from src.pipelines.common import DEFAULT_PIPELINE_KEY, ensure_pipeline_metadata, normalize_pipeline_key


def _load_pipeline_module(pipeline_key: Optional[str]) -> ModuleType:
    normalized_key = normalize_pipeline_key(pipeline_key)
    module_name = f"src.pipelines.{normalized_key}"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError:
        if normalized_key != DEFAULT_PIPELINE_KEY:
            logger.warning(
                f"Pipeline module '{module_name}' not found. Falling back to '{DEFAULT_PIPELINE_KEY}'."
            )
            return importlib.import_module(f"src.pipelines.{DEFAULT_PIPELINE_KEY}")
        raise


async def prepare_turn_system(
    *,
    message: Any,
    turn_context: TurnExecutionContext,
    user_input: str,
) -> TurnExecutionContext:
    pipeline_key = normalize_pipeline_key(turn_context.pipeline_key)
    turn_context.pipeline_key = pipeline_key

    module = _load_pipeline_module(pipeline_key)
    prepare_turn = getattr(module, "prepare_turn", None)
    if prepare_turn is None:
        return turn_context

    logger.info(
        f"Preparing pipeline '{pipeline_key}' for conversation_id={turn_context.conversation_id}"
    )
    updated_context = await prepare_turn(
        message=message,
        turn_context=turn_context,
        user_input=user_input,
    )
    return updated_context or turn_context


async def execute_turn_system(
    *,
    message: Any,
    response_data: ProcessQueryResponse,
    turn_context: TurnExecutionContext,
    user_input: str,
    current_curiosity_score: int,
) -> int:
    pipeline_key = normalize_pipeline_key(turn_context.pipeline_key)
    turn_context.pipeline_key = pipeline_key

    pipeline_metadata = ensure_pipeline_metadata(response_data)
    pipeline_metadata["pipeline_key"] = pipeline_key
    logger.info(
        f"Executing pipeline '{pipeline_key}' for conversation_id={turn_context.conversation_id}"
    )

    module = _load_pipeline_module(pipeline_key)
    return await module.execute_turn(
        message=message,
        response_data=response_data,
        turn_context=turn_context,
        user_input=user_input,
        current_curiosity_score=current_curiosity_score,
    )


async def apply_pipeline_prompt_override(
    *,
    pipeline_key: Optional[str],
    prompt_context: PromptExecutionContext,
) -> PromptExecutionContext:
    module = _load_pipeline_module(pipeline_key)
    return await module.resolve_prompt_context(prompt_context=prompt_context)


async def apply_pipeline_opening_prompt_override(
    *,
    pipeline_key: Optional[str],
    prompt_context: PromptExecutionContext,
) -> PromptExecutionContext:
    module = _load_pipeline_module(pipeline_key)
    resolve_opening_prompt_context = getattr(module, "resolve_opening_prompt_context", None)
    if resolve_opening_prompt_context is None:
        return await module.resolve_prompt_context(prompt_context=prompt_context)
    return await resolve_opening_prompt_context(prompt_context=prompt_context)


__all__ = [
    "apply_pipeline_prompt_override",
    "apply_pipeline_opening_prompt_override",
    "prepare_turn_system",
    "execute_turn_system",
]
