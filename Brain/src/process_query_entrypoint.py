from src.utils.logger import logger
import os
from typing import Optional, Dict, Any, List, Tuple
from src.config_models import FlowConfig
from src.schemas import ProcessQueryResponse
import httpx
from src.core.prompt_renderer import RenderContext, render_prompt_template
from src.core.turn_context import PromptExecutionContext
from src.services.api_service import api_service

# Always use simplified conversation mode
FORCE_SIMPLIFIED_MODE = True


def prompt_template_requires_conversation_memory(prompt_template: str) -> bool:
    return "{{CONVERSATION_MEMORY" in prompt_template


def prompt_template_requires_previous_memories(prompt_template: str) -> bool:
    return "{{PREVIOUS_CONVERSATIONS_MEMORY" in prompt_template


def prompt_template_requires_core_theme(prompt_template: str) -> bool:
    return "{{CORE_THEME" in prompt_template


async def resolve_prompt_execution_context(
    purpose: str = "chat",
    conversation_id: Optional[int] = None,
    prompt_response: Optional[Dict[str, Any]] = None,
) -> PromptExecutionContext:
    """
    Resolve the prompt template and stable metadata for the current turn.
    """
    logger.info(
        f"Resolving prompt execution context (purpose={purpose}, conversation_id={conversation_id})"
    )

    prompt_file_path = os.path.join(os.path.dirname(__file__), "prompts", "simplified_conversation_prompt.txt")
    prompt_template: Optional[str] = None
    prompt_name_used = "simplified_conversation"
    prompt_version_used: Optional[int] = None
    prompt_purpose: Optional[str] = None
    prompt_id_used: Optional[int] = None

    if conversation_id:
        try:
            effective_prompt_response = prompt_response
            if effective_prompt_response is None:
                effective_prompt_response = await api_service.get_conversation_prompt(conversation_id)
            if effective_prompt_response and "prompt_text" in effective_prompt_response:
                prompt_template = effective_prompt_response["prompt_text"]
                prompt_version_used = effective_prompt_response.get("version_number")
                prompt_purpose = effective_prompt_response.get("prompt_purpose")
                prompt_id_used = effective_prompt_response.get("prompt_id")
                if prompt_purpose:
                    prompt_name_used = prompt_purpose
                elif prompt_version_used is not None:
                    prompt_name_used = f"conversation_prompt_v{prompt_version_used}"
                logger.info(
                    "Using conversation-assigned prompt "
                    f"(name={prompt_name_used}, version={prompt_version_used}, purpose={prompt_purpose})"
                )
            else:
                logger.warning(
                    f"Prompt response missing prompt_text for conversation_id={conversation_id}; using fallback"
                )
        except Exception as exc:
            logger.error(
                f"Could not fetch assigned prompt for conversation_id={conversation_id}: {exc}",
                exc_info=True,
            )

    if not prompt_template:
        prompt_template = await _get_prompt_template(prompt_file_path, "simplified_conversation", purpose)
        logger.info("Falling back to simplified_conversation prompt template")

    return PromptExecutionContext(
        prompt_template=prompt_template,
        prompt_name=prompt_name_used,
        prompt_version=prompt_version_used,
        prompt_purpose=prompt_purpose,
        prompt_id=prompt_id_used,
    )

