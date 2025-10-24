import os
import httpx
from typing import Optional
from src.services.llm_service import LLMService
from src.utils.logger import logger

# Configuration
CHAT_CONTROLLER_PROMPT_NAME = "chat_controller"

async def _get_prompt_from_backend(prompt_name: str) -> Optional[str]:
    """
    Fetch prompt template from backend database.
    """
    try:
        backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
        url = f"{backend_url}/api/prompts/{prompt_name}/versions/active"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("prompt_text", "")
    except Exception as e:
        logger.error(f"Error fetching prompt {prompt_name} from backend: {e}")
        return None

async def get_conversation_core_theme(conversation_id: int) -> Optional[str]:
    """
    Fetch the core theme for a conversation from the backend.
    """
    try:
        backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
        url = f"{backend_url}/api/internal/conversations/{conversation_id}/core-theme"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("core_theme")
    except Exception as e:
        logger.error(f"Error fetching core theme for conversation {conversation_id}: {e}")
        return None

async def control_chat_response(
    conversation_id: int, 
    original_response: str, 
    user_query: str,
    current_conversation: Optional[str] = None
) -> dict:  # Change return type to dict
    """
    Controls the chat response based on the conversation's core theme.
    
    Args:
        conversation_id: The conversation ID
        original_response: The original AI response
        user_query: The user's query
        current_conversation: The conversation history
        
    Returns:
        dict: The controlled/enhanced response with metadata
    """
    try:
        # 1. Get the core theme for this conversation
        core_theme = await get_conversation_core_theme(conversation_id)
        
        if not core_theme:
            logger.info(f"No core theme found for conversation {conversation_id}, using original response")
            return {
                "original_response": original_response,
                "controlled_response": original_response,
                "chat_controller_applied": False,
                "core_theme": None,
                "chat_controller_prompt": None,
                "error": "No core theme found"
            }
        
        logger.info(f"Core theme found for conversation {conversation_id}: '{core_theme}'. Applying chat controller.")
        
        # 2. Get the chat controller prompt template
        prompt_template = await _get_prompt_from_backend(CHAT_CONTROLLER_PROMPT_NAME)
        if not prompt_template:
            logger.error(f"Could not fetch chat controller prompt template")
            return {
                "original_response": original_response,
                "controlled_response": original_response,
                "chat_controller_applied": False,
                "core_theme": core_theme,
                "chat_controller_prompt": None,
                "error": "Could not fetch prompt template"
            }
        
        # 3. Format the prompt with the required data
        final_prompt = prompt_template.replace("{{CORE_THEME}}", core_theme)
        final_prompt = final_prompt.replace("{{USER_QUERY}}", user_query)
        final_prompt = final_prompt.replace("{{QUERY_RESPONSE}}", original_response)
        
        # Add conversation history if provided
        if current_conversation:
            final_prompt = final_prompt.replace("{{CURRENT_CONVERSATION}}", current_conversation)
        else:
            final_prompt = final_prompt.replace("{{CURRENT_CONVERSATION}}", "No conversation history available.")
        
        # 4. Call LLM to get controlled response
        llm_service = LLMService()
        response = llm_service.generate_response(
            final_prompt=final_prompt,
            call_type="chat_controller",
            json_mode=False
        )
        
        controlled_response = response.get("raw_response", "").strip()
        
        if not controlled_response:
            logger.warning(f"Chat controller returned empty response for conversation {conversation_id}")
            return {
                "original_response": original_response,
                "controlled_response": original_response,
                "chat_controller_applied": False,
                "core_theme": core_theme,
                "chat_controller_prompt": final_prompt,
                "error": "Empty response from LLM"
            }
        
        logger.info(f"Successfully controlled response for conversation {conversation_id}")
        return {
            "original_response": original_response,
            "controlled_response": controlled_response,
            "chat_controller_applied": True,
            "core_theme": core_theme,
            "chat_controller_prompt": final_prompt,
            "error": None
        }
        
    except Exception as e:
        logger.error(f"Error in chat controller for conversation {conversation_id}: {e}", exc_info=True)
        return {
            "original_response": original_response,
            "controlled_response": original_response,
            "chat_controller_applied": False,
            "core_theme": None,
            "chat_controller_prompt": None,
            "error": str(e)
        }