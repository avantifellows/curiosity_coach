from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import httpx # Added for callback
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv # Added import
import json # Added for S3 config parsing
import boto3 # Added for S3 interaction
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError # Added for S3 error handling
from mangum import Mangum
from pathlib import Path
import asyncio

from src.process_query_entrypoint import process_query, process_follow_up, ProcessQueryResponse
from src.utils.logger import logger
# from src.core.conversational_intent_gatherer import gather_initial_intent, process_follow_up_response, ConversationalIntentError
# from src.core.knowledge_retrieval import retrieve_knowledge, KnowledgeRetrievalError
# from src.core.learning_enhancement import generate_enhanced_response, LearningEnhancementError
from src.config_models import FlowConfig
from src.services.llm_service import LLMService
from src.services.api_service import api_service
from src.schemas import ConversationMemoryData
from pydantic import ValidationError

# Load environment variables from .env file
load_dotenv()

BACKEND_CALLBACK_BASE_URL = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")

BACKEND_CALLBACK_ROUTE = os.getenv("BACKEND_CALLBACK_ROUTE", "/api/internal/brain_response")
BACKEND_CALLBACK_URL = f"{BACKEND_CALLBACK_BASE_URL}{BACKEND_CALLBACK_ROUTE}"

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
    expose_headers=["*"]  # Expose all headers
)

# Setup templates
templates = Jinja2Templates(directory="src/templates")

# Initialize prompts at startup
async def init_prompts():
    """Initialize prompts from text files during application startup"""
    logger.info("Initializing prompts from text files...")
    
    prompts_dir = Path(__file__).parent / "prompts"
    if not prompts_dir.exists():
        logger.error(f"Prompts directory not found at {prompts_dir}")
        return
    
    # Prompt name mapping (filename to friendly name)
    prompt_names = {
        "simplified_conversation_prompt.txt": "simplified_conversation",  # Changed to match the expected name
        "intent_gathering_prompt.txt": "intent_gathering",
        "knowledge_retrieval_prompt.txt": "knowledge_retrieval",
        "response_generator_prompt.txt": "response_generation",
        "learning_prompt.txt": "learning_enhancement",
        "follow_up_response_prompt.txt": "follow_up_response",
        "response_generator_personal_prompt.txt": "response_generation_personal",
        "response_generator_conversational_prompt.txt": "response_generation_conversational"
    }
    
    # Find all text files in prompts directory
    prompt_files = [f for f in prompts_dir.glob("*.txt") if f.name in prompt_names]
    if not prompt_files:
        logger.warning(f"No prompt text files found in {prompts_dir}")
        return
    
    logger.info(f"Found {len(prompt_files)} prompt files")
    
    # Get the backend URL
    backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
    api_url = f"{backend_url}/api/prompts"
    
    # Add each prompt to the database
    async with httpx.AsyncClient() as client:
        for prompt_file in prompt_files:
            try:
                prompt_name = prompt_names.get(prompt_file.name, prompt_file.stem)
                logger.info(f"Processing prompt file: {prompt_file.name} -> {prompt_name}")
                
                with open(prompt_file, "r") as f:
                    prompt_text = f.read()
                
                # First check if prompt exists at all (not just the active version)
                try:
                    check_prompt_url = f"{api_url}/{prompt_name}"
                    logger.info(f"Checking if prompt exists: GET {check_prompt_url}")
                    prompt_response = await client.get(check_prompt_url)
                    
                    # Prompt exists
                    if prompt_response.status_code == 200:
                        # Now check if it has an active version
                        check_active_url = f"{api_url}/{prompt_name}/versions/active/"
                        active_response = await client.get(check_active_url)
                        
                        if active_response.status_code == 200:
                            logger.info(f"Prompt {prompt_name} already exists with active version")
                            continue
                        else:
                            logger.info(f"Prompt {prompt_name} exists but may not have an active version - will add one")
                    else:
                        logger.info(f"Prompt {prompt_name} does not exist - will create it")
                    
                except Exception as e:
                    logger.warning(f"Error checking if prompt {prompt_name} exists: {str(e)}")
                
                # Try to create the prompt first
                prompt_exists = prompt_response.status_code == 200 if 'prompt_response' in locals() else False
                
                if not prompt_exists:
                    try:
                        logger.info(f"Creating prompt {prompt_name}")
                        prompt_create_url = f"{api_url}/"  # Ensure trailing slash
                        prompt_create_response = await client.post(
                            prompt_create_url,
                            json={
                                "name": prompt_name,
                                "description": f"Prompt for {prompt_name.replace('_', ' ')}",
                                "initial_version_text": prompt_text  # Create with initial version in one request
                            }
                        )
                        
                        if prompt_create_response.status_code in (200, 201):
                            logger.info(f"Created prompt: {prompt_name} with initial version")
                            continue  # Created with initial version, can skip creating version
                        elif prompt_create_response.status_code == 409:  # Already exists
                            logger.info(f"Prompt {prompt_name} already exists (409 conflict)")
                            prompt_exists = True
                        else:
                            logger.warning(f"Failed to create prompt {prompt_name}. Status: {prompt_create_response.status_code}, Response: {prompt_create_response.text}")
                    except Exception as e:
                        logger.error(f"Exception creating prompt {prompt_name}: {str(e)}")
                
                # If we get here, either prompt exists or failed to create with initial version
                # Try to create a version with set_active=true query param
                if prompt_exists:
                    try:
                        create_version_url = f"{api_url}/{prompt_name}/versions?set_active=true"
                        logger.info(f"Creating prompt version with POST to {create_version_url}")
                        version_response = await client.post(
                            create_version_url,
                            json={
                                "prompt_text": prompt_text
                            }
                        )
                        
                        if version_response.status_code in (200, 201):
                            logger.info(f"Created active prompt version for {prompt_name}")
                        else:
                            logger.warning(f"Failed to create prompt version for {prompt_name}. Status: {version_response.status_code}, Response: {version_response.text}")
                    except Exception as e:
                        logger.error(f"Exception creating prompt version for {prompt_name}: {str(e)}")
            except Exception as e:
                logger.error(f"Unexpected error processing prompt file {prompt_file.name}: {str(e)}")
    
    logger.info("Prompt initialization complete")

