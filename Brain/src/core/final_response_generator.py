# intent_response_generator.py

import os
import httpx
from typing import Dict, Any, Tuple, Optional
from src.services.llm_service import LLMService
from src.utils.logger import logger

# Define paths relative to this file's location
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
_RESPONSE_TEMPLATE_PATH = os.path.join(_PROMPT_DIR, "response_generator_prompt.txt")
_RESPONSE_CONVERSATIONAL_TEMPLATE_PATH = os.path.join(_PROMPT_DIR, "response_generator_conversational_prompt.txt")
_RESPONSE_PERSONAL_TEMPLATE_PATH = os.path.join(_PROMPT_DIR, "response_generator_personal_prompt.txt")

# Backend API config for prompt versioning
_BACKEND_URL = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
_PROMPT_API_PATH = "/api/prompts"

# Mapping of prompt names to file paths
_PROMPT_PATH_MAP = {
    "response_generation": _RESPONSE_TEMPLATE_PATH,
    "response_generation_conversational": _RESPONSE_CONVERSATIONAL_TEMPLATE_PATH,
    "response_generation_personal": _RESPONSE_PERSONAL_TEMPLATE_PATH
}

class ResponseGenerationError(Exception):
    """Custom exception for response generation errors"""
    pass

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

async def _get_prompt_template(prompt_name: str) -> str:
    """
    Gets a prompt template from a local file or the backend versioning system.
    
    Args:
        prompt_name (str): The name of the prompt to use when querying
        
    Returns:
        str: The prompt template text
        
    Raises:
        ResponseGenerationError: If loading the template fails
    """
    try:
        # First, try to get from the backend (asynchronously)
        logger.info(f"Attempting to fetch '{prompt_name}' prompt from backend versioning system")
        prompt_text = await _get_prompt_from_backend(prompt_name)
        
        if prompt_text:
            logger.info(f"Using versioned prompt '{prompt_name}' from backend")
            return prompt_text
        
        # Fallback to local file - get the appropriate file path for the prompt name
        filepath = _PROMPT_PATH_MAP.get(prompt_name, _RESPONSE_TEMPLATE_PATH)
        
        logger.info(f"Falling back to local prompt template: {filepath}")
        try:
            with open(filepath, "r") as f:
                prompt_template = f.read()
                
            logger.info(f"Successfully loaded local prompt template: {filepath}")
            return prompt_template
        except FileNotFoundError:
            # If the specific template doesn't exist, fall back to the default one
            if prompt_name != "response_generation" and filepath != _RESPONSE_TEMPLATE_PATH:
                logger.warning(f"Specific template {filepath} not found, falling back to default")
                with open(_RESPONSE_TEMPLATE_PATH, "r") as f:
                    prompt_template = f.read()
                return prompt_template
            else:
                raise
    except FileNotFoundError:
        logger.error(f"Local prompt template file not found for prompt: {prompt_name}")
        raise ResponseGenerationError(f"Local prompt template file not found for prompt: {prompt_name}")
    except Exception as e:
        logger.error(f"Failed to get prompt template: {e}", exc_info=True)
        raise ResponseGenerationError(f"Failed to get prompt template: {e}")