async def generate_simplified_response(
    query: str,
    conversation_history: Optional[str] = None,
    user_persona: Optional[Dict[str, Any]] = None,
    purpose: str = "chat",
    conversation_memory: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[int] = None,
    user_id: Optional[int] = None,
    user_created_at: Optional[str] = None,
    user_name: Optional[str] = None,
    current_curiosity_score: int = 0,
    prompt_context: Optional[PromptExecutionContext] = None,
    core_theme: Optional[str] = None,
    previous_memories: Optional[List[Dict[str, Any]]] = None,
) -> Tuple[str, str, str, Dict[str, Any], str, Optional[int]]:
    """
    Generate a simplified response using a single prompt approach.
    
    Args:
        query (str): The user's query
        conversation_history (Optional[str]): Previous conversation history if available
        user_persona (Optional[Dict[str, Any]]): The user's persona data
        purpose (str): The purpose of the query
        conversation_memory (Optional[Dict[str, Any]]): The conversation memory data
        conversation_id (Optional[int]): The conversation ID to fetch assigned prompt
        user_id (Optional[int]): The user ID for fetching previous memories
        current_curiosity_score (int): The latest curiosity score before generating this turn
        
    Returns:
        Tuple[str, str, str, Dict[str, Any], str, Optional[int]]: The response, the prompt template (with placeholders), the formatted prompt (sent to LLM), the full structured response data, the prompt name used, and the prompt version number
    """
    logger.info(f"Generating simplified response for query: {query} (purpose: {purpose}, conversation_id: {conversation_id})")
    
    try:
        effective_prompt_context = prompt_context or await resolve_prompt_execution_context(
            purpose=purpose,
            conversation_id=conversation_id,
        )
        prompt_template = effective_prompt_context.prompt_template
        prompt_name_used = effective_prompt_context.prompt_name
        prompt_version_used = effective_prompt_context.prompt_version

        # Format the prompt with query and conversation history
        logger.info(
            f"Formatting prompt with query length={len(query)} and "
            f"history length={len(conversation_history) if conversation_history else 0}"
        )
        resolved_previous_memories = previous_memories
        if (
            resolved_previous_memories is None
            and "{{PREVIOUS_CONVERSATIONS_MEMORY" in prompt_template
            and user_id
            and conversation_id
        ):
            try:
                resolved_previous_memories = await api_service.get_previous_memories(user_id, conversation_id)
                logger.info(f"Fetched {len(resolved_previous_memories)} previous memories for user {user_id}")
            except Exception as e:
                logger.warning(f"Could not fetch previous memories: {e}")

        formatted_prompt = render_prompt_template(
            prompt_template,
            context=RenderContext(
                query=query,
                conversation_history=conversation_history,
                current_curiosity_score=current_curiosity_score,
                previous_memories=resolved_previous_memories,
                user_persona=user_persona,
                core_theme=core_theme,
                conversation_memory=conversation_memory,
                user_id=user_id,
                user_created_at=user_created_at,
                user_name=user_name,
            ),
        )

        # Call LLM service
        from src.services.llm_service import LLMService
        llm_service = LLMService()
        
        messages = [
            {"role": "system", "content": "You are a Curiosity Coach, designed to engage students in thought-provoking conversations that foster critical thinking and curiosity."},
            {"role": "user", "content": formatted_prompt}
        ]
        
        response_text = llm_service.get_completion(messages, call_type="simplified_conversation")
        return (
            response_text,
            prompt_template,
            formatted_prompt,
            {
                "response": response_text,
                "needs_clarification": False,
                "follow_up_questions": [],
            },
            prompt_name_used,
            prompt_version_used,
        )

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

