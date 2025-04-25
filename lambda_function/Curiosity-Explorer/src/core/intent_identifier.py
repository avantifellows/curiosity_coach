import json
import os
from typing import Dict, Any
from groq import Groq
from dotenv import load_dotenv
from src.services.llm_service import LLMService
from src.utils.logger import logger

# Load environment variables
load_dotenv()

# Read the intent identifier prompt from the text file
with open(os.path.join(os.path.dirname(__file__), "..", "prompts", "intent_identifier_prompt.txt"), "r") as f:
    intent_identifier_prompt = f.read()

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

def identify_intent(query: str) -> Dict[str, Any]:
    """
    Identifies the intent and subject behind a user's query using the LLM prompt.
    
    Args:
        query (str): The user's query to analyze
        
    Returns:
        Dict[str, Any]: A dictionary containing the query, subject, and identified intents
        
    Raises:
        IntentIdentificationError: If the intent identification fails
    """
    try:
        logger.info(f"Identifying intent for query: {query}")
        
        # Initialize LLM service
        logger.debug("Initializing LLM service for intent identification")
        llm_service = LLMService()
        
        # Format the prompt with the query
        formatted_prompt = intent_identifier_prompt.replace("{{INSERT_QUERY_HERE}}", query)
        logger.debug("Formatted prompt for intent identification")
        
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
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON. Raw response: {response_text}")
            logger.error(f"JSON parsing error: {str(e)}")
            raise IntentIdentificationError("Failed to parse LLM response as JSON")
        
        # Validate the response structure
        _validate_intent_response(intent_data)
        
        logger.info("Successfully identified intent")
        return intent_data
        
    except Exception as e:
        logger.error(f"Failed to identify intent: {str(e)}", exc_info=True)
        raise IntentIdentificationError(f"Failed to identify intent: {str(e)}")
