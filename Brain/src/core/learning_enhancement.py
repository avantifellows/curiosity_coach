import os
from typing import Tuple
from src.services.llm_service import LLMService
from src.utils.logger import logger

# Define paths relative to this file's location
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
_LEARNING_PROMPT_PATH = os.path.join(_PROMPT_DIR, "learning_prompt.txt")


class LearningEnhancementError(Exception):
    """Custom exception for learning enhancement errors"""
    pass


def generate_enhanced_response(initial_response: str, context_info: str) -> Tuple[str, str]:
    """
    Generates a learning-enhanced response based on the initial response and context.

    Args:
        initial_response (str): The initial response generated.
        context_info (str): The retrieved knowledge context.

    Returns:
        Tuple[str, str]: A tuple containing:
            - The generated enhanced response string.
            - The learning prompt used to generate the response.

    Raises:
        LearningEnhancementError: If the learning enhancement fails.
    """
    learning_prompt = "" # Initialize
    try:
        logger.debug("Generating learning-enhanced response...")

        # Load learning prompt template
        logger.debug(f"Loading learning prompt template from: {_LEARNING_PROMPT_PATH}")
        try:
            with open(_LEARNING_PROMPT_PATH, "r") as f:
                learning_prompt_template = f.read()
        except Exception as e:
            logger.error(f"Failed to load learning prompt template: {e}", exc_info=True)
            raise LearningEnhancementError(f"Failed to load learning prompt template: {e}")

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