@app.on_event("startup")
async def startup_event():
    """Run initialization tasks on application startup"""
    try:
        # Initialize prompts from text files
        await init_prompts()
    except Exception as e:
        logger.error(f"Error during startup initialization: {str(e)}")

# --- Payload Models ---
class MessagePayload(BaseModel):
    user_id: str
    message_id: str
    purpose: str
    conversation_id: str
    message_content: str
    timestamp: float # Assuming timestamp is a float epoch time
    is_follow_up_response: bool = False  # New field to indicate if this is a response to follow-up questions
    original_query: Optional[str] = None  # Original query if this is a follow-up response
    follow_up_questions: Optional[List[str]] = None  # Follow-up questions that were asked

class BatchTaskRequest(BaseModel):
    task_type: str
    conversation_ids: List[int]

# Updated dequeue function containing the core logic
async def dequeue(message: MessagePayload, background_tasks: Optional[BackgroundTasks] = None):
    """
    Processes a message received either from SQS or the /query endpoint.
    """
    logger.info(f"Processing message: {message.model_dump()}")
    print(f"Processing message: {message.model_dump()}") # Log the message regardless of purpose

    try:
        if message.purpose in ["chat", "test-prompt"]:
            user_input = message.message_content
            if not user_input:
                # Although the model enforces this, good to double-check
                raise HTTPException(status_code=400, detail='No message_content provided')

            # Attempt to load config from S3
            s3_config_dict: Optional[Dict[str, Any]] = FlowConfig.get_config_from_s3()
            
            # Convert s3_config_dict to FlowConfig instance if it exists
            flow_config_instance: Optional[FlowConfig] = None
            if s3_config_dict is not None:
                try:
                    flow_config_instance = FlowConfig(**s3_config_dict)
                except Exception as e: # Catch Pydantic validation errors or others
                    logger.error(f"Error creating FlowConfig instance from S3 data: {s3_config_dict}. Error: {e}", exc_info=True)
                    pass # flow_config_instance remains None
            else:
                # If s3_config_dict is None (e.g., S3 not configured or file not found and init failed),
                # process_query will use its internal default FlowConfig.
                logger.info("No S3 config dictionary loaded, process_query will use default FlowConfig.")

            # Initialize conversation_history_str
            conversation_history_str: Optional[str] = None
            
            # Check if any step wants to use conversation history
            should_fetch_history = False
            if flow_config_instance and flow_config_instance.steps:
                for step_config in flow_config_instance.steps:
                    if step_config.use_conversation_history and step_config.is_use_conversation_history_valid:
                        should_fetch_history = True
                        break
            
            if should_fetch_history and message.conversation_id:
                logger.info(f"Fetching conversation history for conversation_id: {message.conversation_id} via internal endpoint")
                try:
                    # Use the new internal endpoint that does not require auth for Brain service
                    history_url = f"{BACKEND_CALLBACK_BASE_URL.rstrip('/')}/api/internal/conversations/{message.conversation_id}/messages_for_brain"
                    
                    async with httpx.AsyncClient() as client:
                        response = await client.get(history_url)
                    
                    if response.status_code == 200:
                        history_data = response.json()
                        if history_data.get("success") and "messages" in history_data:
                            fetched_messages = history_data["messages"]
                            # Filter out the current message being processed, if present
                            # Assuming message.message_id is a string, and history message IDs are int.
                            current_message_id_int: Optional[int] = None
                            if message.message_id and message.message_id.isdigit():
                                current_message_id_int = int(message.message_id)

                            relevant_messages = []
                            for msg_data in fetched_messages:
                                if current_message_id_int is None or msg_data.get('id') != current_message_id_int:
                                    sender = "User" if msg_data.get('is_user') else "AI"
                                    relevant_messages.append(f"{sender}: {msg_data.get('content')}")
                            
                            if relevant_messages:
                                conversation_history_str = "\n".join(relevant_messages)
                                logger.info(f"Successfully fetched and formatted conversation history. Length: {len(conversation_history_str)}")
                            else:
                                logger.info("No prior messages found in history to use.")
                        else:
                            logger.warning(f"Failed to fetch conversation history: API response indicates failure or malformed data. Response: {response.text}")
                    else:
                        logger.error(f"Error fetching conversation history: API responded with status {response.status_code}. Response: {response.text}")
                except httpx.RequestError as e:
                    logger.error(f"HTTPX RequestError fetching conversation history: {e}", exc_info=True)
                except Exception as e:
                    logger.error(f"Unexpected error fetching or processing conversation history: {e}", exc_info=True)

            # Determine if this is a new query or a follow-up response
            response_data = None
            if message.is_follow_up_response and message.original_query and message.follow_up_questions:
                # This is a follow-up response, process it differently
                logger.info(f"Processing follow-up response for original query: {message.original_query}")
                response_data = await process_follow_up(
                    original_query=message.original_query, 
                    follow_up_questions=message.follow_up_questions,
                    student_response=user_input,
                    config=flow_config_instance,
                    conversation_history=conversation_history_str,
                    purpose=message.purpose
                )
            else:
                # Process as a regular query
                logger.info(f"Processing query with S3-loaded config (if available): {s3_config_dict}")
                response_data = await process_query(
                    user_input, 
                    config=flow_config_instance,
                    conversation_history=conversation_history_str,
                    purpose=message.purpose
                )

            # Create a client for fetching the prompt version ID
            backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
            async with httpx.AsyncClient() as client:
                # Check if the response needs clarification (has follow-up questions)
                if response_data.needs_clarification and response_data.follow_up_questions:
                    # Prepare and schedule the callback with follow-up questions
                    callback_payload = {
                        "user_id": int(message.user_id),
                        "conversation_id": message.conversation_id,
                        "original_message_id": int(message.message_id) if message.message_id.isdigit() else None,
                        "llm_response": response_data.final_response,  # This contains the formatted follow-up questions
                        "pipeline_data": response_data.model_dump(),  # Include all pipeline data
                        "needs_clarification": True,
                        "follow_up_questions": response_data.follow_up_questions,
                        "original_query": message.original_query if message.is_follow_up_response else user_input,
                        "prompt_version_id": await get_prompt_version_id(client, backend_url, "simplified_conversation", message.purpose)
                    }
                else:
                    # Prepare and schedule the callback with the final response
                    callback_payload = {
                        "user_id": int(message.user_id),
                        "conversation_id": message.conversation_id,
                        "original_message_id": int(message.message_id) if message.message_id.isdigit() else None,
                        "llm_response": response_data.final_response,
                        "pipeline_data": response_data.model_dump(),
                        "needs_clarification": False,
                        "prompt_version_id": await get_prompt_version_id(client, backend_url, "simplified_conversation", message.purpose)
                    }

            # Schedule callback
            if background_tasks:
                # Running in FastAPI context, use background task
                background_tasks.add_task(perform_backend_callback, callback_payload)
                logger.info(f"Scheduled background callback task for user_id: {message.user_id}")
            else:
                # Running in non-FastAPI context (e.g., SQS Lambda path), run synchronously
                logger.info(f"Running callback synchronously for user_id: {message.user_id}")
                try:
                    await perform_backend_callback(callback_payload)
                except Exception as cb_exc:
                    logger.error(f"Error during awaited callback execution (SQS context): {cb_exc}", exc_info=True)

            return response_data.model_dump()
        else:
            # Handle other purposes like "test_generation", "doubt_solver", "other"
            logger.info(f"Received message with purpose '{message.purpose}', not processing further.")
            # Return a specific response for non-chat purposes
            return {
                "status": "received",
                "message": f"Message with purpose '{message.purpose}' received but not processed.",
                "original_message": message.model_dump()
            }

    except Exception as e:
        logger.error(f"Error processing message in dequeue: {e}", exc_info=True)
        # Reraise as HTTPException for FastAPI to handle centrally
        # Note: If called outside FastAPI context (e.g., Lambda), this needs adjustment
        raise HTTPException(status_code=500, detail=f"Error processing message: {str(e)}")

