from src.core.intent_identifier import identify_intent, IntentIdentificationError
from src.core.knowledge_retrieval import retrieve_knowledge, KnowledgeRetrievalError
from src.core.final_response_generator import generate_initial_response, ResponseGenerationError
from src.core.learning_enhancement import generate_enhanced_response, LearningEnhancementError
from src.utils.logger import logger
import os
import json
from typing import Optional, Dict, Any
from src.config_models import FlowConfig

def process_query(query: str, config: Optional[FlowConfig] = None) -> dict:
    """
    Process a user query through the intent identification and response generation pipeline.
    
    Args:
        query (str): The user's query to process
        config (Optional[FlowConfig]): Configuration object for the processing pipeline.
            If None, default configuration will be used.
        
    Returns:
        dict: A dictionary containing the final response and intermediate prompts/responses
        
    Raises:
        Exception: If any part of the pipeline fails
    """

    # import ipdb; ipdb.set_trace()
    try:
        logger.info(f"Processing query: {query}")
        
        # If no config is provided, use a default FlowConfig instance
        if config is None:
            config = FlowConfig()
            logger.info("No configuration provided, using default FlowConfig.")
        else:
            logger.info(f"Using provided configuration: {config.model_dump()}")

        intermediate_data = {
            'prompts': [],
            'intermediate_responses': [],
            'intent': None,
        }
        
        # 1. Identify the intent and subject behind the query
        logger.debug("Identifying intent...")
        intent_json, intent_prompt = identify_intent(query)
        logger.info(f"Identified intent: {intent_json}")
        
        # Store intent data and the prompt used
        intermediate_data['prompts'].append(intent_prompt)
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
        
        # 2. Retrieve context information
        logger.debug("Retrieving knowledge context...")
        context_info, knowledge_prompt = retrieve_knowledge(main_topic, related_topics)
        intermediate_data['prompts'].append(knowledge_prompt)
        intermediate_data['intermediate_responses'].append(context_info)
        logger.debug(f"Retrieved context: {context_info}")
        
        # 3. Generate the initial response based on intent and context
        logger.debug("Generating initial response...")
        initial_response, final_prompt = generate_initial_response(query, intent_json, context_info)
        intermediate_data['prompts'].append(final_prompt)
        intermediate_data['intermediate_responses'].append(initial_response)
        logger.debug(f"Generated initial response: {initial_response[:100]}...") # Log snippet

        # Initialize final response with the initial one
        final_response = initial_response

        # 4. Generate learning-enhanced response (conditionally)
        logger.debug("Checking if learning-enhanced response should be generated...")
        print(f"Config: {config.model_dump()}")
        if config.run_enhancement_step:
            logger.debug("Generating learning-enhanced response...")
            enhanced_response_val, learning_prompt = generate_enhanced_response(initial_response, context_info)
            intermediate_data['prompts'].append(learning_prompt)
            intermediate_data['intermediate_responses'].append(enhanced_response_val)
            final_response = enhanced_response_val # Update final response
            logger.info("Successfully generated enhanced response")
        else:
            logger.info("Skipping learning-enhanced response generation as per config.")
            # final_response remains initial_response

        import pprint
        pprint.pprint(intermediate_data['prompts'])
        # import ipdb; ipdb.set_trace()
        return {
            'response': final_response, # Use the correctly named variable
            'prompts': intermediate_data['prompts'],
            'intermediate_responses': intermediate_data['intermediate_responses'],
            'intent': intermediate_data['intent'],
        }
        
    except IntentIdentificationError as e:
        logger.error(f"Error identifying intent: {e}", exc_info=True)
        raise
    except KnowledgeRetrievalError as e:
        logger.error(f"Error retrieving knowledge: {e}", exc_info=True)
        raise
    except ResponseGenerationError as e:
        logger.error(f"Error generating initial response: {e}", exc_info=True)
        raise
    except LearningEnhancementError as e:
        logger.error(f"Error generating enhanced response: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    # Ensure logger is configured if running standalone
    # from src.utils.logger import setup_logging
    # setup_logging()
    
    query = "Why do some planets have rings?"
    try:
        logger.info("Starting query processing...")
        
        # Example with default config (enhancement runs)
        logger.info("--- Running with default config (enhancement enabled) ---")
        response_default = process_query(query)
        logger.info("Query processing completed successfully (default config)")
        import pprint
        pprint.pprint(response_default)

        # # Example with enhancement disabled
        # logger.info("\n--- Running with enhancement disabled ---")
        # config_no_enhance = FlowConfig(run_enhancement_step=False)
        # response_no_enhance = process_query(query, config=config_no_enhance)
        # logger.info("Query processing completed successfully (enhancement disabled)")
        # pprint.pprint(response_no_enhance)

        # # Example with enhancement explicitly enabled
        # logger.info("\n--- Running with enhancement explicitly enabled ---")
        # config_enhance = FlowConfig(run_enhancement_step=True)
        # response_enhance = process_query(query, config=config_enhance)
        # logger.info("Query processing completed successfully (enhancement enabled)")
        # pprint.pprint(response_enhance)

    except Exception as e:
        logger.error(f"Failed to process query: {e}", exc_info=True)
