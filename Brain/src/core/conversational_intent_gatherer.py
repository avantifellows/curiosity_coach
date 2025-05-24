import json
import os
import httpx
from typing import Dict, Any, Tuple, Union, List, Optional
from src.services.llm_service import LLMService
from src.utils.logger import logger

# Define paths relative to this file's location
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
_INTENT_GATHERING_TEMPLATE_PATH = os.path.join(_PROMPT_DIR, "intent_gathering_prompt.txt")
_FOLLOW_UP_RESPONSE_TEMPLATE_PATH = os.path.join(_PROMPT_DIR, "follow_up_response_prompt.txt")

# Backend API config for prompt versioning
_BACKEND_URL = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
_PROMPT_API_PATH = "/api/prompts"

class ConversationalIntentError(Exception):
    """Custom exception for conversational intent gathering errors"""
    pass

def _validate_intent_gathering_response(response: Dict[str, Any]) -> None:
    """
    Validates the structure of the intent gathering response.
    
    Args:
        response (Dict[str, Any]): The response to validate
        
    Raises:
        ConversationalIntentError: If the response is invalid
    """
    logger.debug("Validating intent gathering response structure")
    
    if "needs_clarification" not in response:
        logger.error("Missing 'needs_clarification' field in response")
        raise ConversationalIntentError("Missing 'needs_clarification' field in response")
    
    if not isinstance(response["needs_clarification"], bool):
        logger.error(f"'needs_clarification' must be a boolean, got: {type(response['needs_clarification'])}")
        raise ConversationalIntentError("'needs_clarification' must be a boolean")
    
    if response["needs_clarification"]:
        # Validate structure for when clarification is needed
        required_keys = ["follow_up_questions", "partial_understanding"]
        if not all(key in response for key in required_keys):
            logger.error(f"Missing required keys for clarification. Found: {list(response.keys())}")
            raise ConversationalIntentError("Missing required keys for clarification")
        
        if not isinstance(response["follow_up_questions"], list):
            logger.error(f"'follow_up_questions' must be a list, got: {type(response['follow_up_questions'])}")
            raise ConversationalIntentError("'follow_up_questions' must be a list")
        
        if not response["follow_up_questions"]:
            logger.error("'follow_up_questions' list cannot be empty")
            raise ConversationalIntentError("'follow_up_questions' list cannot be empty")
    else:
        # Validate structure for when intent is clear
        required_keys = ["query", "subject", "intents", "context"]
        if not all(key in response for key in required_keys):
            logger.error(f"Missing required keys for complete intent. Found: {list(response.keys())}")
            raise ConversationalIntentError("Missing required keys for complete intent")
        
        # Check subject structure
        subject_keys = ["main_topic", "related_topics"]
        if not all(key in response["subject"] for key in subject_keys):
            logger.error(f"Missing required subject keys. Found: {list(response['subject'].keys())}")
            raise ConversationalIntentError("Missing required subject keys")
        
        # Check intents structure
        intents_keys = ["primary_intent", "secondary_intent"]
        if not all(key in response["intents"] for key in intents_keys):
            logger.error(f"Missing required intent keys. Found: {list(response['intents'].keys())}")
            raise ConversationalIntentError("Missing required intent keys")
        
        # Check context structure
        context_keys = ["known_information", "motivation", "learning_goal"]
        if not all(key in response["context"] for key in context_keys):
            logger.error(f"Missing required context keys. Found: {list(response['context'].keys())}")
            raise ConversationalIntentError("Missing required context keys")
    
    logger.debug("Intent gathering response validation successful")

