from src.core.conversational_intent_gatherer import gather_initial_intent, process_follow_up_response, ConversationalIntentError
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
            'final_response': None,
            'follow_up_questions': None,  # New field for follow-up questions
            'needs_clarification': False  # New field to indicate if clarification is needed
        }
        
        # 1. Gather intent using our new conversational approach
        step_name_intent = "intent_gathering"  # New step name
        is_intent_enabled = get_step_enabled_status(step_name_intent, effective_config.steps)
        use_history_intent = get_step_use_conversation_history_status(step_name_intent, effective_config.steps)
        
        intent_result = None
        main_topic = None
        related_topics = None
        context_info = None
        knowledge_prompt = None
        
        if is_intent_enabled:
            logger.debug(f"Executing step: {step_name_intent}...")
            
            # Use conversation history if enabled and available
            history_for_intent = conversation_history if use_history_intent and conversation_history else None
            
            # Gather initial intent information
            intent_result = gather_initial_intent(query, history_for_intent)
            logger.info(f"Gathered intent. Needs clarification: {intent_result.get('needs_clarification', False)}")
            
            # Check if we need follow-up questions or have complete intent
            if intent_result.get('needs_clarification', False):
                # Store follow-up questions in pipeline data
                pipeline_data['needs_clarification'] = True
                pipeline_data['follow_up_questions'] = intent_result.get('follow_up_questions', [])
                pipeline_data['partial_understanding'] = intent_result.get('partial_understanding', '')
                
                # Set final response to the follow-up questions
                formatted_questions = "\n".join(intent_result.get('follow_up_questions', []))
                pipeline_data['final_response'] = formatted_questions
                
                # Add step data and return early - we need user to respond to questions
                intent_step_data = {
                    'name': step_name_intent,
                    'enabled': is_intent_enabled,
                    'result': intent_result,
                    'needs_clarification': True
                }
                pipeline_data['steps'].append(intent_step_data)
                
                return ProcessQueryResponse(**pipeline_data)
            else:
                # We have complete intent information
                main_topic = intent_result.get("subject", {}).get("main_topic")
                related_topics = intent_result.get("subject", {}).get("related_topics", [])
        else:
            logger.info(f"Skipping step: {step_name_intent} as per config.")
        
        intent_step_data = {
            'name': step_name_intent,
            'enabled': is_intent_enabled,
            'result': intent_result,
            'main_topic': main_topic,
            'related_topics': related_topics,
            'needs_clarification': False
        }
        pipeline_data['steps'].append(intent_step_data)
        
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
            
        initial_response = None
        initial_response_prompt = None
            
        if is_initial_resp_enabled:
            logger.debug(f"Executing step: {step_name_initial_resp}...")
            initial_response, initial_response_prompt = generate_initial_response(
                query_for_initial_resp, 
                intent_result, # Pass the full intent result instead of just intent_json
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
        
        enhancement_prompt_result = None
        enhanced_response_val = None

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
        
        # Return the final response and pipeline data
        logger.info("Successfully processed query and generated response")
        return ProcessQueryResponse(**pipeline_data)
            
    except Exception as e:
        logger.error(f"Error in process_query: {str(e)}", exc_info=True)
        raise

def process_follow_up(
    original_query: str,
    follow_up_questions: List[str],
    student_response: str,
    config: Optional[FlowConfig] = None,
    conversation_history: Optional[str] = None
) -> ProcessQueryResponse:
    """
    Process a follow-up response from the student to determine intent and generate a final response.
    
    Args:
        original_query (str): The original query that initiated the conversation
        follow_up_questions (List[str]): The follow-up questions previously asked
        student_response (str): The student's response to the follow-up questions
        config (Optional[FlowConfig]): Configuration object for the processing pipeline
        conversation_history (Optional[str]): Previous conversation history
        
    Returns:
        ProcessQueryResponse: A response object containing the final response and pipeline data
        
    Raises:
        Exception: If any part of the pipeline fails
    """
    try:
        logger.info(f"Processing follow-up response: {student_response}")
        
        effective_config = config if config is not None else FlowConfig()
        if config is None:
            logger.info("No configuration provided, using default FlowConfig.")
        else:
            logger.info(f"Using provided configuration: {effective_config.model_dump()}")
        
        pipeline_data = {
            'query': original_query,
            'config_used': effective_config.model_dump(),
            'steps': [],
            'final_response': None,
            'follow_up_questions': None,
            'needs_clarification': False
        }
        
        # 1. Process the follow-up response
        step_name_follow_up = "follow_up_processing"
        is_follow_up_enabled = get_step_enabled_status(step_name_follow_up, effective_config.steps)
        use_history_follow_up = get_step_use_conversation_history_status(step_name_follow_up, effective_config.steps)
        
        intent_result = None
        main_topic = None
        related_topics = None
        
        if is_follow_up_enabled:
            logger.debug(f"Executing step: {step_name_follow_up}...")
            
            # Use conversation history if enabled and available
            history_for_follow_up = conversation_history if use_history_follow_up and conversation_history else None
            
            # Process the follow-up response
            intent_result = process_follow_up_response(
                original_query,
                follow_up_questions,
                student_response,
                history_for_follow_up
            )
            logger.info(f"Processed follow-up response. Needs further clarification: {intent_result.get('needs_clarification', False)}")
            
            # Check if we need additional follow-up questions
            if intent_result.get('needs_clarification', False):
                # Store follow-up questions in pipeline data
                pipeline_data['needs_clarification'] = True
                pipeline_data['follow_up_questions'] = intent_result.get('follow_up_questions', [])
                pipeline_data['partial_understanding'] = intent_result.get('partial_understanding', '')
                
                # Set final response to the follow-up questions
                formatted_questions = "\n".join(intent_result.get('follow_up_questions', []))
                pipeline_data['final_response'] = formatted_questions
                
                # Add step data and return early - we need user to respond to additional questions
                follow_up_step_data = {
                    'name': step_name_follow_up,
                    'enabled': is_follow_up_enabled,
                    'result': intent_result,
                    'needs_clarification': True
                }
                pipeline_data['steps'].append(follow_up_step_data)
                
                return ProcessQueryResponse(**pipeline_data)
            else:
                # We have complete intent information
                main_topic = intent_result.get("subject", {}).get("main_topic")
                related_topics = intent_result.get("subject", {}).get("related_topics", [])
        else:
            logger.info(f"Skipping step: {step_name_follow_up} as per config.")
        
        follow_up_step_data = {
            'name': step_name_follow_up,
            'enabled': is_follow_up_enabled,
            'result': intent_result,
            'main_topic': main_topic,
            'related_topics': related_topics,
            'needs_clarification': False
        }
        pipeline_data['steps'].append(follow_up_step_data)
        
        # Continue with the rest of the pipeline (knowledge retrieval, response generation, etc.)
        # This is the same as in the regular process_query function
        
        # 2. Retrieve context information
        step_name_knowledge = "knowledge_retrieval"
        is_knowledge_enabled = get_step_enabled_status(step_name_knowledge, effective_config.steps)
        context_info = None
        knowledge_prompt = None
        
        if is_knowledge_enabled:
            if main_topic:
                logger.debug(f"Executing step: {step_name_knowledge}...")
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
        
        # 3. Generate response based on intent and context
        step_name_initial_resp = "initial_response_generation"
        is_initial_resp_enabled = get_step_enabled_status(step_name_initial_resp, effective_config.steps)
        use_history_initial_resp = get_step_use_conversation_history_status(step_name_initial_resp, effective_config.steps)
        
        query_for_initial_resp = original_query
        if use_history_initial_resp and conversation_history:
            query_for_initial_resp = f"""{original_query}\n\nFor context, this is the conversation history between you and the user: {conversation_history}\n\nThe user's response to your follow-up questions: {student_response}"""
            logger.debug(f"Using conversation history for {step_name_initial_resp}")
        
        initial_response = None
        initial_response_prompt = None
        
        if is_initial_resp_enabled:
            logger.debug(f"Executing step: {step_name_initial_resp}...")
            initial_response, initial_response_prompt = generate_initial_response(
                query_for_initial_resp,
                intent_result,
                context_info
            )
            logger.debug(f"Generated initial response: {initial_response[:100] if initial_response else 'None'}...")
            pipeline_data['final_response'] = initial_response
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
        
        enhancement_prompt_result = None
        enhanced_response_val = None
        
        if is_enhancement_enabled:
            if initial_response:
                logger.debug(f"Executing step: {step_name_enhancement}...")
                
                input_for_enhancement = initial_response
                if use_history_enhancement and conversation_history:
                    input_for_enhancement = f"""{initial_response}\n\nFor context, this is the conversation history that led to this response: {conversation_history}\n\nThe user's response to your follow-up questions: {student_response}"""
                    logger.debug(f"Using conversation history for {step_name_enhancement}")
                
                enhanced_response_val, enhancement_prompt_result = generate_enhanced_response(
                    input_for_enhancement,
                    context_info
                )
                pipeline_data['final_response'] = enhanced_response_val
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
        
        # Return the final response and pipeline data
        logger.info("Successfully processed follow-up and generated response")
        return ProcessQueryResponse(**pipeline_data)
    
    except Exception as e:
        logger.error(f"Error in process_follow_up: {str(e)}", exc_info=True)
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
                StepConfig(name="intent_gathering", enabled=True),
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
