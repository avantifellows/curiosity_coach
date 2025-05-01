from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import time
import uuid
import httpx # Added for callback
import asyncio # Added for synchronous callback execution
from typing import Optional
import os
from dotenv import load_dotenv # Added import

from src.process_query_entrypoint import process_query
from src.utils.logger import logger
from src.core.intent_identifier import identify_intent, IntentIdentificationError # Import identify_intent
from src.core.knowledge_retrieval import retrieve_knowledge, KnowledgeRetrievalError
from src.core.learning_enhancement import generate_enhanced_response, LearningEnhancementError # Import learning enhancement

# Load environment variables from .env file
load_dotenv() # Added call

BACKEND_CALLBACK_BASE_URL = os.getenv("BACKEND_CALLBACK_BASE_URL", "http://localhost:5000")
BACKEND_CALLBACK_ROUTE = os.getenv("BACKEND_CALLBACK_ROUTE", "/api/messages/internal/brain_response")
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

# Pydantic model for the message structure
class MessagePayload(BaseModel):
    user_id: str
    message_id: str
    purpose: str
    conversation_id: str
    message_content: str
    timestamp: float # Assuming timestamp is a float epoch time

# Updated dequeue function containing the core logic
def dequeue(message: MessagePayload, background_tasks: Optional[BackgroundTasks] = None):
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

            # Process the query and get response only if purpose is 'chat'
            response_data = process_query(user_input)

            # Prepare the response content for 'chat' purpose
            content={
                'response': response_data.get('response'), # Return the main response string directly
                'prompts': response_data.get('prompts', []),
                'intermediate_responses': response_data.get('intermediate_responses', []),
                'intent': response_data.get('intent'),
                'intent_prompt': response_data.get('intent_prompt'),
                # Optionally include original message details if needed for context
                'original_message': message.model_dump()
            }

            # Prepare and schedule the callback if response was generated
            if content and 'response' in content:
                callback_payload = {
                    "user_id": int(message.user_id), # Ensure correct type
                    "conversation_id": message.conversation_id,
                    "original_message_id": int(message.message_id) if message.message_id.isdigit() else None, # Handle non-int IDs if needed
                    "response_content": content.get('response'),
                    # Pass other relevant fields from the result back to the backend
                    "intent": content.get('intent'),
                    "prompts": content.get('prompts'),
                    "intermediate_responses": content.get('intermediate_responses'),
                    "intent_prompt": content.get('intent_prompt')
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


            return content
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

@app.post("/query")
async def handle_query(message: MessagePayload, background_tasks: BackgroundTasks):
    # The /query endpoint now directly accepts the full message payload
    # and passes it to the dequeue function along with background_tasks.
    try:
        # Dequeue handles processing and schedules the callback if needed.
        result = dequeue(message, background_tasks) # Pass background_tasks

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