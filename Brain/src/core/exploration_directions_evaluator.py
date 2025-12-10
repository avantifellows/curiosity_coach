<<<<<<< HEAD
import json
=======
from pickle import FALSE
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
import httpx
import os
from typing import Optional, List, Dict, Any
from src.services.llm_service import LLMService
from src.services.api_service import api_service
from src.utils.logger import logger
from src.utils.prompt_injection import inject_core_theme_placeholder
from src.core.exploration_directions_config import EXPLORATION_DIRECTIONS_PROMPT_NAME

async def _get_exploration_prompt_template() -> Optional[str]:
    """Fetch exploration directions prompt template from backend database."""
    try:
        backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
        url = f"{backend_url}/api/prompts/{EXPLORATION_DIRECTIONS_PROMPT_NAME}/versions/active"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
            prompt_text = data.get("prompt_text", "")
            logger.info(f"Fetched exploration directions prompt from backend: {len(prompt_text)} chars")
            return prompt_text
    except Exception as e:
        logger.error(f"Error fetching exploration prompt from backend: {e}")
        return None

async def _format_conversation_for_prompt(conversation_history: List[Dict[str, Any]]) -> str:
    """Format conversation history for the prompt."""
    if not conversation_history:
        return "No conversation history yet."
    
    formatted_messages = []
    for msg in conversation_history:  # Last 10 messages
        role = "User" if msg.get('is_user', False) else "AI"
        content = msg.get('content', '')
        formatted_messages.append(f"{role}: {content}")
    
    return "\n".join(formatted_messages)

async def evaluate_exploration_directions(
<<<<<<< HEAD
    conversation_id: int,
    core_theme: Optional[str],
    conversation_history: List[Dict[str, Any]],
    current_query: Optional[str] = None,
    latest_user_message: Optional[str] = None,
    latest_ai_response: Optional[str] = None,
    current_curiosity_score: int = 0,
=======
    conversation_id: int, 
    core_theme: Optional[str],
    conversation_history: List[Dict[str, Any]],
    current_query: Optional[str] = None
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
) -> Optional[Dict[str, Any]]:
    """
    Evaluates possible exploration directions based on core theme and conversation.
    Returns dict with 'directions' list and metadata, or None on failure.
    """
<<<<<<< HEAD
    core_theme_value = core_theme if core_theme else "No core theme identified yet."

    if not core_theme:
        logger.info(
            f"No core theme available for conversation {conversation_id}; proceeding with placeholder"
        )

=======
    if not core_theme:
        logger.info(f"No core theme for conversation {conversation_id}, skipping exploration evaluation")
        return None
    
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
    logger.info(f"Starting exploration directions evaluation for conversation {conversation_id}")
    
    try:
        # Get prompt template from DB
        prompt_template = await _get_exploration_prompt_template()
        if not prompt_template:
<<<<<<< HEAD
            logger.warning("Could not fetch exploration directions prompt template from DB")
            return None

        # Format conversation history
        formatted_history = await _format_conversation_for_prompt(conversation_history)

        # Use the injection system to replace placeholders
        # First inject core theme
        formatted_prompt = inject_core_theme_placeholder(prompt_template, core_theme_value)
=======
            logger.warning(f"Could not fetch exploration directions prompt template from DB")
            return None
        
        # Format conversation history
        formatted_history = await _format_conversation_for_prompt(conversation_history)
        
        # Use the injection system to replace placeholders
        # First inject core theme
        formatted_prompt = inject_core_theme_placeholder(prompt_template, core_theme)
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
        
        # Then inject conversation history (simple replace since no special injection function exists)
        if "{{CONVERSATION_HISTORY}}" in formatted_prompt:
            formatted_prompt = formatted_prompt.replace("{{CONVERSATION_HISTORY}}", formatted_history)
<<<<<<< HEAD

        if "{{QUERY}}" in formatted_prompt:
            query_text = current_query if current_query else "No current query available"
            formatted_prompt = formatted_prompt.replace("{{QUERY}}", query_text)

        if "{{LATEST_USER_MESSAGE}}" in formatted_prompt:
            formatted_prompt = formatted_prompt.replace("{{LATEST_USER_MESSAGE}}", latest_user_message or "")

        if "{{LATEST_AI_RESPONSE}}" in formatted_prompt:
            formatted_prompt = formatted_prompt.replace("{{LATEST_AI_RESPONSE}}", latest_ai_response or "")

        if "{{CURRENT_CURIOSITY_SCORE}}" in formatted_prompt:
            bounded_score = max(0, min(100, current_curiosity_score))
            formatted_prompt = formatted_prompt.replace("{{CURRENT_CURIOSITY_SCORE}}", str(bounded_score))

        if "{{CONVERSATION_ID}}" in formatted_prompt:
            formatted_prompt = formatted_prompt.replace("{{CONVERSATION_ID}}", str(conversation_id))
        logger.debug(f"Final formatted prompt (first 200 chars): {formatted_prompt[:200]}...")

