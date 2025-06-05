from src.core.conversational_intent_gatherer import gather_initial_intent, process_follow_up_response, ConversationalIntentError
from src.core.knowledge_retrieval import retrieve_knowledge, KnowledgeRetrievalError
from src.core.final_response_generator import generate_initial_response, ResponseGenerationError
from src.core.learning_enhancement import generate_enhanced_response, LearningEnhancementError
from src.utils.logger import logger
import os
import json
from typing import Optional, Dict, Any, List, Tuple
from src.config_models import FlowConfig, StepConfig
from src.schemas import ProcessQueryResponse, PipelineData
import httpx

# Intent categories as constants
INTENT_EDUCATIONAL = "educational"
INTENT_CONVERSATIONAL = "conversational"
INTENT_CLARIFICATION = "clarification"
INTENT_ADMINISTRATIVE = "administrative"
INTENT_PERSONAL = "personal"

# Step names as constants
STEP_INTENT_GATHERING = "intent_gathering"
STEP_FOLLOW_UP = "follow_up_processing"
STEP_KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
STEP_INITIAL_RESPONSE = "initial_response_generation"
STEP_LEARNING_ENHANCEMENT = "learning_enhancement"
STEP_SIMPLIFIED_CONVERSATION = "simplified_conversation"

# --- Flag to override config and force simplified mode ---
# When true, this overrides any S3 config and always uses simplified mode
FORCE_SIMPLIFIED_MODE = True

def is_step_enabled(step_name: str, config: FlowConfig) -> bool:
    """
    Helper function to check if a step is enabled in the configuration.
    
    Args:
        step_name: The name of the step to check
        config: The flow configuration
        
    Returns:
        True if the step is enabled, False otherwise
    """
    # Special case for simplified mode - always return True if forcing simplified mode
    if step_name == STEP_SIMPLIFIED_CONVERSATION and FORCE_SIMPLIFIED_MODE:
        return True
        
    for step_config in config.steps:
        if step_config.name == step_name:
            return step_config.enabled
            
    logger.warning(f"No configuration for {step_name}, defaulting to enabled")
    return True

def should_use_conversation_history(step_name: str, config: FlowConfig) -> bool:
    """
    Determines if a specific step should use conversation history.
    
    Args:
        step_name: The name of the step to check
        config: The flow configuration
        
    Returns:
        True if the step should use conversation history, False otherwise
    """
    for step_config in config.steps:
        if step_config.name == step_name:
            return step_config.use_conversation_history
            
    logger.warning(f"No configuration for {step_name}, defaulting to not using conversation history")
    return False

def should_run_step(step_name: str, intent_data: Optional[Dict[str, Any]], config: FlowConfig) -> bool:
    """
    Determines if a specific pipeline step should be executed based on
    the step configuration and intent category.
    
    Args:
        step_name: The name of the step to check
        intent_data: The intent data from the intent gathering step
        config: The flow configuration
        
    Returns:
        True if the step should be executed, False otherwise
    """
    # First check if the step is enabled in configuration
    enabled = is_step_enabled(step_name, config)
    if not enabled:
        logger.info(f"Step {step_name} is disabled in configuration")
        return False
        
    # If intent data is not available, default to running the step
    if intent_data is None:
        logger.debug(f"No intent data available for {step_name}, defaulting to enabled")
        return True
        
    # Get the intent category, defaulting to "educational" if not specified
    intent_category = intent_data.get("intent_category", INTENT_EDUCATIONAL)
    logger.info(f"Intent category for {step_name} decision: {intent_category}")
    
    # Apply conditional logic based on step and intent
    if step_name == STEP_KNOWLEDGE_RETRIEVAL:
        should_run = intent_category in [INTENT_EDUCATIONAL, INTENT_CLARIFICATION]
        logger.info(f"Knowledge retrieval should run: {should_run} (category: {intent_category})")
        return should_run
        
    elif step_name == STEP_LEARNING_ENHANCEMENT:
        should_run = intent_category == INTENT_EDUCATIONAL
        logger.info(f"Learning enhancement should run: {should_run} (category: {intent_category})")
        return should_run
    
    elif step_name == STEP_INITIAL_RESPONSE:
        # All intent categories need a response, but the format and template might differ
        logger.info(f"Initial response should run for all intent categories")
        return True
        
    # Default to enabled for other steps
    return True

