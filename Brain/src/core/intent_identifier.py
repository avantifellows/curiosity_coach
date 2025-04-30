import json
import os
from typing import Dict, Any, Tuple
from groq import Groq
from dotenv import load_dotenv
from src.services.llm_service import LLMService
from src.utils.logger import logger

# Load environment variables
load_dotenv()

# Define paths relative to this file's location
_PROMPT_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")
_INTENT_TEMPLATE_PATH = os.path.join(_PROMPT_DIR, "intent_identifier_prompt.txt")
_INTENT_CONFIG_PATH = os.path.join(_PROMPT_DIR, "intent_config.json")

class IntentIdentificationError(Exception):
    """Custom exception for intent identification errors"""
    pass

def _validate_intent_response(response: Dict[str, Any]) -> None:
    """
    Validates the structure and content of the intent response.
    
    Args:
        response (Dict[str, Any]): The response to validate
        
    Raises:
        IntentIdentificationError: If the response is invalid
    """
    logger.debug("Validating intent response structure")
    required_keys = ["query", "subject", "intents"]
    subject_keys = ["main_topic", "related_topics"]
    intent_keys = ["cognitive_intent", "exploratory_intent", 
                  "metacognitive_intent", "emotional_identity_intent", 
                  "recursive_intent"]
    
    # Check if all required keys are present
    if not all(key in response for key in required_keys):
        logger.error(f"Missing required keys in response. Found: {list(response.keys())}")
        raise IntentIdentificationError("Missing required keys in response")
    
    # Check if subject has all required keys
    if not all(key in response["subject"] for key in subject_keys):
        logger.error(f"Missing required subject keys. Found: {list(response['subject'].keys())}")
        raise IntentIdentificationError("Missing required subject keys")
    
    # Check if intents dictionary has all required keys
    if not all(key in response["intents"] for key in intent_keys):
        logger.error(f"Missing required intent keys. Found: {list(response['intents'].keys())}")
        raise IntentIdentificationError("Missing required intent keys")
    
    # Validate that each intent is either a string or None
    for intent, value in response["intents"].items():
        if value is not None and not isinstance(value, str):
            logger.error(f"Invalid type for intent {intent}: {type(value)}")
            raise IntentIdentificationError(f"Invalid type for intent {intent}")
    
    # Validate that related_topics is a list
    if not isinstance(response["subject"]["related_topics"], list):
        logger.error(f"related_topics is not a list: {type(response['subject']['related_topics'])}")
        raise IntentIdentificationError("related_topics must be a list")
    
    logger.debug("Intent response validation successful")

def identify_intent(query: str) -> Tuple[Dict[str, Any], str]:
    """
    Identifies the intent and subject behind a user's query using the LLM prompt.
    Also returns the exact prompt used for this identification.

    Args:
        query (str): The user's query to analyze

    Returns:
        Tuple[Dict[str, Any], str]: A tuple containing:
            - A dictionary with the query, subject, and identified intents.
            - The formatted prompt string sent to the LLM.

    Raises:
        IntentIdentificationError: If the intent identification fails
    """
    formatted_prompt = "" # Initialize to ensure it's always defined
    try:
        logger.info(f"Identifying intent for query: {query}")
        
        # Load intent configuration
        logger.debug(f"Loading intent config from: {_INTENT_CONFIG_PATH}")
        try:
            with open(_INTENT_CONFIG_PATH, "r") as f:
                intent_config = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load intent config: {e}", exc_info=True)
            raise IntentIdentificationError(f"Failed to load intent config: {e}")
            
        # Format intent definitions for the prompt
        intent_definitions = []
        for intent_key, possible_values in intent_config.items():
            values_str = ", ".join([f'"{val}"' for val in possible_values])
            definition = f'"{intent_key}": "one of: {values_str}, or null"'
            intent_definitions.append(definition)
        intent_definitions_str = ",\n        ".join(intent_definitions)
        logger.debug("Formatted intent definitions")

        # Read the intent identifier prompt template
        logger.debug(f"Loading intent prompt template from: {_INTENT_TEMPLATE_PATH}")
        try:
            with open(_INTENT_TEMPLATE_PATH, "r") as f:
                intent_identifier_prompt_template = f.read()
        except Exception as e:
            logger.error(f"Failed to load intent prompt template: {e}", exc_info=True)
            raise IntentIdentificationError(f"Failed to load intent prompt template: {e}")

        # Format the complete prompt
        formatted_prompt = intent_identifier_prompt_template.replace("{{INTENT_DEFINITIONS}}", intent_definitions_str)
        formatted_prompt = formatted_prompt.replace("{{INSERT_QUERY_HERE}}", query)
        logger.debug("Formatted complete prompt for intent identification")
        
        # Initialize LLM service
        logger.debug("Initializing LLM service for intent identification")
        llm_service = LLMService()
        
        # Prepare messages for the LLM
        messages = [
            {"role": "system", "content": "You are an educational AI assistant trained in pedagogy."},
            {"role": "user", "content": formatted_prompt}
        ]
        
        # Get completion from the configured LLM provider
        logger.debug("Requesting completion from LLM")
        response_text = llm_service.get_completion(messages, call_type="intent_identification")
        
        try:
            logger.debug("Parsing LLM response as JSON")
            intent_data = json.loads(response_text)
            # Add the original query to the response data, as the prompt requests it
            intent_data["query"] = query 
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON. Raw response: {response_text}")
            logger.error(f"JSON parsing error: {str(e)}")
            raise IntentIdentificationError("Failed to parse LLM response as JSON")
        
        # Validate the response structure
        _validate_intent_response(intent_data)
        
        logger.info("Successfully identified intent")
        return intent_data, formatted_prompt # Return both intent data and the prompt
        
    except IntentIdentificationError: # Re-raise specific errors
        raise
    except Exception as e:
        # Include the potentially generated prompt in the error message if available
        error_msg = f"Failed to identify intent: {str(e)}"
        if formatted_prompt:
            error_msg += f"\nPrompt used:\n{formatted_prompt}"
        logger.error(error_msg, exc_info=True)
        raise IntentIdentificationError(f"Failed to identify intent: {str(e)}")