async def perform_backend_callback(payload: dict):
    """Sends the processing result back to the backend service."""
    logger.info(f"Performing callback to backend for user: {payload.get('user_id')}")
    logger.info(f"Attempting callback to URL: {BACKEND_CALLBACK_URL}")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(BACKEND_CALLBACK_URL, json=payload)
            response.raise_for_status() # Raise exception for 4xx/5xx errors
            logger.info(f"Backend callback successful, status: {response.status_code}")
    except httpx.RequestError as exc:
        logger.error(f"Callback request error to {BACKEND_CALLBACK_URL}: {exc}")
    except httpx.HTTPStatusError as exc:
        logger.error(f"Callback HTTP status error: {exc.response.status_code} - {exc.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error during callback: {e}", exc_info=True)

async def get_prompt_version_id(client, backend_url, prompt_name, purpose="chat"):
    """Fetch the appropriate prompt version ID for a given prompt name based on purpose."""
    try:
        if purpose == "chat":
            # For chat endpoint, use production version
            version_url = f"{backend_url}/api/prompts/{prompt_name}/versions/production"
        else:
            # For test-prompt and others, use active version
            version_url = f"{backend_url}/api/prompts/{prompt_name}/versions/active"
            
        response = await client.get(version_url)
        if response.status_code == 200:
            data = response.json()
            version_type = "production" if purpose == "chat" else "active"
            is_production = data.get("is_production", False)
            logger.info(f"Retrieved {version_type} version {data.get('version_number')} (ID: {data.get('id')}, production: {is_production}) for prompt '{prompt_name}' (purpose: {purpose})")
            return data.get("id")
    except Exception as e:
        logger.error(f"Error fetching prompt version ID for {prompt_name} (purpose: {purpose}): {e}")
    return None

