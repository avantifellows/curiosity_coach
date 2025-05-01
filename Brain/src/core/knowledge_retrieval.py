import os
from typing import Dict, Any, Tuple, List, Union
from src.services.llm_service import LLMService
from src.utils.logger import logger

# Define paths relative to this file's location
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
_KNOWLEDGE_TEMPLATE_PATH = os.path.join(_PROMPT_DIR, "knowledge_retrieval_prompt.txt")

class KnowledgeRetrievalError(Exception):
    """Custom exception for knowledge retrieval errors"""
    pass

def retrieve_knowledge(main_topic: str, related_topics: List[str], get_prompt_template_only: bool = False) -> Union[Tuple[str, str], str]:
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
        logger.debug(f"Loading knowledge retrieval prompt template from: {_KNOWLEDGE_TEMPLATE_PATH}")
        try:
            with open(_KNOWLEDGE_TEMPLATE_PATH, "r") as f:
                knowledge_prompt_template = f.read()
            formatted_prompt_template_text = knowledge_prompt_template # Store for potential return
        except Exception as e:
            logger.error(f"Failed to load knowledge retrieval prompt template: {e}", exc_info=True)
            raise KnowledgeRetrievalError(f"Failed to load knowledge retrieval prompt template: {e}")

        # Return just the template if requested
        if get_prompt_template_only:
            logger.info("Returning only the knowledge retrieval prompt template.")
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

        # Format the complete prompt with actual topics
        formatted_prompt = knowledge_prompt_template.replace("{{MAIN_TOPIC}}", main_topic)
        formatted_prompt = formatted_prompt.replace("{{RELATED_TOPICS}}", ", ".join(related_topics))
        logger.debug("Formatted complete prompt for knowledge retrieval")

        # Initialize LLM service
        logger.debug("Initializing LLM service for knowledge retrieval")
        llm_service = LLMService()
        
        # Get context information from knowledge retrieval
        logger.debug("Requesting knowledge context from LLM")
        knowledge_response = llm_service.generate_response(formatted_prompt, call_type="knowledge_retrieval")
        context_info = knowledge_response["raw_response"]
        
        logger.info("Successfully retrieved knowledge context")
        return context_info, formatted_prompt # Return both context and the prompt
        
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