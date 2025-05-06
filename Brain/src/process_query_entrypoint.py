from src.core.intent_identifier import identify_intent, IntentIdentificationError
from src.core.knowledge_retrieval import retrieve_knowledge, KnowledgeRetrievalError
from src.core.final_response_generator import generate_initial_response, ResponseGenerationError
from src.core.learning_enhancement import generate_enhanced_response, LearningEnhancementError
from src.utils.logger import logger
import os
import json
from typing import Optional, Dict, Any, List
from src.config_models import FlowConfig
from src.schemas import ProcessQueryResponse, PipelineData

def process_query(query: str, config: Optional[FlowConfig] = None) -> ProcessQueryResponse:
    """
    Process a user query through the intent identification and response generation pipeline.
    
    Args:
        query (str): The user's query to process
        config (Optional[FlowConfig]): Configuration object for the processing pipeline.
            If None, default configuration will be used.
        
    Returns:
        ProcessQueryResponse: A response object containing the final response and intermediate prompts/responses
        
    Raises:
        Exception: If any part of the pipeline fails
    """

    # import ipdb; ipdb.set_trace()
    try:
        logger.info(f"Processing query: {query}")
        
        effective_config = config if config is not None else FlowConfig()
        if config is None:
            logger.info("No configuration provided, using default FlowConfig.")
        else:
            logger.info(f"Using provided configuration: {effective_config.model_dump()}")

        pipeline_data = {
            'query': query,
            'config_used': effective_config.model_dump(),
            'steps': [],
            'final_response': None
        }
        
        # 1. Identify the intent and subject behind the query
        logger.debug("Identifying intent...")
        intent_json, intent_prompt = identify_intent(query)
        logger.info(f"Identified intent: {intent_json}")
        
        intent_step_data = {
            'name': 'intent_identification',
            'enabled': True,
            'prompt': intent_prompt,
            'raw_result': intent_json,
            'main_topic': intent_json["subject"]["main_topic"],
            'related_topics': intent_json["subject"]["related_topics"],
        }
        pipeline_data['steps'].append(intent_step_data)
        
        main_topic = intent_step_data['main_topic']
        related_topics = intent_step_data['related_topics']
        logger.debug(f"Main topic: {main_topic}, Related topics: {related_topics}")
        
        # 2. Retrieve context information
        logger.debug("Retrieving knowledge context...")
        context_info, knowledge_prompt = retrieve_knowledge(main_topic, related_topics)
        knowledge_step_data = {
            'name': 'knowledge_retrieval',
            'enabled': True,
            'prompt': knowledge_prompt,
            'result': context_info
        }
        pipeline_data['steps'].append(knowledge_step_data)
        logger.debug(f"Retrieved context: {context_info}")
        
        # 3. Generate the initial response based on intent and context
        logger.debug("Generating initial response...")
        initial_response, initial_response_prompt = generate_initial_response(
            query, 
            intent_step_data['raw_result'], 
            knowledge_step_data['result']
        )
        initial_response_step_data = {
            'name': 'initial_response_generation',
            'enabled': True,
            'prompt': initial_response_prompt,
            'result': initial_response
        }
        pipeline_data['steps'].append(initial_response_step_data)
        logger.debug(f"Generated initial response: {initial_response[:100]}...")

        pipeline_data['final_response'] = initial_response

        # 4. Generate learning-enhanced response (conditionally)
        logger.debug("Checking if learning-enhanced response should be generated...")
        print(f"Config: {effective_config.model_dump()}")
        
        enhancement_step_data = {
            'name': 'learning_enhancement',
            'enabled': effective_config.run_enhancement_step,
            'prompt': None,
            'result': None
        }
        if effective_config.run_enhancement_step:
            logger.debug("Generating learning-enhanced response...")
            enhanced_response_val, learning_prompt = generate_enhanced_response(
                initial_response_step_data['result'], 
                knowledge_step_data['result']
            )
            enhancement_step_data['prompt'] = learning_prompt
            enhancement_step_data['result'] = enhanced_response_val
            pipeline_data['final_response'] = enhanced_response_val
            logger.info("Successfully generated enhanced response")
        else:
            logger.info("Skipping learning-enhanced response generation as per config.")
        pipeline_data['steps'].append(enhancement_step_data)

        return ProcessQueryResponse(
            response=pipeline_data['final_response'],
            pipeline_data=PipelineData(
                query=pipeline_data['query'],
                config_used=pipeline_data['config_used'],
                steps=pipeline_data['steps'],
                final_response=pipeline_data['final_response']
            )
        )
        
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