class QueryRequest(BaseModel):
    query: str

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/rules", response_class=HTMLResponse)
async def show_rules(request: Request):
    """
    Route that displays the rules/processing flow documentation page.
    """
    try:
        # Attempt to fetch active prompt versions for all relevant prompts
        backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
        prompts_to_fetch = [
            "intent_gathering", 
            "knowledge_retrieval", 
            "response_generation",
            "learning_enhancement"
        ]
        
        prompt_templates = {}
        
        for prompt_name in prompts_to_fetch:
            try:
                active_version_url = f"{backend_url}/api/prompts/{prompt_name}/versions/active"
                logger.info(f"Fetching active prompt version for '{prompt_name}' from: {active_version_url}")
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(active_version_url)
                
                if response.status_code == 200:
                    data = response.json()
                    prompt_templates[f"{prompt_name}_template"] = data.get("prompt_text", "")
                    logger.info(f"Successfully fetched active version for prompt: {prompt_name}")
                else:
                    logger.warning(f"No active version found for prompt '{prompt_name}' ({response.status_code}). Will use local fallback.")
                    # Load from file as fallback
                    prompt_file_path = os.path.join(os.path.dirname(__file__), "prompts", f"{prompt_name}_prompt.txt")
                    if os.path.exists(prompt_file_path):
                        logger.info(f"Falling back to local prompt template: {prompt_file_path}")
                        with open(prompt_file_path, "r") as f:
                            prompt_templates[f"{prompt_name}_template"] = f.read()
                        logger.info(f"Successfully loaded local prompt template: {prompt_file_path}")
                    else:
                        logger.error(f"Could not load prompt template: {prompt_file_path} does not exist")
                        prompt_templates[f"{prompt_name}_template"] = "Error: Prompt template could not be loaded."
            except Exception as e:
                logger.error(f"Error fetching prompt template '{prompt_name}': {str(e)}", exc_info=True)
                prompt_templates[f"{prompt_name}_template"] = f"Error loading template: {str(e)}"
        
        return templates.TemplateResponse("rules.html", {
            "request": request, 
            **prompt_templates
        })
    except Exception as e:
        logger.error(f"Error in rules endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/simplified_rules", response_class=HTMLResponse)