def get_appropriate_prompt_for_intent(step_name: str, intent_data: Optional[Dict[str, Any]]) -> str:
    """
    Determines the appropriate prompt name to use for a specific step based on intent category.
    This helps with selecting different prompt templates for different intent types.
    
    Args:
        step_name: The name of the step to get the prompt for
        intent_data: The intent data from the intent gathering step
        
    Returns:
        The appropriate prompt name to use
    """
    # If no intent data is available, use the default prompt name
    if intent_data is None:
        return _get_default_prompt_name(step_name)
        
    # Get the intent category, defaulting to "educational" if not specified
    intent_category = intent_data.get("intent_category", INTENT_EDUCATIONAL)
    
    # For initial response generation, the prompt might vary based on intent category
    if step_name == STEP_INITIAL_RESPONSE:
        if intent_category == INTENT_CONVERSATIONAL:
            return "response_generation_conversational"
        elif intent_category == INTENT_PERSONAL:
            return "response_generation_personal"
        else:
            return "response_generation"  # Default for educational, clarification, etc.
    
    # For now, other steps use a single prompt template
    return _get_default_prompt_name(step_name)

def _get_default_prompt_name(step_name: str) -> str:
    """
    Returns the default prompt name for a given step.
    
    Args:
        step_name: The name of the step
        
    Returns:
        The default prompt name
    """
    if step_name == STEP_INTENT_GATHERING:
        return "intent_gathering"
    elif step_name == STEP_FOLLOW_UP:
        return "follow_up_response"
    elif step_name == STEP_KNOWLEDGE_RETRIEVAL:
        return "knowledge_retrieval"
    elif step_name == STEP_INITIAL_RESPONSE:
        return "response_generation"
    elif step_name == STEP_LEARNING_ENHANCEMENT:
        return "learning_enhancement"
    else:
        logger.warning(f"Unknown step name: {step_name}, returning the step name as prompt name")
        return step_name

async def generate_simplified_response(query: str, conversation_history: Optional[str] = None, purpose: str = "chat") -> Tuple[str, str, Dict[str, Any]]:
    """
    Generate a simplified response using a single prompt approach.
    
    Args:
        query (str): The user's query
        conversation_history (Optional[str]): Previous conversation history if available
        purpose (str): The purpose of the query
        
    Returns:
        Tuple[str, str, Dict[str, Any]]: The response, the prompt used, and the full structured response data
    """
    logger.info(f"Generating simplified response for query: {query} (purpose: {purpose})")
    
    # Define prompt file path
    prompt_file_path = os.path.join(os.path.dirname(__file__), "prompts", "simplified_conversation_prompt.txt")
    
    try:
        # Get prompt template - try from backend first, then fallback to local file
        prompt_template = await _get_prompt_template(prompt_file_path, "simplified_conversation", purpose)
        
        # Format the prompt with query and conversation history
        formatted_prompt = prompt_template.replace("{{QUERY}}", query)
        
        if conversation_history:
            formatted_prompt = formatted_prompt.replace("{{CONVERSATION_HISTORY}}", conversation_history)
        else:
            formatted_prompt = formatted_prompt.replace("{{CONVERSATION_HISTORY}}", "No previous conversation.")
        
        # Call LLM service
        from src.services.llm_service import LLMService
        llm_service = LLMService()
        
        messages = [
            {"role": "system", "content": "You are a Curiosity Coach, designed to engage students in thought-provoking conversations that foster critical thinking and curiosity."},
            {"role": "user", "content": formatted_prompt}
        ]
        
        response_text = llm_service.get_completion(messages, call_type="simplified_conversation")
        
        # Parse the JSON response
        try:
            import json
            import re
            
            # Clean up markdown code blocks if present
            # This handles cases where the LLM returns ```json {... json here...} ```
            cleaned_response = response_text
            markdown_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
            if markdown_match:
                logger.info("Detected markdown code block in LLM response, extracting JSON content")
                cleaned_response = markdown_match.group(1)
            
            response_data = json.loads(cleaned_response)
            
            # Check if we need clarification or have a normal response
            if response_data.get("needs_clarification", False):
                # Format follow-up questions
                follow_up_questions = response_data.get("follow_up_questions", [])
                formatted_response = "\n".join(follow_up_questions)
            else:
                # Get the normal response
                formatted_response = response_data.get("response", "")
                
            return formatted_response, formatted_prompt, response_data
            
        except json.JSONDecodeError:
            # Fallback in case response isn't valid JSON
            logger.error(f"Failed to parse JSON response: {response_text}")
            return response_text, formatted_prompt, {"response": response_text, "needs_clarification": False}
            
    except Exception as e:
        logger.error(f"Error in generate_simplified_response: {str(e)}", exc_info=True)
        raise

