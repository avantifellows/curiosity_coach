import os
import httpx
import asyncio
from typing import Dict, Any, Tuple, List, Union, Optional
from src.services.llm_service import LLMService
from src.utils.logger import logger

# Define paths relative to this file's location
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
_KNOWLEDGE_TEMPLATE_PATH = os.path.join(_PROMPT_DIR, "knowledge_retrieval_prompt.txt")

# Backend API config for prompt versioning
_BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5000")
_PROMPT_API_PATH = "/api/prompts"

class KnowledgeRetrievalError(Exception):
    """Custom exception for knowledge retrieval errors"""
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
        KnowledgeRetrievalError: If loading the template fails
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
        raise KnowledgeRetrievalError(f"Local prompt template file not found: {filepath}")
    except Exception as e:
        logger.error(f"Failed to get prompt template: {e}", exc_info=True)
        raise KnowledgeRetrievalError(f"Failed to get prompt template: {e}")

async def retrieve_knowledge(main_topic: str, related_topics: List[str], get_prompt_template_only: bool = False) -> Union[Tuple[str, str], str]:
    """
    Retrieves context knowledge based on the main topic and related topics using an LLM,
    or returns the formatted prompt template itself.

    Args:
        main_topic (str): The main topic identified from the query. Used as placeholder if get_prompt_template_only is True.
        related_topics (List[str]): A list of related topics. Used as placeholder if get_prompt_template_only is True.
        get_prompt_template_only (bool): If True, returns only the formatted prompt template
                                         without substituting the topics and without calling the LLM.

    Returns:
        Union[Tuple[str, str], str]:
            - If get_prompt_template_only is False: A tuple containing the retrieved knowledge context (string)
              and the formatted prompt string sent to the LLM.
            - If get_prompt_template_only is True: The formatted prompt template string.

    Raises:
        KnowledgeRetrievalError: If the knowledge retrieval fails (and get_prompt_template_only is False)
                                   or if loading the template fails.
    """
    formatted_prompt_template_text = "" # Initialize for error reporting
    formatted_prompt = "" # Initialize for error reporting

    try:
        # Read the knowledge retrieval prompt template (needed for both modes)
        knowledge_prompt_template = await _get_prompt_template(_KNOWLEDGE_TEMPLATE_PATH, "knowledge_retrieval")
        formatted_prompt_template_text = knowledge_prompt_template # Store for potential return

        # Return just the template if requested
        if get_prompt_template_only:
            logger.info(f"Returning only the knowledge retrieval prompt template.")
            # Ensure placeholders are still present
            if "{{MAIN_TOPIC}}" not in formatted_prompt_template_text or "{{RELATED_TOPICS}}" not in formatted_prompt_template_text:
                 logger.warning("Placeholders not found in the template when returning knowledge template only.")
            return formatted_prompt_template_text

        # --- Continue with normal knowledge retrieval if get_prompt_template_only is False ---

        # If no main topic is provided, skip knowledge retrieval (only applies when not getting template)
        if not main_topic:
            logger.info("No main topic provided, skipping knowledge retrieval.")
            return "", ""  # Return empty context and empty prompt

        logger.info(f"Retrieving knowledge for main topic: {main_topic}")

        # Format the related topics as a comma-separated list or handle empty list
        related_topics_str = ", ".join(related_topics) if related_topics else "None specified"
        
        # Format the complete prompt with actual topics
        formatted_prompt = knowledge_prompt_template.replace("{{MAIN_TOPIC}}", main_topic)
        formatted_prompt = formatted_prompt.replace("{{RELATED_TOPICS}}", related_topics_str)
        logger.debug(f"Formatted complete prompt for knowledge retrieval on: {main_topic}")

        # Initialize LLM service
        logger.debug("Initializing LLM service for knowledge retrieval")
        llm_service = LLMService()
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": "You are an educational knowledge assistant with expertise across many domains."},
            {"role": "user", "content": formatted_prompt}
        ]
        
        # Get context information from knowledge retrieval
        logger.debug("Requesting knowledge context from LLM")
        response = llm_service.get_completion(messages, call_type="knowledge_retrieval")
        
        # Validate the response is not empty
        if not response or len(response.strip()) < 50:
            logger.warning(f"Knowledge retrieval returned unusually short response: '{response}'")
            
        logger.info(f"Successfully retrieved knowledge context ({len(response)} chars)")
        return response, formatted_prompt # Return both context and the prompt
        
    except KnowledgeRetrievalError: # Re-raise specific errors
        raise
    except Exception as e:
        error_msg = f"Failed to retrieve knowledge or load template: {str(e)}"
        if formatted_prompt: # Note: formatted_prompt might be empty if error occurred before it was fully set
            error_msg += f"\nPrompt used:\n{formatted_prompt}"
        elif get_prompt_template_only and formatted_prompt_template_text:
            error_msg += f"\nPrompt template being processed:\n{formatted_prompt_template_text}"
        logger.error(error_msg, exc_info=True)
        raise KnowledgeRetrievalError(error_msg)