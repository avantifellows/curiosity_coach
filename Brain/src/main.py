from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import time
import uuid
import httpx # Added for callback
from typing import Optional

from src.process_query_entrypoint import process_query
from src.utils.logger import logger

# TODO: Move this to settings/environment variable
BACKEND_CALLBACK_URL = "http://localhost:5000/api/messages/internal/brain_response"

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
def dequeue(message: MessagePayload):
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

@app.post("/query")
async def handle_query(message: MessagePayload, background_tasks: BackgroundTasks):
    # The /query endpoint now directly accepts the full message payload
    # and passes it to the dequeue function.
    try:
        # Dequeue still runs synchronously, but the callback will be in the background
        result = dequeue(message)

        # If dequeue processed successfully (was 'chat' and didn't raise error within itself)
        # Prepare and schedule the callback
        if message.purpose == "chat" and result and 'response' in result:
            callback_payload = {
                "user_id": int(message.user_id), # Ensure correct type
                "conversation_id": message.conversation_id,
                "original_message_id": int(message.message_id) if message.message_id.isdigit() else None, # Handle non-int IDs if needed
                "response_content": result.get('response'),
                # Pass other relevant fields from the result back to the backend
                "intent": result.get('intent'),
                "prompts": result.get('prompts'),
                "intermediate_responses": result.get('intermediate_responses'),
                "intent_prompt": result.get('intent_prompt')
            }
            # Add the callback task to run in the background
            background_tasks.add_task(perform_backend_callback, callback_payload)
            logger.info(f"Scheduled backend callback for user_id: {message.user_id}")
        else:
            logger.info(f"No callback performed for purpose: {message.purpose}")

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