async def show_simplified_rules(request: Request):
    """
    Route that displays the simplified rules/processing flow documentation page.
    """
    try:
        # Attempt to fetch the simplified conversation prompt template
        backend_url = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
        prompt_name = "simplified_conversation"
        
        try:
            active_version_url = f"{backend_url}/api/prompts/{prompt_name}/versions/active"
            logger.info(f"Fetching active prompt version for '{prompt_name}' from: {active_version_url}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(active_version_url)
            
            if response.status_code == 200:
                data = response.json()
                simplified_conversation_template = data.get("prompt_text", "")
                logger.info(f"Successfully fetched active version for prompt: {prompt_name}")
            else:
                logger.warning(f"No active version found for prompt '{prompt_name}' ({response.status_code}). Will use local fallback.")
                # Load from file as fallback
                prompt_file_path = os.path.join(os.path.dirname(__file__), "prompts", f"{prompt_name}_prompt.txt")
                if os.path.exists(prompt_file_path):
                    logger.info(f"Falling back to local prompt template: {prompt_file_path}")
                    with open(prompt_file_path, "r") as f:
                        simplified_conversation_template = f.read()
                    logger.info(f"Successfully loaded local prompt template: {prompt_file_path}")
                else:
                    logger.warning(f"Could not load prompt template: {prompt_file_path} does not exist")
                    simplified_conversation_template = None
        except Exception as e:
            logger.error(f"Error fetching prompt template '{prompt_name}': {str(e)}", exc_info=True)
            simplified_conversation_template = None
        
        return templates.TemplateResponse("simplified_rules.html", {
            "request": request, 
            "simplified_conversation_template": simplified_conversation_template
        })
    except Exception as e:
        logger.error(f"Error in simplified_rules endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/get-config")
async def get_config_schema():
    """Returns the JSON schema for the FlowConfig model along with the current configuration values."""
    try:
        # Get the JSON schema
        schema = FlowConfig.model_json_schema()
        
        # Get current config values from S3
        current_config = FlowConfig.get_config_from_s3()
        
        # If no config exists in S3, use default values
        if not current_config:
            current_config = FlowConfig().model_dump(exclude_none=True)
        
        # Return both schema and current values
        return JSONResponse(content={
            "schema": schema,
            "current_values": current_config
        })
    except Exception as e:
        logger.error(f"Error generating FlowConfig schema or retrieving current values: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not retrieve configuration schema and values.")

@app.post("/set-config")
async def set_config_values(config: FlowConfig):
    """
    Receives new configuration values, validates them against FlowConfig,
    and saves them to S3.
    """
    bucket_name = os.getenv("FLOW_CONFIG_S3_BUCKET_NAME")
    object_key = os.getenv("FLOW_CONFIG_S3_KEY", "flow_config.json")

    if not bucket_name:
        logger.error("FLOW_CONFIG_S3_BUCKET_NAME not set. Cannot save config to S3.")
        raise HTTPException(status_code=500, detail="S3 bucket name not configured on server.")

    try:
        config_data_to_save = config.model_dump(exclude_none=True) # Use validated model data
        logger.info(f"Attempting to save new config to S3: s3://{bucket_name}/{object_key} - Data: {config_data_to_save}")

        s3_client = boto3.client('s3')
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=json.dumps(config_data_to_save, indent=2),
            ContentType='application/json'
        )
        logger.info(f"Successfully saved new config to S3: s3://{bucket_name}/{object_key}")
        return JSONResponse(content={"message": "Configuration updated successfully.", "new_config": config_data_to_save})
    except ClientError as e:
        logger.error(f"S3 ClientError when saving config to s3://{bucket_name}/{object_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Could not save configuration to S3: {e}")
    except (NoCredentialsError, PartialCredentialsError):
        logger.error("AWS credentials not found or incomplete for S3 access during set_config.")
        raise HTTPException(status_code=500, detail="AWS credentials error on server.")
    except Exception as e:
        logger.error(f"Failed to save config to s3://{bucket_name}/{object_key}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred while saving configuration: {e}")