async def _get_prompt_template(filepath: str, prompt_name: str, purpose: str = "chat") -> str:
    """
    Gets a prompt template from a local file or the backend versioning system.
    
    Args:
        filepath (str): The local file path to use as fallback
        prompt_name (str): The name to use when querying the backend
        purpose (str): The purpose/endpoint ("chat" uses earliest, others use active)
        
    Returns:
        str: The prompt template text
        
    Raises:
        Exception: If loading the template fails
    """
    try:
        # First, try to get from the backend (asynchronously)
        logger.info(f"Attempting to fetch '{prompt_name}' prompt from backend versioning system (purpose: {purpose})")
        prompt_text = await _get_prompt_from_backend(prompt_name, purpose)
        
        if prompt_text:
            logger.info(f"Using versioned prompt '{prompt_name}' from backend (purpose: {purpose})")
            return prompt_text
        
        # Fallback to local file
        logger.info(f"Falling back to local prompt template: {filepath}")
        with open(filepath, "r") as f:
            prompt_template = f.read()
            
        logger.info(f"Successfully loaded local prompt template: {filepath}")
        return prompt_template
    except FileNotFoundError:
        logger.error(f"Local prompt template file not found: {filepath}")
        raise Exception(f"Local prompt template file not found: {filepath}")
    except Exception as e:
        logger.error(f"Failed to get prompt template: {e}", exc_info=True)
        raise Exception(f"Failed to get prompt template: {e}")

async def _get_prompt_from_backend(prompt_name: str, purpose: str = "chat") -> Optional[str]:
    """
    Attempts to retrieve the prompt version template from the backend versioning system.
    
    Args:
        prompt_name (str): The name of the prompt to retrieve
        purpose (str): The purpose/endpoint ("chat" uses production, others use active)
        
    Returns:
        Optional[str]: The prompt template text if found, None otherwise
    """
    try:
        # Get backend URL from environment
        backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
        
        # Build the appropriate URL based on purpose
        if purpose == "chat":
            # For chat endpoint, use production version
            version_url = f"{backend_url}/api/prompts/{prompt_name}/versions/production"
        else:
            # For test-prompt and others, use active version
            version_url = f"{backend_url}/api/prompts/{prompt_name}/versions/active"
            
        logger.debug(f"Fetching prompt version from: {version_url} (purpose: {purpose})")
        
        # Make the request
        async with httpx.AsyncClient() as client:
            response = await client.get(version_url, timeout=5.0)
            
            if response.status_code == 200:
                data = response.json()
                prompt_text = data.get("prompt_text")
                version_id = data.get("id")
                version_number = data.get("version_number")
                is_production = data.get("is_production", False)
                version_type = "production" if purpose == "chat" else "active"
                logger.info(f"Retrieved {version_type} version {version_number} (ID: {version_id}, production: {is_production}) for prompt '{prompt_name}' (purpose: {purpose})")
                return prompt_text
                
            logger.warning(f"Failed to get prompt version from backend: Status {response.status_code}")
            return None
            
    except Exception as e:
        logger.warning(f"Error getting prompt version from backend: {e}")
        return None

