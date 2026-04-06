from typing import Any, Optional

from src.core.turn_context import PromptExecutionContext, TurnExecutionContext
from src.schemas import ProcessQueryResponse
from src.services.api_service import api_service
from src.utils.logger import logger

from src.pipelines.common import run_common_steps

# Set this to a prompt name if this pipeline should always use one DB prompt.
# Leave as None to reuse the conversation-assigned prompt.
PROMPT_NAME_OVERRIDE: Optional[str] = "dinesh_single_prompt"


async def resolve_prompt_context(
    *,
    prompt_context: PromptExecutionContext,
) -> PromptExecutionContext:
    if not PROMPT_NAME_OVERRIDE:
        return prompt_context

    prompt_template = await api_service.get_prompt_template(
        PROMPT_NAME_OVERRIDE,
        prefer_production=False,
    )
    if not prompt_template:
        logger.warning(
            f"Could not load single_prompt prompt '{PROMPT_NAME_OVERRIDE}', "
            "falling back to conversation-assigned prompt"
        )
        return prompt_context

    logger.info(f"Using hardcoded prompt '{PROMPT_NAME_OVERRIDE}' for single_prompt pipeline")
    return PromptExecutionContext(
        prompt_template=prompt_template,
        prompt_name=PROMPT_NAME_OVERRIDE,
        prompt_version=None,
        prompt_purpose=None,
        prompt_id=None,
    )

async def prepare_turn(
    *,
    message: Any,
    turn_context: TurnExecutionContext,
    user_input: str,
  ) -> TurnExecutionContext:
    if not turn_context.prompt_context:
        return turn_context

    prompt_template = turn_context.prompt_context.prompt_template.replace(
        "{{USER_CREATED_AT}}",
        turn_context.user_created_at or "Unknown",
    )

    turn_context.prompt_context = PromptExecutionContext(
        prompt_template=prompt_template,
        prompt_name=turn_context.prompt_context.prompt_name,
        prompt_version=turn_context.prompt_context.prompt_version,
        prompt_purpose=turn_context.prompt_context.prompt_purpose,
        prompt_id=turn_context.prompt_context.prompt_id,
    )

    return turn_context

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