@app.post("/query")
async def handle_query(message: MessagePayload, background_tasks: BackgroundTasks):
    # The /query endpoint now directly accepts the full message payload
    # and passes it to the dequeue function along with background_tasks.
    try:
        # Dequeue handles processing and schedules the callback if needed.
        result = await dequeue(message, background_tasks) # await dequeue call

        # Return the immediate result from dequeue (could be success/error/non-chat info)
        # Use JSONResponse to ensure correct content type and structure
        return JSONResponse(content=result)
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions raised by dequeue
        logger.error(f"HTTPException during dequeue: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        # Catch any other unexpected errors during the call to dequeue
        logger.error(f"Unexpected error in /query endpoint calling dequeue: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/follow-up")
async def handle_follow_up(message: MessagePayload, background_tasks: BackgroundTasks):
    """
    Endpoint specifically for handling follow-up responses to previous questions.
    """
    if not message.is_follow_up_response:
        raise HTTPException(status_code=400, detail="This endpoint is only for follow-up responses. Set is_follow_up_response to true.")
    
    if not message.original_query:
        raise HTTPException(status_code=400, detail="original_query is required for follow-up responses")
    
    if not message.follow_up_questions:
        raise HTTPException(status_code=400, detail="follow_up_questions is required for follow-up responses")
    
    # Use the same dequeue function, which now handles both regular queries and follow-ups
    try:
        result = await dequeue(message, background_tasks)
        return JSONResponse(content=result)
    except HTTPException as http_exc:
        logger.error(f"HTTPException during follow-up dequeue: {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error in /follow-up endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

async def process_memory_generation_batch(conversation_ids: List[int]):
    """
    Processes a batch of conversation IDs to generate and save memories.
    """
    logger.info(f"Starting memory generation batch for {len(conversation_ids)} conversations.")
    llm_service = LLMService()

    # Load the prompt template from the file
    try:
        prompts_dir = Path(__file__).parent / "prompts"
        with open(prompts_dir / "memory_generation_prompt.txt", "r") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        logger.error("Could not find memory_generation_prompt.txt. Aborting batch task.")
        return

    for conv_id in conversation_ids:
        try:
            logger.info(f"Processing conversation ID: {conv_id}")
            history = await api_service.get_conversation_history(conv_id)

            if history is None:
                logger.warning(f"Could not retrieve history for conversation {conv_id}. Skipping.")
                continue
            
            if not history:
                logger.info(f"Conversation {conv_id} has no history. Skipping memory generation.")
                continue

            # 1. Format history for the LLM
            formatted_history = "\n".join([f"{'User' if msg['is_user'] else 'AI'}: {msg['content']}" for msg in history])
            
            # 2. Call LLM to generate a structured memory
            prompt = prompt_template.format(conversation_history=formatted_history)
            
            response_dict = await asyncio.to_thread(
                llm_service.generate_response,
                prompt,
                call_type="response_generation" 
            )
            summary_json_str = response_dict.get("raw_response")

            if not summary_json_str:
                logger.error(f"LLM did not return a response for conversation {conv_id}.")
                continue
            
            # 3. Parse and save the memory
            try:
                # The output might be inside a code block, so we extract it.
                if "```json" in summary_json_str:
                    summary_json_str = summary_json_str.split("```json\n")[1].split("\n```")[0]
                
                # print(summary_json_str)
                summary_data = json.loads(summary_json_str)
                # print(summary_data)
                
                # Validate the data structure using the Pydantic model
                validated_data = ConversationMemoryData(**summary_data)
                
                # import ipdb; ipdb.set_trace()
                # Use the validated data (converted back to a dict) for saving
                success = await api_service.save_memory(conv_id, validated_data.model_dump())

                if success:
                    logger.info(f"Successfully generated, validated, and saved memory for conversation {conv_id}.")
                else:
                    logger.error(f"Failed to save memory for conversation {conv_id} after validation.")
            except json.JSONDecodeError:
                logger.error(f"Failed to decode LLM response into JSON for conv {conv_id}. Response: {summary_json_str}")
            except ValidationError as e:
                logger.error(f"Pydantic validation failed for conversation {conv_id}. Errors: {e.json()}")
            
        except Exception as e:
            logger.error(f"Error processing memory for conversation {conv_id}: {e}", exc_info=True)
            # Continue to the next conversation even if one fails

@app.post("/tasks", status_code=202)
async def handle_batch_tasks(task_request: BatchTaskRequest, background_tasks: BackgroundTasks):
    """
    Generic endpoint to receive and delegate batch tasks.
    Currently handles memory generation.
    """
    logger.info(f"Received task request: {task_request.model_dump()}")

    if task_request.task_type == "GENERATE_MEMORY_BATCH":
        if not task_request.conversation_ids:
            logger.info("Received memory generation task with no conversation IDs.")
            return {"message": "Task received, but no conversation IDs provided."}
        
        background_tasks.add_task(process_memory_generation_batch, task_request.conversation_ids)
        logger.info(f"Queued background task for memory generation for {len(task_request.conversation_ids)} conversations.")
        return {"message": f"Accepted task to generate memories for {len(task_request.conversation_ids)} conversations."}
    else:
        logger.warning(f"Received unknown task type: {task_request.task_type}")
        raise HTTPException(status_code=400, detail=f"Unknown task type: {task_request.task_type}")

if __name__ == '__main__':
    # Use uvicorn to run the app
    # reload=True enables auto-reloading for development
    uvicorn.run("src.main:app", host="127.0.0.1", port=int(os.getenv("PORT", "8001")), reload=True) 