async def process_query(query: str, config: Optional[FlowConfig] = None, conversation_history: Optional[str] = None, purpose: str = "chat") -> ProcessQueryResponse:
    """
    Process a user query through the intent identification and response generation pipeline.
    
    Args:
        query (str): The user's query to process
        config (Optional[FlowConfig]): Configuration object for the processing pipeline.
            If None, default configuration will be used.
        conversation_history (Optional[str]): The conversation history between the user and the system.
        purpose (str): The purpose of the query
        
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
            'follow_up_questions': None,
            'needs_clarification': False
        }
        
        # Check if simplified mode is enabled (either by config or force flag)
        is_simplified_mode = FORCE_SIMPLIFIED_MODE or effective_config.use_simplified_mode
        
        if is_simplified_mode:
            logger.info("Using simplified conversation mode")
            
            # Generate simplified response
            response, prompt, response_data = await generate_simplified_response(query, conversation_history, purpose)
            
            # Check if we need clarification
            needs_clarification = response_data.get("needs_clarification", False)
            
            # Update pipeline data with follow-up questions if needed
            if needs_clarification:
                pipeline_data['needs_clarification'] = True
                pipeline_data['follow_up_questions'] = response_data.get("follow_up_questions", [])
                # No need for partial_understanding in simplified mode
            
            # Update pipeline data
            simplified_step_data = {
                'name': STEP_SIMPLIFIED_CONVERSATION,
                'enabled': True,
                'prompt': prompt,
                'result': response,
                'response_data': response_data,
                'needs_clarification': needs_clarification
            }
            pipeline_data['steps'].append(simplified_step_data)
            pipeline_data['final_response'] = response
            
            return ProcessQueryResponse(**pipeline_data)
        
        # If not in simplified mode, proceed with the original pipeline
        # 1. Gather intent using our conversational approach
        step_name_intent = STEP_INTENT_GATHERING
        is_intent_enabled = is_step_enabled(step_name_intent, effective_config)
        use_history_intent = should_use_conversation_history(step_name_intent, effective_config)
        
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
            intent_result = await gather_initial_intent(query, history_for_intent)
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
        
        # Get the intent category to determine which steps to execute
        intent_category = intent_result.get("intent_category", INTENT_EDUCATIONAL) if intent_result else INTENT_EDUCATIONAL
        logger.info(f"Intent category identified: {intent_category}")
        
        # 2. Retrieve context information - only if needed based on intent
        step_name_knowledge = STEP_KNOWLEDGE_RETRIEVAL
        is_knowledge_enabled = should_run_step(step_name_knowledge, intent_result, effective_config)
        use_history_knowledge = should_use_conversation_history(step_name_knowledge, effective_config)

        if is_knowledge_enabled:
            if main_topic:
                logger.debug(f"Executing step: {step_name_knowledge}...")
                # Conversation history is not directly applicable to main_topic input for this step.
                input_for_knowledge = main_topic
                context_info, knowledge_prompt = await retrieve_knowledge(input_for_knowledge, related_topics if related_topics else [])
                logger.debug(f"Retrieved context: {context_info}")
            else:
                logger.warning(f"Skipping content generation for {step_name_knowledge} as main_topic is not available.")
        else:
            logger.info(f"Skipping step: {step_name_knowledge} as per config or intent category.")

        knowledge_step_data = {
            'name': step_name_knowledge,
            'enabled': is_knowledge_enabled,
            'prompt': knowledge_prompt,
            'result': context_info
        }
        pipeline_data['steps'].append(knowledge_step_data)
        logger.debug(f"Context info after knowledge step: {context_info}")
        
        # 3. Generate the initial response based on intent and context
        step_name_initial_resp = STEP_INITIAL_RESPONSE
        is_initial_resp_enabled = should_run_step(step_name_initial_resp, intent_result, effective_config)
        use_history_initial_resp = should_use_conversation_history(step_name_initial_resp, effective_config)

        query_for_initial_resp = query
        if use_history_initial_resp and conversation_history:
            query_for_initial_resp = f"""{query}\n\nFor context, this is the conversation history between you and the user: {conversation_history}"""
            logger.debug(f"Using conversation history for {step_name_initial_resp}")
            
        initial_response = None
        initial_response_prompt = None
            
        if is_initial_resp_enabled:
            logger.debug(f"Executing step: {step_name_initial_resp}...")
            
            # Get the appropriate prompt name based on intent category
            prompt_name = get_appropriate_prompt_for_intent(step_name_initial_resp, intent_result)
            logger.info(f"Using prompt '{prompt_name}' for response generation based on intent category")
            
            initial_response, initial_response_prompt = await generate_initial_response(
                query_for_initial_resp, 
                intent_result, # Pass the full intent result instead of just intent_json
                context_info, # Can be None
                prompt_name=prompt_name
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
        step_name_enhancement = STEP_LEARNING_ENHANCEMENT
        is_enhancement_enabled = should_run_step(step_name_enhancement, intent_result, effective_config)
        use_history_enhancement = should_use_conversation_history(step_name_enhancement, effective_config)
        
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

                enhanced_response_val, enhancement_prompt_result = await generate_enhanced_response(
                    input_for_enhancement, 
                    context_info # Can be None
                )
                pipeline_data['final_response'] = enhanced_response_val # Update final response
                logger.info("Successfully generated enhanced response")
            else:
                logger.warning(f"Skipping content generation for {step_name_enhancement} as initial_response is not available.")
        else:
            logger.info(f"Skipping step: {step_name_enhancement} as per config or intent category.")

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

async def process_follow_up(
    original_query: str,
    follow_up_questions: List[str],
    student_response: str,
    config: Optional[FlowConfig] = None,
    conversation_history: Optional[str] = None,
    purpose: str = "chat"
) -> ProcessQueryResponse:
    """
    Process a follow-up response from the student to determine intent and generate a final response.
    
    Args:
        original_query (str): The original query that initiated the conversation
        follow_up_questions (List[str]): The follow-up questions previously asked
        student_response (str): The student's response to the follow-up questions
        config (Optional[FlowConfig]): Configuration object for the processing pipeline
        conversation_history (Optional[str]): Previous conversation history
        purpose (str): The purpose of the query
        
    Returns:
        ProcessQueryResponse: A response object containing the final response and pipeline data
        
    Raises:
        Exception: If any part of the pipeline fails
    """
    try:
        logger.info(f"Processing follow-up. Original query: '{original_query}', Student response: '{student_response}' (purpose: {purpose})")
        
        effective_config = config if config is not None else FlowConfig()
        if config is None:
            logger.info("No configuration provided for follow-up processing, using default FlowConfig.")
        else:
            logger.info(f"Using provided configuration for follow-up processing: {effective_config.model_dump()}")

        # Initialize pipeline data structure
        pipeline_data = {
            'query': student_response,
            'config_used': effective_config.model_dump(),
            'steps': [],
            'final_response': None
        }
        
        # Check if simplified mode is enabled (by config or force flag)
        is_simplified_mode = FORCE_SIMPLIFIED_MODE or effective_config.use_simplified_mode
        
        if is_simplified_mode:
            logger.info("Using simplified conversation mode for follow-up")
            
            # Create conversation history with original query and response
            enhanced_conversation_history = ""
            if conversation_history:
                enhanced_conversation_history = conversation_history
            else:
                enhanced_conversation_history = f"User: {original_query}\nAI: {', '.join(follow_up_questions)}\nUser: {student_response}"
            
            # Generate simplified response
            response, prompt, response_data = await generate_simplified_response(student_response, enhanced_conversation_history, purpose)
            
            # Check if we need clarification (again)
            needs_clarification = response_data.get("needs_clarification", False)
            
            # Update pipeline data with follow-up questions if needed
            if needs_clarification:
                pipeline_data['needs_clarification'] = True
                pipeline_data['follow_up_questions'] = response_data.get("follow_up_questions", [])
            
            # Update pipeline data
            simplified_step_data = {
                'name': STEP_SIMPLIFIED_CONVERSATION,
                'enabled': True,
                'prompt': prompt,
                'result': response,
                'response_data': response_data,
                'needs_clarification': needs_clarification
            }
            pipeline_data['steps'].append(simplified_step_data)
            pipeline_data['final_response'] = response
            
            return ProcessQueryResponse(**pipeline_data)
        
        # Original follow-up processing logic for non-simplified mode
        # ... rest of function remains unchanged ...

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