async def _get_prompt_from_backend(prompt_name: str) -> Optional[str]:
    """
    Attempts to fetch the active prompt version from the backend versioning system.
    
    Args:
        prompt_name (str): The name of the prompt to retrieve
        
    Returns:
        Optional[str]: The prompt text if found, None otherwise
    """
    try:
        url = f"{_BACKEND_URL}{_PROMPT_API_PATH}/{prompt_name}/versions/active"
        logger.info(f"Fetching active prompt version for '{prompt_name}' from: {url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Successfully fetched prompt '{prompt_name}' (version {data.get('version_number')}) from backend")
                return data.get("prompt_text")
            elif response.status_code == 404:
                logger.warning(f"No active version found for prompt '{prompt_name}' (404). Will use local fallback.")
                return None
            else:
                logger.warning(f"Failed to fetch prompt '{prompt_name}' from backend: {response.status_code} - {response.text}")
                return None
    except httpx.RequestError as e:
        logger.warning(f"Network error when fetching prompt from backend: {e}", exc_info=True)
        return None
    except httpx.TimeoutException:
        logger.warning(f"Timeout when fetching prompt '{prompt_name}' from backend", exc_info=True)
        return None
    except Exception as e:
        logger.warning(f"Error fetching prompt from backend: {e}", exc_info=True)
        return None

async def _get_prompt_template(filepath: str, prompt_name: str) -> str:
    """
    Gets a prompt template from a local file or the backend versioning system.
    
    Args:
        filepath (str): The local file path to use as fallback
        prompt_name (str): The name to use when querying the backend
        
    Returns:
        str: The prompt template text
        
    Raises:
        ConversationalIntentError: If loading the template fails
    """
    try:
        # First, try to get from the backend (asynchronously)
        logger.info(f"Attempting to fetch '{prompt_name}' prompt from backend versioning system")
        prompt_text = await _get_prompt_from_backend(prompt_name)
        
        if prompt_text:
            logger.info(f"Using versioned prompt '{prompt_name}' from backend")
            return prompt_text
        
        # Fallback to local file
        logger.info(f"Falling back to local prompt template: {filepath}")
        with open(filepath, "r") as f:
            prompt_template = f.read()
            
        logger.info(f"Successfully loaded local prompt template: {filepath}")
        return prompt_template
    except FileNotFoundError:
        logger.error(f"Local prompt template file not found: {filepath}")
        raise ConversationalIntentError(f"Local prompt template file not found: {filepath}")
    except Exception as e:
        logger.error(f"Failed to get prompt template: {e}", exc_info=True)
        raise ConversationalIntentError(f"Failed to get prompt template: {e}")

async def gather_initial_intent(query: str, conversation_history: Optional[str] = None, get_prompt_template_only: bool = False) -> Union[Dict[str, Any], str]:
    """
    Analyzes a query to determine if follow-up questions are needed or if intent is clear.
    
    Args:
        query (str): The user's query to analyze
        conversation_history (Optional[str]): Previous conversation history
        get_prompt_template_only (bool): If True, returns only the prompt template without calling the LLM
        
    Returns:
        Union[Dict[str, Any], str]: 
            - If get_prompt_template_only is False: Response indicating whether clarification is needed or complete intent data
            - If get_prompt_template_only is True: The prompt template
        
    Raises:
        ConversationalIntentError: If the intent gathering fails
    """
    try:
        # Get the prompt template (from backend or local file)
        intent_gathering_template = await _get_prompt_template(
            _INTENT_GATHERING_TEMPLATE_PATH, 
            "intent_gathering"
        )
        
        # Return just the template if requested
        if get_prompt_template_only:
            return intent_gathering_template
        
        # Format the prompt with query
        formatted_prompt = intent_gathering_template.replace("{{INSERT_QUERY_HERE}}", query)
        
        # Add conversation history if available
        if conversation_history:
            formatted_prompt = formatted_prompt.replace(
                "{{CONVERSATION_HISTORY}}", 
                f"\nConversation history:\n{conversation_history}"
            )
        else:
            formatted_prompt = formatted_prompt.replace("{{CONVERSATION_HISTORY}}", "")
        
        # Get LLM response
        logger.debug("Initializing LLM service for intent gathering")
        llm_service = LLMService()
        
        messages = [
            {"role": "system", "content": "You are an educational AI assistant designed to foster curiosity in young students."},
            {"role": "user", "content": formatted_prompt}
        ]
        
        logger.debug("Requesting completion from LLM for intent gathering")
        response_text = llm_service.get_completion(messages, call_type="intent_gathering")
        
        try:
            logger.debug("Parsing LLM response as JSON")
            intent_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON. Raw response: {response_text}")
            logger.error(f"JSON parsing error: {str(e)}")
            raise ConversationalIntentError("Failed to parse LLM response as JSON")
        
        # Validate the response
        _validate_intent_gathering_response(intent_data)
        
        logger.info(f"Successfully gathered intent information. Needs clarification: {intent_data['needs_clarification']}")
        return intent_data
    
    except ConversationalIntentError:
        raise
    except Exception as e:
        logger.error(f"Failed to gather intent: {str(e)}", exc_info=True)
        raise ConversationalIntentError(f"Failed to gather intent: {str(e)}")

