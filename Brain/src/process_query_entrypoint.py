from src.core.intent_identifier import identify_intent, IntentIdentificationError
from src.core.knowledge_retrieval import retrieve_knowledge, KnowledgeRetrievalError
from src.core.final_response_generator import generate_initial_response, ResponseGenerationError
from src.core.learning_enhancement import generate_enhanced_response, LearningEnhancementError
from src.utils.logger import logger
import os
import json
from typing import Optional, Dict, Any, List
from src.config_models import FlowConfig, StepConfig
from src.schemas import ProcessQueryResponse, PipelineData

def get_step_enabled_status(step_name: str, steps_config: List[StepConfig]) -> bool:
    """Helper function to find if a step is enabled from the list of StepConfig."""
    for step_conf in steps_config:
        if step_conf.name == step_name:
            return step_conf.enabled
    logger.warning(f"Configuration for step '{step_name}' not found. Assuming disabled.")
    return False # Default to False if step name not found in config

def get_step_use_conversation_history_status(step_name: str, steps_config: List[StepConfig]) -> bool:
    """Helper function to find if a step should use conversation history."""
    for step_conf in steps_config:
        if step_conf.name == step_name:
            return step_conf.use_conversation_history
    logger.warning(f"Configuration for step '{step_name}' not found for use_conversation_history. Assuming false.")
    return False

