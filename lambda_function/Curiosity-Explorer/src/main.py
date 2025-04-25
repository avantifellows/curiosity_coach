from src.core.intent_response_generator import generate_response_prompt
from src.core.intent_identifier import identify_intent, IntentIdentificationError
from src.services.llm_service import LLMService
from src.utils.logger import logger
import os
import json

def process_query(query: str) -> dict:
    """
    Process a user query through the intent identification and response generation pipeline.
    
    Args:
        query (str): The user's query to process
        
    Returns:
        dict: A dictionary containing the final response and intermediate prompts/responses
        
    Raises:
        Exception: If any part of the pipeline fails
    """
    try:
        logger.info(f"Processing query: {query}")
        intermediate_data = {
            'prompts': [],
            'intermediate_responses': [],
            'intent': None,
            'intent_prompt': None
        }
        
        # Read the intent identifier prompt
        with open(os.path.join("src", "prompts", "intent_identifier_prompt.txt"), "r") as f:
            intent_identifier_prompt = f.read()
        formatted_prompt = intent_identifier_prompt.replace("{{INSERT_QUERY_HERE}}", query)
        intermediate_data['intent_prompt'] = formatted_prompt
        
        # Identify the intent and subject behind the query
        logger.debug("Identifying intent...")
        intent_json = identify_intent(query)
        logger.info(f"Identified intent: {intent_json}")
        
        # Store intent data
        intermediate_data['intent'] = {
            'main_topic': intent_json["subject"]["main_topic"],
            'related_topics': intent_json["subject"]["related_topics"],
            'intents': intent_json["intents"],
            'confidence': 1.0,  # Since we don't have confidence in the current implementation
            'raw_intent': intent_json
        }
        
        # Extract the main topic for context
        main_topic = intent_json["subject"]["main_topic"]
        related_topics = intent_json["subject"]["related_topics"]
        logger.debug(f"Main topic: {main_topic}, Related topics: {related_topics}")
        
        # Initialize LLM service for knowledge retrieval
        llm_service = LLMService()
        
        # Generate knowledge retrieval prompt
        knowledge_prompt = f"""
        Please provide detailed, accurate information about the following topic:
        Main Topic: {main_topic}
        Related Topics: {', '.join(related_topics)}
        
        Focus on providing factual, scientific information that would be relevant to answering questions about this topic.
        """
        
        intermediate_data['prompts'].append(knowledge_prompt)
        
        # Get context information from knowledge retrieval
        logger.debug("Retrieving knowledge context...")
        knowledge_response = llm_service.generate_response(knowledge_prompt, call_type="knowledge_retrieval")
        context_info = knowledge_response["raw_response"]
        intermediate_data['intermediate_responses'].append(context_info)
        logger.debug(f"Retrieved context: {context_info}")
        
        # Generate the final prompt
        logger.debug("Generating response prompt...")
        final_prompt = generate_response_prompt(query, intent_json, context_info)
        intermediate_data['prompts'].append(final_prompt)
        logger.debug(f"Generated prompt: {final_prompt}")
        
        # Generate the initial response
        logger.debug("Generating initial response...")
        response_dict = llm_service.generate_response(final_prompt, call_type="response_generation")
        initial_response = response_dict["raw_response"]
        intermediate_data['intermediate_responses'].append(initial_response)
        
        # Generate learning-enhanced response
        logger.debug("Generating learning-enhanced response...")
        with open(os.path.join("src", "prompts", "learning_prompt.txt"), "r") as f:
            learning_prompt_template = f.read()
        
        learning_prompt = learning_prompt_template.format(
            original_response=initial_response,
            context_info=context_info
        )
        intermediate_data['prompts'].append(learning_prompt)
        
        learning_response = llm_service.generate_response(learning_prompt, call_type="learning_enhancement")
        enhanced_response = learning_response["raw_response"]
        intermediate_data['intermediate_responses'].append(enhanced_response)
        
        logger.info("Successfully generated enhanced response")
        return {
            'response': enhanced_response,
            'prompts': intermediate_data['prompts'],
            'intermediate_responses': intermediate_data['intermediate_responses'],
            'intent': intermediate_data['intent'],
            'intent_prompt': intermediate_data['intent_prompt']
        }
        
    except IntentIdentificationError as e:
        logger.error(f"Error identifying intent: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise

def _validate_intent_response(response: dict) -> None:
    """
    Validate the structure of the intent identification response.
    
    Args:
        response (dict): The response to validate
        
    Raises:
        IntentIdentificationError: If the response structure is invalid
    """
    required_keys = ["query", "subject", "intents"]
    for key in required_keys:
        if key not in response:
            raise IntentIdentificationError(f"Missing required key in intent response: {key}")
    
    # Validate subject structure
    if "main_topic" not in response["subject"] or "related_topics" not in response["subject"]:
        raise IntentIdentificationError("Invalid subject structure in intent response")
    
    # Validate related_topics is a list
    if not isinstance(response["subject"]["related_topics"], list):
        raise IntentIdentificationError("related_topics must be a list")
    
    # Validate intents structure
    if not isinstance(response["intents"], dict):
        raise IntentIdentificationError("intents must be a dictionary")
    
    # Validate each intent is either a string or None
    for intent_type, intent_value in response["intents"].items():
        if intent_value is not None and not isinstance(intent_value, str):
            raise IntentIdentificationError(f"Intent value for {intent_type} must be a string or None")

if __name__ == "__main__":
    query = "Why do some planets have rings?"
    try:
        logger.info("Starting query processing...")
        response = process_query(query)
        logger.info("Query processing completed successfully")
        print(response)
    except Exception as e:
        logger.error(f"Failed to process query: {e}", exc_info=True)
