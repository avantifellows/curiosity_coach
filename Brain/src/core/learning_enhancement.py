import os
import httpx
import asyncio
from typing import Tuple, Union, Optional
from src.services.llm_service import LLMService
from src.utils.logger import logger

# Define paths relative to this file's location
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
_LEARNING_PROMPT_PATH = os.path.join(_PROMPT_DIR, "learning_prompt.txt")

# Backend API config for prompt versioning
_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
_PROMPT_API_PATH = "/api/prompts"

class LearningEnhancementError(Exception):
    """Custom exception for learning enhancement errors"""
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
        url = f"{_BACKEND_URL}{_PROMPT_API_PATH}/{prompt_name}/versions/active/"
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
        LearningEnhancementError: If loading the template fails
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
        raise LearningEnhancementError(f"Local prompt template file not found: {filepath}")
    except Exception as e:
        logger.error(f"Failed to get prompt template: {e}", exc_info=True)
        raise LearningEnhancementError(f"Failed to get prompt template: {e}")

async def generate_enhanced_response(initial_response: str, context_info: str, get_prompt_template_only: bool = False) -> Tuple[str, str]:
    """
    Generates a learning-enhanced response based on the initial response and context,
    or returns the formatted prompt template itself.

    Args:
        initial_response (str): The initial response generated. Required placeholder if get_prompt_template_only is True.
        context_info (str): The retrieved knowledge context. Required placeholder if get_prompt_template_only is True.
        get_prompt_template_only (bool): If True, returns only the formatted prompt template
                                         without substituting placeholders and without calling the LLM.

    Returns:
        Union[Tuple[str, str], str]:
            - If get_prompt_template_only is False: A tuple containing the generated enhanced response string
              and the learning prompt used to generate the response.
            - If get_prompt_template_only is True: The formatted prompt template string.

    Raises:
        LearningEnhancementError: If the learning enhancement fails (and get_prompt_template_only is False)
                                   or if loading the template fails.
    """
    learning_prompt_template_text = "" # Initialize for error reporting
    learning_prompt = "" # Initialize
    try:
        # Load learning prompt template (needed for both modes)
        learning_prompt_template = await _get_prompt_template(_LEARNING_PROMPT_PATH, "learning_enhancement")
        learning_prompt_template_text = learning_prompt_template # Store for potential return

        # Return just the template if requested
        if get_prompt_template_only:
            logger.info("Returning only the learning enhancement prompt template.")
            # Check for placeholders
            if "{original_response}" not in learning_prompt_template_text or "{context_info}" not in learning_prompt_template_text:
                logger.warning("Placeholders missing in the template when returning learning template only.")
            return learning_prompt_template_text

        # --- Continue with normal response generation if get_prompt_template_only is False ---

        logger.debug("Generating learning-enhanced response...")

        # Format the learning prompt
        learning_prompt = learning_prompt_template.format(
            original_response=initial_response,
            context_info=context_info
        )
        logger.debug("Formatted learning prompt")

        # Initialize LLM service
        logger.debug("Initializing LLM service for learning enhancement")
        llm_service = LLMService()

        # Generate learning-enhanced response
        learning_response = llm_service.generate_response(learning_prompt, call_type="learning_enhancement")
        enhanced_response = learning_response["raw_response"]

        logger.debug("Successfully generated learning-enhanced response")
        return enhanced_response, learning_prompt

    except Exception as e:
        error_msg = f"Failed to generate enhanced response: {str(e)}"
        if learning_prompt:
            error_msg += f"\nPrompt used:\n{learning_prompt}"
        logger.error(error_msg, exc_info=True)
        raise LearningEnhancementError(error_msg) 