async def process_follow_up_response(
    original_query: str,
    previous_questions: List[str],
    student_response: str,
    conversation_history: Optional[str] = None
) -> Dict[str, Any]:
    """
    Processes a student's response to follow-up questions and determines if intent is now clear.
    
    Args:
        original_query (str): The original query that started the conversation
        previous_questions (List[str]): List of previous follow-up questions asked
        student_response (str): The student's response to the follow-up questions
        conversation_history (Optional[str]): Previous conversation history
        
    Returns:
        Dict[str, Any]: Response indicating whether further clarification is needed or complete intent data
        
    Raises:
        ConversationalIntentError: If processing the follow-up response fails
    """
    try:
        # Get the prompt template (from backend or local file)
        follow_up_template = await _get_prompt_template(
            _FOLLOW_UP_RESPONSE_TEMPLATE_PATH, 
            "follow_up_response"
        )
        
        # Format the prompt
        formatted_prompt = follow_up_template.replace("{{ORIGINAL_QUERY}}", original_query)
        formatted_prompt = formatted_prompt.replace("{{STUDENT_RESPONSE}}", student_response)
        
        # Format previous questions
        questions_str = "\n".join([f"- {q}" for q in previous_questions])
        formatted_prompt = formatted_prompt.replace("{{PREVIOUS_QUESTIONS}}", questions_str)
        
        # Add conversation history if available
        if conversation_history:
            formatted_prompt = formatted_prompt.replace(
                "{{CONVERSATION_HISTORY}}", 
                f"\nAdditional conversation history:\n{conversation_history}"
            )
        else:
            formatted_prompt = formatted_prompt.replace("{{CONVERSATION_HISTORY}}", "")
        
        # Get LLM response
        logger.debug("Initializing LLM service for follow-up response processing")
        llm_service = LLMService()
        
        messages = [
            {"role": "system", "content": "You are an educational AI assistant designed to foster curiosity in young students."},
            {"role": "user", "content": formatted_prompt}
        ]
        
        logger.debug("Requesting completion from LLM for follow-up response")
        response_text = llm_service.get_completion(messages, call_type="follow_up_processing")
        
        try:
            logger.debug("Parsing LLM response as JSON")
            intent_data = json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON. Raw response: {response_text}")
            logger.error(f"JSON parsing error: {str(e)}")
            raise ConversationalIntentError("Failed to parse LLM response as JSON")
        
        # Validate the response
        _validate_intent_gathering_response(intent_data)
        
        logger.info(f"Successfully processed follow-up response. Needs further clarification: {intent_data['needs_clarification']}")
        return intent_data
    
    except ConversationalIntentError:
        raise
    except Exception as e:
        logger.error(f"Failed to process follow-up response: {str(e)}", exc_info=True)
        raise ConversationalIntentError(f"Failed to process follow-up response: {str(e)}") 