=======
        
              # Inject current user query
        if "{{QUERY}}" in formatted_prompt:
            query_text = current_query if current_query else "No current query available"
            formatted_prompt = formatted_prompt.replace("{{QUERY}}", query_text)
        logger.debug(f"Final formatted prompt (first 200 chars): {formatted_prompt[:200]}...")
        
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
        # Call LLM
        llm_service = LLMService()
        logger.debug(f"Calling LLM for exploration directions evaluation")

        response = llm_service.generate_response(
            final_prompt=formatted_prompt,
            call_type="exploration_directions_evaluation",
            json_mode=False
        )

<<<<<<< HEAD
        raw_response = (response.get("raw_response", "") or "").strip()

        if not raw_response:
            logger.warning(f"Empty response from LLM for conversation {conversation_id}")
            return {
                'directions': [],
                'core_theme': core_theme_value,
                'prompt': formatted_prompt,
                'raw_response': raw_response,
                'evaluation_successful': False,
                'curiosity_score': None,
                'curiosity_reason': None,
                'curiosity_error': 'Empty response from LLM'
            }

        directions: List[str] = []
        curiosity_score: Optional[int] = None
        curiosity_reason: Optional[str] = None
        curiosity_error: Optional[str] = None

        try:
            parsed = json.loads(raw_response)
            if isinstance(parsed, dict):
                raw_directions = parsed.get("exploration_directions") or parsed.get("directions")
                if isinstance(raw_directions, list):
                    directions = [d.strip() for d in raw_directions if isinstance(d, str) and d.strip()]

                curiosity_score_val = parsed.get("curiosity_score") or parsed.get("score")
                curiosity_reason_val = parsed.get("curiosity_reason") or parsed.get("reason")

                if isinstance(curiosity_score_val, (int, float)):
                    curiosity_score = int(max(0, min(100, round(curiosity_score_val))))
                if isinstance(curiosity_reason_val, str):
                    curiosity_reason = curiosity_reason_val.strip()
            else:
                logger.warning(f"Unexpected JSON structure for exploration response in conversation {conversation_id}")
                curiosity_error = 'Unexpected JSON structure'
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON response for conversation {conversation_id}")
            logger.debug(f"Raw response: {raw_response}")
            # Attempt legacy parsing for directions if JSON parsing fails
            directions = [d.strip() for d in raw_response.split('#') if d.strip()]
            curiosity_error = 'JSON decode error'

        evaluation_successful = len(directions) > 0
        if not evaluation_successful:
            logger.warning(f"No exploration directions parsed for conversation {conversation_id}")

        return {
            'directions': directions,
            'core_theme': core_theme_value,
            'prompt': formatted_prompt,
            'raw_response': raw_response,
            'evaluation_successful': evaluation_successful,
            'curiosity_score': curiosity_score,
            'curiosity_reason': curiosity_reason,
            'curiosity_error': curiosity_error,
        }
=======
        # Parse comma-separated string response
        raw_response = response.get("raw_response", "").strip()
        try:
            if raw_response:
                # Split by comma and clean up each direction
                directions = [d.strip() for d in raw_response.split('#') if d.strip()]
                if len(directions) > 0:
                    logger.info(f"Generated {len(directions)} exploration directions for conversation {conversation_id}")
                    return {
                        'directions': directions,
                        'core_theme': core_theme,
                        'prompt': formatted_prompt,
                        'evaluation_successful': True
                    }
                else:
                    logger.warning(f"Empty directions after parsing for conversation {conversation_id}")
                    return None
            else:
                logger.warning(f"Empty response from LLM for conversation {conversation_id}")
                return None
        except Exception as e:
            logger.error(f"Failed to parse directions string for conversation {conversation_id}: {e}")
            logger.debug(f"Raw response: {raw_response}")
            return None
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
    except Exception as e:
        logger.error(f"Error evaluating exploration directions for conversation {conversation_id}: {e}", exc_info=True)
        return None

async def get_conversation_core_theme(conversation_id: int) -> Optional[str]:
    """Fetch core theme from backend API."""
    try:
        core_theme = await api_service.get_conversation_core_theme(conversation_id)
        return core_theme
    except Exception as e:
        logger.warning(f"Could not fetch core theme from API: {e}")
<<<<<<< HEAD
        return None
=======
        return None
>>>>>>> 19272150e8ad8591993fc62068b2a76868920788
