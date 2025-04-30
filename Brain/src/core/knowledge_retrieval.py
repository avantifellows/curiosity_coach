import os
from typing import Dict, Any, Tuple, List
from src.services.llm_service import LLMService
from src.utils.logger import logger

# Define paths relative to this file's location
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
_KNOWLEDGE_TEMPLATE_PATH = os.path.join(_PROMPT_DIR, "knowledge_retrieval_prompt.txt")

class KnowledgeRetrievalError(Exception):
    """Custom exception for knowledge retrieval errors"""
    pass

def retrieve_knowledge(main_topic: str, related_topics: List[str]) -> Tuple[str, str]:
    """
    Retrieves context knowledge based on the main topic and related topics using an LLM.
    Also returns the exact prompt used for retrieval.

    Args:
        main_topic (str): The main topic identified from the query.
        related_topics (List[str]): A list of related topics.

    Returns:
        Tuple[str, str]: A tuple containing:
            - The retrieved knowledge context (string).
            - The formatted prompt string sent to the LLM.

    Raises:
        KnowledgeRetrievalError: If the knowledge retrieval fails.
    """
    # If no main topic is provided, skip knowledge retrieval
    if not main_topic:
        logger.info("No main topic provided, skipping knowledge retrieval.")
        return "", ""  # Return empty context and empty prompt

    formatted_prompt = "" # Initialize to ensure it's always defined
    try:
        logger.info(f"Retrieving knowledge for main topic: {main_topic}")
        
        # Read the knowledge retrieval prompt template
        logger.debug(f"Loading knowledge retrieval prompt template from: {_KNOWLEDGE_TEMPLATE_PATH}")
        try:
            with open(_KNOWLEDGE_TEMPLATE_PATH, "r") as f:
                knowledge_prompt_template = f.read()
        except Exception as e:
            logger.error(f"Failed to load knowledge retrieval prompt template: {e}", exc_info=True)
            raise KnowledgeRetrievalError(f"Failed to load knowledge retrieval prompt template: {e}")

        # Format the complete prompt
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
        # Include the potentially generated prompt in the error message if available
        error_msg = f"Failed to retrieve knowledge: {str(e)}"
        if formatted_prompt:
            error_msg += f"\nPrompt used:\n{formatted_prompt}"
        logger.error(error_msg, exc_info=True)
        raise KnowledgeRetrievalError(f"Failed to retrieve knowledge: {str(e)}") 