def _generate_response_prompt(query: str, intent_data: Dict[str, Any], context_info: str, template: str) -> str:
    """
    Generates the prompt for the initial response based on query, intent, and context.
    
    Args:
        query (str): The user's query
        intent_data (Dict[str, Any]): The intent data from intent gathering
        context_info (str): Retrieved context information
        template (str): The response generator prompt template
        
    Returns:
        str: Formatted prompt for response generation
    """
    # Extract primary intent information from intent data (if available)
    primary_intent_category = "unknown"
    primary_intent_type = "unknown"
    primary_intent_confidence = 0.0
    intent_category = "unknown"
    
    if intent_data and "intents" in intent_data and "primary_intent" in intent_data["intents"]:
        primary_intent = intent_data["intents"]["primary_intent"]
        primary_intent_category = primary_intent.get("category", "unknown")
        primary_intent_type = primary_intent.get("specific_type", "unknown")
        primary_intent_confidence = primary_intent.get("confidence", 0.0)
        intent_category = intent_data.get("intent_category", primary_intent_category)
    
    # Format the prompt template with the query, intent information, and context
    formatted_prompt = template.replace("{{QUERY}}", query)
    formatted_prompt = formatted_prompt.replace("{{INTENT_CATEGORY}}", intent_category)
    formatted_prompt = formatted_prompt.replace("{{PRIMARY_INTENT_CATEGORY}}", primary_intent_category)
    formatted_prompt = formatted_prompt.replace("{{PRIMARY_INTENT_TYPE}}", primary_intent_type)
    formatted_prompt = formatted_prompt.replace("{{PRIMARY_INTENT_CONFIDENCE}}", str(primary_intent_confidence))
    
    # Add context information if available
    if context_info and context_info.strip():
        formatted_prompt = formatted_prompt.replace("{{CONTEXT_INFO}}", context_info.strip())
    else:
        formatted_prompt = formatted_prompt.replace("{{CONTEXT_INFO}}", "No additional context available.")
    
    # Add student context from intent data if available
    student_context = {}
    if intent_data and "context" in intent_data:
        student_context = intent_data["context"]
    
    known_info = student_context.get("known_information", "Not specified")
    motivation = student_context.get("motivation", "Not specified")
    learning_goal = student_context.get("learning_goal", "Not specified")
    
    formatted_prompt = formatted_prompt.replace("{{KNOWN_INFORMATION}}", known_info)
    formatted_prompt = formatted_prompt.replace("{{MOTIVATION}}", motivation)
    formatted_prompt = formatted_prompt.replace("{{LEARNING_GOAL}}", learning_goal)
    
    # Add secondary intent information if available and confidence is good
    secondary_intent_section = "No significant secondary intent identified."
    if (intent_data and "intents" in intent_data and "secondary_intent" in intent_data["intents"] and
            intent_data["intents"]["secondary_intent"].get("confidence", 0.0) > 0.3):
        secondary_intent = intent_data["intents"]["secondary_intent"]
        sec_category = secondary_intent.get("category", "unknown")
        sec_type = secondary_intent.get("specific_type", "unknown")
        sec_confidence = secondary_intent.get("confidence", 0.0)
        
        secondary_intent_section = f"Secondary intent: {sec_category} / {sec_type} (confidence: {sec_confidence})"
    
    formatted_prompt = formatted_prompt.replace("{{SECONDARY_INTENT_INFO}}", secondary_intent_section)
    
    return formatted_prompt

async def generate_initial_response(
    query: str, 
    intent_data: Optional[Dict[str, Any]], 
    context_info: Optional[str] = None, 
    get_prompt_template_only: bool = False,
    prompt_name: str = "response_generation",
    conversation_memory: Optional[Dict[str, Any]] = None,
    user_persona: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """
    Generates the initial response based on the query, identified intents, and retrieved context.
    
    Args:
        query (str): The user's query
        intent_data (Optional[Dict[str, Any]]): The intent data from the intent gathering process
        context_info (Optional[str]): Retrieved context information about the topic
        get_prompt_template_only (bool): If True, returns only the prompt template without calling the LLM
        prompt_name (str): The specific prompt name to use, which can vary based on intent category
        
    Returns:
        Tuple[str, str]: The generated response and the prompt used to generate it
        
    Raises:
        ResponseGenerationError: If the response generation fails
    """
    try:
        # Get the prompt template (from backend or local file)
        prompt_template = await _get_prompt_template(prompt_name)
        
        # Return just the template if requested
        if get_prompt_template_only:
            return prompt_template, ""
        
        # Generate formatted prompt
        final_prompt = _generate_response_prompt(
            query, 
            intent_data if intent_data else {}, 
            context_info if context_info else "",
            prompt_template
        )

        # Inject persona placeholders if present
        if "{{USER_PERSONA" in final_prompt:
            from src.utils.prompt_injection import inject_persona_placeholders
            final_prompt = inject_persona_placeholders(final_prompt, user_persona)

        # Inject conversation memory if placeholders exist
        if "{{CONVERSATION_MEMORY" in final_prompt:
            from src.utils.prompt_injection import inject_memory_placeholders
            final_prompt = inject_memory_placeholders(final_prompt, conversation_memory)
        
        # Initialize LLM service
        logger.debug("Initializing LLM service for initial response generation")
        llm_service = LLMService()

        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": "You are Curiosity Coach, an educational AI designed to foster curiosity and engage students in meaningful learning conversations."},
            {"role": "user", "content": final_prompt}
        ]
        
        # Generate the initial response
        logger.debug("Generating initial response...")
        initial_response = llm_service.get_completion(messages, call_type="response_generation")

        logger.debug("Successfully generated initial response")
        return initial_response, final_prompt

    except Exception as e:
        error_msg = f"Failed to generate initial response: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise ResponseGenerationError(error_msg)