async def process_query(
    query: str,
    config: Optional[FlowConfig] = None,
    conversation_history: Optional[str] = None,
    user_persona: Optional[Dict[str, Any]] = None,
    purpose: str = "chat",
    conversation_memory: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[int] = None,
    user_id: Optional[int] = None,
    user_created_at: Optional[str] = None,
    user_name: Optional[str] = None,
    current_curiosity_score: int = 0,
    prompt_context: Optional[PromptExecutionContext] = None,
    core_theme: Optional[str] = None,
    previous_memories: Optional[List[Dict[str, Any]]] = None,
) -> ProcessQueryResponse:
    """
    Process a user query through the intent identification and response generation pipeline.
    
    Args:
        query (str): The user's query to process
        config (Optional[FlowConfig]): Configuration object for the processing pipeline.
            If None, default configuration will be used.
        conversation_history (Optional[str]): The conversation history between the user and the system.
        user_persona (Optional[Dict[str, Any]]): The user's persona data.
        purpose (str): The purpose of the query
        conversation_memory (Optional[Dict[str, Any]]): The conversation memory data.
        conversation_id (Optional[int]): The conversation ID to fetch assigned prompt
        user_id (Optional[int]): The user ID for fetching previous memories
        
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
            'needs_clarification': False,
            'current_curiosity_score': current_curiosity_score,
        }
        
        # Check if simplified mode is enabled (either by config or force flag)
        is_simplified_mode = FORCE_SIMPLIFIED_MODE or effective_config.use_simplified_mode
        
        if is_simplified_mode:
            logger.info("Using simplified conversation mode")
            
            # Generate simplified response
            response, prompt_template, formatted_prompt, response_data, prompt_name_used, prompt_version_used = await generate_simplified_response(
                query,
                conversation_history,
                user_persona,
                purpose,
                conversation_memory,
                conversation_id,
                user_id,
                user_created_at,
                user_name,
                current_curiosity_score=current_curiosity_score,
                prompt_context=prompt_context,
                core_theme=core_theme,
                previous_memories=previous_memories,
            )
            
            # Check if we need clarification
            needs_clarification = response_data.get("needs_clarification", False)
            
            # Update pipeline data with follow-up questions if needed
            if needs_clarification:
                pipeline_data['needs_clarification'] = True
                pipeline_data['follow_up_questions'] = response_data.get("follow_up_questions", [])
                # No need for partial_understanding in simplified mode
            
            # Update pipeline data - always use 'simplified_conversation' as step name for schema validation
            # Track the actual prompt used separately for debugging/tracking
            simplified_step_data = {
                'name': 'simplified_conversation',  # Must match schema expectations
                'enabled': True,
                'prompt_template': prompt_template,  # Original template with placeholders
                'formatted_prompt': formatted_prompt,  # What actually went to the LLM
                'prompt': formatted_prompt,  # Keep for backwards compatibility
                'result': response,
                'response_data': response_data,
                'needs_clarification': needs_clarification,
                'prompt_name': prompt_name_used,  # Track actual prompt purpose (visit_1, visit_2, etc.)
                'prompt_version': prompt_version_used  # Include version for debugging
            }
            pipeline_data['steps'].append(simplified_step_data)
            pipeline_data['final_response'] = response
            
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
    user_persona: Optional[Dict[str, Any]] = None,
    purpose: str = "chat",
    conversation_memory: Optional[Dict[str, Any]] = None,
    conversation_id: Optional[int] = None,
    user_id: Optional[int] = None,
    user_created_at: Optional[str] = None,
    user_name: Optional[str] = None,
    current_curiosity_score: int = 0,
    prompt_context: Optional[PromptExecutionContext] = None,
    core_theme: Optional[str] = None,
    previous_memories: Optional[List[Dict[str, Any]]] = None,
) -> ProcessQueryResponse:
    """
    Process a follow-up response from the student to determine intent and generate a final response.
    
    Args:
        original_query (str): The original query that initiated the conversation
        follow_up_questions (List[str]): The follow-up questions previously asked
        student_response (str): The student's response to the follow-up questions
        config (Optional[FlowConfig]): Configuration object for the processing pipeline
        conversation_history (Optional[str]): Previous conversation history
        user_persona (Optional[Dict[str, Any]]): The user's persona data.
        purpose (str): The purpose of the query
        conversation_memory (Optional[Dict[str, Any]]): The conversation memory data.
        conversation_id (Optional[int]): The conversation ID to fetch assigned prompt
        user_id (Optional[int]): The user ID for fetching previous memories
        
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
            'final_response': None,
            'current_curiosity_score': current_curiosity_score,
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
            response, prompt_template, formatted_prompt, response_data, prompt_name_used, prompt_version_used = await generate_simplified_response(
                student_response,
                enhanced_conversation_history,
                user_persona,
                purpose,
                conversation_memory,
                conversation_id,
                user_id,
                user_created_at,
                user_name,
                current_curiosity_score=current_curiosity_score,
                prompt_context=prompt_context,
                core_theme=core_theme,
                previous_memories=previous_memories,
            )
            
            # Check if we need clarification (again)
            needs_clarification = response_data.get("needs_clarification", False)
            
            # Update pipeline data with follow-up questions if needed
            if needs_clarification:
                pipeline_data['needs_clarification'] = True
                pipeline_data['follow_up_questions'] = response_data.get("follow_up_questions", [])
            
            # Update pipeline data - always use 'simplified_conversation' as step name for schema validation
            # Track the actual prompt used separately for debugging/tracking
            simplified_step_data = {
                'name': 'simplified_conversation',  # Must match schema expectations
                'enabled': True,
                'prompt_template': prompt_template,  # Original template with placeholders
                'formatted_prompt': formatted_prompt,  # What actually went to the LLM
                'prompt': formatted_prompt,  # Keep for backwards compatibility
                'result': response,
                'response_data': response_data,
                'needs_clarification': needs_clarification,
                'prompt_name': prompt_name_used,  # Track actual prompt purpose (visit_1, visit_2, etc.)
                'prompt_version': prompt_version_used  # Include version for debugging
            }
            pipeline_data['steps'].append(simplified_step_data)
            pipeline_data['final_response'] = response
            
            return ProcessQueryResponse(**pipeline_data)

    except Exception as e:
        logger.error(f"Error in process_follow_up: {str(e)}", exc_info=True)
        raise
