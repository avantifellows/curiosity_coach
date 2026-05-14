from typing import List, Optional

from src.core.chat_controller import get_conversation_core_theme
from src.services.api_service import api_service
from src.services.llm_service import LLMService
from src.utils.logger import logger


CHAT_CONTROLLER_13YO_PROMPT_NAME = "chat_controller_13yo"


async def control_and_adapt_response_for_13_year_old(
    conversation_id: int,
    original_response: str,
    user_query: str,
    current_conversation: Optional[str] = None,
    exploration_directions: Optional[List[str]] = None,
    core_theme: Optional[str] = None,
) -> dict:
    """
    One foreground pass that combines legacy chat control and 13-year-old adaptation.

    The prompt lives in the prompt DB as `chat_controller_13yo`.
    """
    try:
        resolved_core_theme = core_theme
        if resolved_core_theme is None:
            resolved_core_theme = await get_conversation_core_theme(conversation_id)

        prompt_template = await api_service.get_prompt_template(
            CHAT_CONTROLLER_13YO_PROMPT_NAME,
            prefer_production=False,
        )
        if not prompt_template:
            logger.error("Could not fetch chat_controller_13yo prompt template")
            return {
                "original_response": original_response,
                "controlled_response": original_response,
                "combined_response": original_response,
                "chat_controller_applied": False,
                "age_adapter_applied": False,
                "combined_controller_applied": False,
                "core_theme": resolved_core_theme,
                "chat_controller_prompt": None,
                "combined_prompt": None,
                "error": "Could not fetch chat_controller_13yo prompt template",
            }

        final_prompt = prompt_template.replace(
            "{{CORE_THEME}}",
            resolved_core_theme or "No current theme as such",
        )
        final_prompt = final_prompt.replace("{{USER_QUERY}}", user_query)
        final_prompt = final_prompt.replace("{{QUERY_RESPONSE}}", original_response)

        if exploration_directions:
            final_prompt = final_prompt.replace(
                "{{EXPLORATION_DIRECTIONS}}",
                ", ".join(exploration_directions),
            )
        else:
            final_prompt = final_prompt.replace(
                "{{EXPLORATION_DIRECTIONS}}",
                "No exploration directions available",
            )

        if current_conversation:
            final_prompt = final_prompt.replace("{{CURRENT_CONVERSATION}}", current_conversation)
        else:
            final_prompt = final_prompt.replace(
                "{{CURRENT_CONVERSATION}}",
                "No conversation history available.",
            )

        response = LLMService().generate_response(
            final_prompt=final_prompt,
            call_type="chat_controller_13yo",
            json_mode=False,
        )
        combined_response = response.get("raw_response", "").strip()

        if not combined_response:
            logger.warning(
                "Combined chat controller returned empty response for conversation %s",
                conversation_id,
            )
            return {
                "original_response": original_response,
                "controlled_response": original_response,
                "combined_response": original_response,
                "chat_controller_applied": False,
                "age_adapter_applied": False,
                "combined_controller_applied": False,
                "core_theme": resolved_core_theme,
                "chat_controller_prompt": final_prompt,
                "combined_prompt": final_prompt,
                "error": "Empty response from LLM",
            }

        return {
            "original_response": original_response,
            "controlled_response": combined_response,
            "combined_response": combined_response,
            "chat_controller_applied": True,
            "age_adapter_applied": True,
            "combined_controller_applied": True,
            "core_theme": resolved_core_theme,
            "chat_controller_prompt": final_prompt,
            "combined_prompt": final_prompt,
            "error": None,
        }

    except Exception as exc:
        logger.error(
            "Error in combined chat controller / 13yo adapter for conversation %s: %s",
            conversation_id,
            exc,
            exc_info=True,
        )
        return {
            "original_response": original_response,
            "controlled_response": original_response,
            "combined_response": original_response,
            "chat_controller_applied": False,
            "age_adapter_applied": False,
            "combined_controller_applied": False,
            "core_theme": None,
            "chat_controller_prompt": None,
            "combined_prompt": None,
            "error": str(exc),
        }
