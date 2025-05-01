import os
from typing import Tuple, Union
from src.services.llm_service import LLMService
from src.utils.logger import logger

# Define paths relative to this file's location
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
_LEARNING_PROMPT_PATH = os.path.join(_PROMPT_DIR, "learning_prompt.txt")


class LearningEnhancementError(Exception):
    """Custom exception for learning enhancement errors"""
    pass


def generate_enhanced_response(initial_response: str, context_info: str, get_prompt_template_only: bool = False) -> Tuple[str, str]:
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
        logger.debug(f"Loading learning prompt template from: {_LEARNING_PROMPT_PATH}")
        try:
            with open(_LEARNING_PROMPT_PATH, "r") as f:
                learning_prompt_template = f.read()
            learning_prompt_template_text = learning_prompt_template # Store for potential return
        except Exception as e:
            logger.error(f"Failed to load learning prompt template: {e}", exc_info=True)
            raise LearningEnhancementError(f"Failed to load learning prompt template: {e}")

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