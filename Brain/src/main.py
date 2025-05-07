from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ValidationError
import uvicorn
import time
import uuid
import httpx # Added for callback
import asyncio # Added for synchronous callback execution
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv # Added import
import json # Added for S3 config parsing
import boto3 # Added for S3 interaction
from botocore.exceptions import NoCredentialsError, PartialCredentialsError, ClientError # Added for S3 error handling
from mangum import Mangum

from src.process_query_entrypoint import process_query, ProcessQueryResponse
from src.utils.logger import logger
from src.core.intent_identifier import identify_intent, IntentIdentificationError # Import identify_intent
from src.core.knowledge_retrieval import retrieve_knowledge, KnowledgeRetrievalError
from src.core.learning_enhancement import generate_enhanced_response, LearningEnhancementError # Import learning enhancement
from src.config_models import FlowConfig # Import FlowConfig from new location

# Load environment variables from .env file
load_dotenv() # Added call

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
)

# Setup templates
templates = Jinja2Templates(directory="src/templates")

# --- Configuration Models ---
# FlowConfig class has been moved to src.config_models.py

# --- Payload Models ---
class MessagePayload(BaseModel):
    user_id: str
    message_id: str
    purpose: str
    conversation_id: str
    message_content: str
    timestamp: float # Assuming timestamp is a float epoch time

# Updated dequeue function containing the core logic
async def dequeue(message: MessagePayload, background_tasks: Optional[BackgroundTasks] = None):
    """
    Processes a message received either from SQS or the /query endpoint.
    """
    logger.info(f"Processing message: {message.model_dump()}")
    print(f"Processing message: {message.model_dump()}") # Log the message regardless of purpose

    try:
        if message.purpose == "chat":
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


            # Process the query and get response only if purpose is 'chat'
            logger.info(f"Processing query with S3-loaded config (if available): {s3_config_dict}")
            response_data = process_query(
                user_input, 
                config=flow_config_instance,
                conversation_history=conversation_history_str # Pass fetched history
            )

            # Prepare and schedule the callback if response was generated
            if response_data and response_data.response:
                callback_payload = {
                    "user_id": int(message.user_id), # Ensure correct type
                    "conversation_id": message.conversation_id,
                    "original_message_id": int(message.message_id) if message.message_id.isdigit() else None, # Handle non-int IDs if needed
                    "llm_response": response_data.response, # The final response string
                    "pipeline_data": response_data.pipeline_data.model_dump() # The pipeline data
                }
                # Schedule callback differently based on context
                if background_tasks:
                    # Running in FastAPI context, use background task
                    background_tasks.add_task(perform_backend_callback, callback_payload)
                    logger.info(f"Scheduled background callback task for user_id: {message.user_id}")
                else:
                    # Running in non-FastAPI context (e.g., SQS Lambda path), run synchronously
                    logger.info(f"Running callback synchronously for user_id: {message.user_id}")
                    try:
                        asyncio.run(perform_backend_callback(callback_payload))
                    except Exception as cb_exc:
                        # Log synchronous callback errors, but don't let them fail the main dequeue process necessarily
                        logger.error(f"Error during synchronous callback execution: {cb_exc}", exc_info=True)
                        # Depending on requirements, you might want to re-raise or handle differently
            else:
                 logger.warning(f"No response generated for chat message, callback not scheduled for user_id: {message.user_id}")


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

class QueryRequest(BaseModel):
    query: str

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/rules", response_class=HTMLResponse)
async def show_rules(request: Request):
    try:
        # Call identify_intent to get only the template
        intent_prompt_template = identify_intent(query="dummy", get_prompt_template_only=True)

        # Call retrieve_knowledge to get only the template
        # Pass dummy topics as they are required by the signature but not used
        knowledge_prompt_template = retrieve_knowledge(main_topic="dummy", related_topics=[], get_prompt_template_only=True)

        # Call generate_enhanced_response to get only the template
        # Pass dummy initial response and context
        learning_prompt_template = generate_enhanced_response(initial_response="dummy", context_info="dummy", get_prompt_template_only=True)

        return templates.TemplateResponse(
            "rules.html",
            {
                "request": request,
                "intent_prompt_template": intent_prompt_template,
                "knowledge_prompt_template": knowledge_prompt_template,
                "learning_prompt_template": learning_prompt_template # Pass learning template
            }
        )
    except (IntentIdentificationError, KnowledgeRetrievalError, LearningEnhancementError) as e: # Catch both errors
        logger.error(f"Failed to get prompt template(s) for /rules page: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Could not load rules information.")
    except Exception as e:
        logger.error(f"Unexpected error generating /rules page: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error generating rules page.")

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

        # The callback scheduling logic is now inside dequeue.
        # We just return the immediate result from dequeue.

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

if __name__ == '__main__':
    # Use uvicorn to run the app
    # reload=True enables auto-reloading for development
    uvicorn.run("main:app", host="127.0.0.1", port=5000, reload=True) 