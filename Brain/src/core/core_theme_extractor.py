import json
import os
import httpx
<<<<<<< HEAD
from typing import Optional, List, Dict, Any, Tuple
=======
from typing import Optional
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
from src.services.llm_service import LLMService
from src.services.api_service import api_service
from src.utils.logger import logger
from src.core.core_theme_config import CORE_THEME_EXTRACTION_ENABLED, CORE_THEME_TRIGGER_MESSAGE_COUNT, CORE_THEME_PROMPT_NAME

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

async def _format_conversation_for_prompt(conversation_history: list) -> str:
    """
    Format conversation history for the prompt.
    """
    formatted_messages = []
    
    for msg in conversation_history:
        if msg.get('is_user', False):
            formatted_messages.append(f"User: {msg.get('content', '')}")
        else:
            formatted_messages.append(f"AI: {msg.get('content', '')}")
    
    return "\n".join(formatted_messages)

<<<<<<< HEAD
async def extract_core_theme_from_conversation(
    conversation_id: int,
    conversation_history: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[Optional[str], Optional[str]]:
=======
async def extract_core_theme_from_conversation(conversation_id: int) -> Optional[str]:
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
    """
    Extracts the core theme from a conversation.
    Returns the (core theme, final prompt) tuple.
    """
    logger.info(f"Starting core theme extraction for conversation {conversation_id}")
    
<<<<<<< HEAD
    final_prompt: Optional[str] = None

    try:
        # 1. Fetch conversation history if not provided
        history = conversation_history
        if history is None:
            history = await api_service.get_conversation_history(conversation_id)
=======
    try:
        # 1. Fetch conversation history
        history = await api_service.get_conversation_history(conversation_id)
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
        print("history", history)
        print("########################################################")
        if not history:
            logger.warning(f"No conversation history found for conversation {conversation_id}")
<<<<<<< HEAD
            return None, None
=======
            return None
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
        
        # 2. Filter to get only user messages
        user_messages = [msg for msg in history if msg.get('is_user', False)]
        print("user_messages", user_messages)
        print("########################################################")
        # 3. Check if we have enough messages
        if len(user_messages) < CORE_THEME_TRIGGER_MESSAGE_COUNT:
            logger.info(f"Conversation {conversation_id} has only {len(user_messages)} user messages. Need at least {CORE_THEME_TRIGGER_MESSAGE_COUNT} for theme extraction.")
<<<<<<< HEAD
            return None, None
=======
            return None
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
        
        # 4. Format conversation for prompt
        formatted_conversation = await _format_conversation_for_prompt(history)
        print("formatted_conversation", formatted_conversation)
        print("########################################################")
        # 5. Get prompt template from database
        prompt_template = await _get_prompt_from_backend(CORE_THEME_PROMPT_NAME)
        if not prompt_template:
            logger.error(f"Could not fetch prompt template for {CORE_THEME_PROMPT_NAME}")
<<<<<<< HEAD
            return None, None
=======
            return None
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
        
        # 6. Format the final prompt with conversation history
        final_prompt = prompt_template.replace("{{CONVERSATION_HISTORY}}", formatted_conversation)
        print("final_prompt", final_prompt)
        print("########################################################")
        
        # 7. Call LLM to extract theme
        llm_service = LLMService()
        response = llm_service.generate_response(
            final_prompt=final_prompt,
            call_type="core_theme_extraction",
            json_mode=False
        )
        
        core_theme = response.get("raw_response", "").strip()
        print("core_theme", core_theme)
        print("########################################################")
        
        if not core_theme:
            logger.warning(f"LLM returned empty theme for conversation {conversation_id}")
            return None, final_prompt
        
        logger.info(f"Successfully extracted core theme for conversation {conversation_id}: '{core_theme}'")
        return core_theme, final_prompt
        
    except Exception as e:
        logger.error(f"Error extracting core theme for conversation {conversation_id}: {e}", exc_info=True)
        return None, final_prompt

async def update_conversation_theme(conversation_id: int, core_theme: str) -> bool:
    """
    Updates the conversation's core theme via backend internal API.
    """
    try:
        backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
        url = f"{backend_url}/api/internal/conversations/{conversation_id}/core-chat-theme"
        payload = {"core_chat_theme": core_theme}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.put(url, json=payload)
            response.raise_for_status()
            logger.info(f"Successfully updated core theme for conversation {conversation_id}")
            return True
    except Exception as e:
        logger.error(f"Error updating core theme for conversation {conversation_id}: {e}")
<<<<<<< HEAD
        return False
=======
        return False
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
