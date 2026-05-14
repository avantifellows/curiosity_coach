from typing import Any, Optional

from src.core.prompt_renderer import RenderContext, render_prompt_template
from src.core.turn_context import TurnExecutionContext
from src.schemas import ProcessQueryResponse
from src.services.api_service import api_service
from src.services.llm_service import LLMService
from src.utils.logger import logger

from src.pipelines.common import ASSIGNED_PROMPT, append_pipeline_step, named_prompt, run_common_steps

# First pass:
# - leave as None to reuse the conversation-assigned prompt
# - set to a prompt name if you want to pin the first pass
FIRST_PROMPT_NAME_OVERRIDE: Optional[str] = None

# Second pass:
# - leave as None to skip refinement
# - set to a prompt name if you want the second pass to come from the prompt UI
SECOND_PROMPT_NAME_OVERRIDE: Optional[str] = None

TURN_PROMPT_POLICY = (
    named_prompt(FIRST_PROMPT_NAME_OVERRIDE, prefer_production=False)
    if FIRST_PROMPT_NAME_OVERRIDE
    else ASSIGNED_PROMPT
)


async def _resolve_second_prompt_template() -> Optional[tuple[str, str]]:
    if not SECOND_PROMPT_NAME_OVERRIDE:
        return None

    prompt_template = await api_service.get_prompt_template(
        SECOND_PROMPT_NAME_OVERRIDE,
        prefer_production=False,
    )
    if not prompt_template:
        logger.warning(
            f"Could not load second-pass prompt '{SECOND_PROMPT_NAME_OVERRIDE}', "
            "skipping double prompt refinement"
        )
        return None

    return prompt_template, SECOND_PROMPT_NAME_OVERRIDE


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

    draft_response = response_data.final_response or ""
    if not draft_response.strip():
        return current_curiosity_score

    second_prompt_resolution = await _resolve_second_prompt_template()
    if not second_prompt_resolution:
        return current_curiosity_score

    second_prompt_template, second_prompt_name = second_prompt_resolution
    formatted_second_prompt = render_prompt_template(
        second_prompt_template,
        context=RenderContext(
            query=user_input or "",
            conversation_history=turn_context.conversation_history,
            current_curiosity_score=turn_context.current_curiosity_score,
            previous_memories=turn_context.previous_memories,
            user_persona=turn_context.user_persona,
            core_theme=turn_context.core_theme,
            conversation_memory=turn_context.conversation_memory,
            user_id=turn_context.user_id,
            user_created_at=turn_context.user_created_at,
            user_name=turn_context.user_name,
            extra_vars={"DRAFT_RESPONSE": draft_response},
        ),
    )

    try:
        llm_service = LLMService()
        revised_response = llm_service.get_completion(
            [
                {
                    "role": "system",
                    "content": "You refine assistant replies without changing their underlying intent.",
                },
                {
                    "role": "user",
                    "content": formatted_second_prompt,
                },
            ]
        ).strip()

        if revised_response:
            response_data.final_response = revised_response
            append_pipeline_step(
                response_data,
                {
                    "name": "double_prompt_refinement",
                    "enabled": True,
                    "prompt_template": second_prompt_template,
                    "formatted_prompt": formatted_second_prompt,
                    "prompt": formatted_second_prompt,
                    "result": revised_response,
                    "draft_response": draft_response,
                    "prompt_name": second_prompt_name,
                },
                pipeline_key="double_prompt_refinement",
                pipeline_payload={
                    "prompt_template": second_prompt_template,
                    "formatted_prompt": formatted_second_prompt,
                    "draft_response": draft_response,
                    "result": revised_response,
                    "prompt_name": second_prompt_name,
                },
            )
    except Exception as exc:
        logger.error(f"Error in double prompt refinement: {exc}", exc_info=True)

    return current_curiosity_score