def process_query(query: str, config: Optional[FlowConfig] = None, conversation_history: Optional[str] = None) -> ProcessQueryResponse:
    """
    Process a user query through the intent identification and response generation pipeline.
    
    Args:
        query (str): The user's query to process
        config (Optional[FlowConfig]): Configuration object for the processing pipeline.
            If None, default configuration will be used.
        conversation_history (Optional[str]): The conversation history between the user and the system.
        
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
        
        # Initialize variables that are outputs of conditional steps
        intent_json: Optional[Dict[str, Any]] = None
        intent_prompt: Optional[str] = None
        main_topic: Optional[str] = None
        related_topics: Optional[List[str]] = None
        context_info: Optional[str] = None
        knowledge_prompt: Optional[str] = None
        initial_response: Optional[str] = None
        initial_response_prompt: Optional[str] = None

        # 1. Identify the intent and subject behind the query
        step_name_intent = "intent_identification"
        is_intent_enabled = get_step_enabled_status(step_name_intent, effective_config.steps)
        use_history_intent = get_step_use_conversation_history_status(step_name_intent, effective_config.steps)
        
        query_for_intent = query
        if use_history_intent and conversation_history:
            query_for_intent = f"""{query}\n\nFor context, this is the conversation history between you and the user: {conversation_history}"""
            logger.debug(f"Using conversation history for {step_name_intent}")

        if is_intent_enabled:
            logger.debug(f"Executing step: {step_name_intent}...")
            intent_json, intent_prompt = identify_intent(query_for_intent)
            logger.info(f"Identified intent: {intent_json}")
            if intent_json and "subject" in intent_json:
                main_topic = intent_json["subject"].get("main_topic")
                related_topics = intent_json["subject"].get("related_topics")
            else:
                logger.warning(f"Intent identification result did not contain expected 'subject' structure: {intent_json}")
        else:
            logger.info(f"Skipping step: {step_name_intent} as per config.")
        
        intent_step_data = {
            'name': step_name_intent,
            'enabled': is_intent_enabled,
            'prompt': intent_prompt,
            'raw_result': intent_json,
            'main_topic': main_topic,
            'related_topics': related_topics,
        }
        pipeline_data['steps'].append(intent_step_data)
        
        # main_topic and related_topics are now set (or None if step skipped/failed)
        logger.debug(f"Main topic after intent step: {main_topic}, Related topics: {related_topics}")
        
        # 2. Retrieve context information
        step_name_knowledge = "knowledge_retrieval"
        is_knowledge_enabled = get_step_enabled_status(step_name_knowledge, effective_config.steps)
        use_history_knowledge = get_step_use_conversation_history_status(step_name_knowledge, effective_config.steps)

        if is_knowledge_enabled:
            if main_topic:
                logger.debug(f"Executing step: {step_name_knowledge}...")
                # Conversation history is not directly applicable to main_topic input for this step.
                input_for_knowledge = main_topic
                context_info, knowledge_prompt = retrieve_knowledge(input_for_knowledge, related_topics if related_topics else [])
                logger.debug(f"Retrieved context: {context_info}")
            else:
                logger.warning(f"Skipping content generation for {step_name_knowledge} as main_topic is not available.")
        else:
            logger.info(f"Skipping step: {step_name_knowledge} as per config.")

        knowledge_step_data = {
            'name': step_name_knowledge,
            'enabled': is_knowledge_enabled,
            'prompt': knowledge_prompt,
            'result': context_info
        }
        pipeline_data['steps'].append(knowledge_step_data)
        logger.debug(f"Context info after knowledge step: {context_info}")
        
        # 3. Generate the initial response based on intent and context
        step_name_initial_resp = "initial_response_generation"
        is_initial_resp_enabled = get_step_enabled_status(step_name_initial_resp, effective_config.steps)
        use_history_initial_resp = get_step_use_conversation_history_status(step_name_initial_resp, effective_config.steps)

        query_for_initial_resp = query
        if use_history_initial_resp and conversation_history:
            query_for_initial_resp = f"""{query}\n\nFor context, this is the conversation history between you and the user: {conversation_history}"""
            logger.debug(f"Using conversation history for {step_name_initial_resp}")
            
        if is_initial_resp_enabled:
            logger.debug(f"Executing step: {step_name_initial_resp}...")
            initial_response, initial_response_prompt = generate_initial_response(
                query_for_initial_resp, 
                intent_json, # Can be None
                context_info # Can be None
            )
            logger.debug(f"Generated initial response: {initial_response[:100] if initial_response else 'None'}...")
            pipeline_data['final_response'] = initial_response # Tentative final response
        else:
            logger.info(f"Skipping step: {step_name_initial_resp} as per config.")

        initial_response_step_data = {
            'name': step_name_initial_resp,
            'enabled': is_initial_resp_enabled,
            'prompt': initial_response_prompt,
            'result': initial_response
        }
        pipeline_data['steps'].append(initial_response_step_data)

        # 4. Generate learning-enhanced response (conditionally)
        step_name_enhancement = "learning_enhancement"
        is_enhancement_enabled = get_step_enabled_status(step_name_enhancement, effective_config.steps)
        use_history_enhancement = get_step_use_conversation_history_status(step_name_enhancement, effective_config.steps)
        
        logger.debug(f"Checking if {step_name_enhancement} should be generated... Config enabled: {is_enhancement_enabled}")
        # The print statement for config can be kept if useful, or removed.
        # print(f"Config for enhancement check: {effective_config.model_dump()}") 
        
        enhancement_prompt_result: Optional[str] = None
        enhanced_response_val: Optional[str] = None

        if is_enhancement_enabled:
            if initial_response:
                logger.debug(f"Executing step: {step_name_enhancement}...")
                
                input_for_enhancement = initial_response
                if use_history_enhancement and conversation_history:
                    # Here, history is prepended to the initial_response, which is the primary input for enhancement
                    input_for_enhancement = f"""{initial_response}\n\nFor context, this is the conversation history that led to this response: {conversation_history}"""
                    logger.debug(f"Using conversation history for {step_name_enhancement}")

                enhanced_response_val, enhancement_prompt_result = generate_enhanced_response(
                    input_for_enhancement, 
                    context_info # Can be None
                )
                pipeline_data['final_response'] = enhanced_response_val # Update final response
                logger.info("Successfully generated enhanced response")
            else:
                logger.warning(f"Skipping content generation for {step_name_enhancement} as initial_response is not available.")
        else:
            logger.info(f"Skipping step: {step_name_enhancement} as per config.")

        enhancement_step_data = {
            'name': step_name_enhancement,
            'enabled': is_enhancement_enabled,
            'prompt': enhancement_prompt_result,
            'result': enhanced_response_val
        }
        pipeline_data['steps'].append(enhancement_step_data)

        if pipeline_data['final_response'] is None:
            logger.warning("Pipeline completed but no final response was generated.")
            pipeline_data['final_response'] = "No response could be generated based on the current configuration and inputs."

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
        
        # Example with default config (all steps enabled by default from FlowConfig)
        logger.info("--- Running with default config (all steps enabled) ---")
        response_default = process_query(query)
        logger.info("Query processing completed successfully (default config)")
        import pprint
        pprint.pprint(response_default.model_dump_json(indent=2)) # Use model_dump_json for better readability

        # Example with learning_enhancement disabled
        logger.info("\n--- Running with learning_enhancement disabled ---")
        config_no_enhance = FlowConfig(
            steps=[
                StepConfig(name="intent_identification", enabled=True),
                StepConfig(name="knowledge_retrieval", enabled=True),
                StepConfig(name="initial_response_generation", enabled=True),
                StepConfig(name="learning_enhancement", enabled=False), # Disable enhancement
            ]
        )
        response_no_enhance = process_query(query, config=config_no_enhance)
        logger.info("Query processing completed successfully (learning_enhancement disabled)")
        pprint.pprint(response_no_enhance.model_dump_json(indent=2))

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
