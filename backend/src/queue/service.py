import os
import json
import boto3
import time
import uuid
import httpx  # Import httpx
from src.config.settings import settings

# Determine mode based on settings
# LOCAL_BRAIN_URL = os.getenv("LOCAL_BRAIN_ENDPOINT_URL") # Remove this direct getenv
# Local mode is active only if APP_ENV is development AND the local URL is set in settings
LOCAL_MODE = settings.APP_ENV == 'development' and bool(settings.LOCAL_BRAIN_ENDPOINT_URL)

class QueueService:
    """Service for interacting with SQS queue or a local HTTP endpoint"""

    def __init__(self):
        """Initialize SQS client or local endpoint URL using settings"""
        self.local_mode = LOCAL_MODE
        self.local_brain_url = settings.LOCAL_BRAIN_ENDPOINT_URL # Use settings here
        self.queue_url = settings.SQS_QUEUE_URL

        if self.local_mode:
            print(f"Using local mode (APP_ENV={settings.APP_ENV}, LOCAL_BRAIN_ENDPOINT_URL is set). Sending messages to: {self.local_brain_url}")
        else:
            if settings.APP_ENV != 'development':
                 print(f"Using SQS mode (APP_ENV={settings.APP_ENV}). Queue URL: {self.queue_url}")
            elif not self.local_brain_url: # Check the value from settings
                 print(f"Using SQS mode (APP_ENV={settings.APP_ENV}, but LOCAL_BRAIN_ENDPOINT_URL is not set in settings). Queue URL: {self.queue_url}")
            else: # Should not happen based on LOCAL_MODE logic, but good for clarity
                 print(f"Using SQS mode. Queue URL: {self.queue_url}")
                 
            if not self.queue_url:
                print("Warning: SQS_QUEUE_URL is not set. SQS mode will likely fail.")
                self.sqs = None
                return
            
            try:
                self.sqs = boto3.client(
                    'sqs',
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                )
                # Basic check if client was created
                if self.sqs is None:
                     raise Exception("SQS client initialization failed.")
                # Optional: Test connection (can slow down startup)
                # self.sqs.list_queues()
                print("SQS client initialized successfully.")
            except Exception as e:
                print(f"AWS SQS connection failed: {e}")
                print("SQS operations will likely fail.")
                self.sqs = None # Ensure sqs is None if setup fails

    async def send_message(self, user_id, message_content, message_id=None, purpose="chat", conversation_id=None):
        """
        Send a message to the SQS queue or local HTTP endpoint.

        Args:
            user_id (int): ID of the user sending the message
            message_content (str): Content of the message
            message_id (int, optional): ID of the message in the database
            purpose (str, optional): Purpose of the message (chat, test_generation, doubt_solver)
            conversation_id (str, optional): ID of the conversation this message belongs to

        Returns:
            dict: Response from SQS or local endpoint call
        """
        if not conversation_id:
            conversation_id = f"conv_{uuid.uuid4().hex[:8]}"

        message_body = {
            'user_id': str(user_id),
            'message_id': str(message_id) if message_id else f"msg_{uuid.uuid4().hex[:8]}",
            'purpose': purpose,
            'conversation_id': conversation_id,
            'message_content': message_content,
            'timestamp': time.time()
        }

        print("INSIDE QUEUE SERVICE SEND MESSAGE")
        print("local mode", self.local_mode)
        if self.local_mode:
            if not self.local_brain_url: # Check the value from settings
                 # This check is somewhat redundant now due to the LOCAL_MODE definition, but safe to keep
                 print("Error: Local mode is enabled but LOCAL_BRAIN_ENDPOINT_URL is not set in settings.")
                 return {"error": "Local endpoint URL not configured"}
            try:
                # Use httpx for async HTTP requests
                async with httpx.AsyncClient() as client:
                    # Ensure the URL includes the specific endpoint path
                    target_url = f"{self.local_brain_url.rstrip('/')}/query"
                    response = await client.post(target_url, json=message_body)
                    response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
                    print(f"Local endpoint call successful: Status {response.status_code} to {target_url}")
                    # Attempt to parse JSON, return raw text if fails
                    try:
                         return response.json()
                    except json.JSONDecodeError:
                         return {"status_code": response.status_code, "content": response.text}
            except httpx.RequestError as exc:
                target_url = f"{self.local_brain_url.rstrip('/')}/query" # Ensure target_url is defined for error message
                print(f"Caught httpx.RequestError sending message to {target_url}. Type: {type(exc)}, Details: {repr(exc)}")
                return {"error": f"Failed to connect/read from local endpoint: {exc}"}
            except httpx.HTTPStatusError as exc:
                 # Log the response body for status errors too, might contain helpful info
                 print(f"Local endpoint returned error status {exc.response.status_code}. Response: {exc.response.text}")
                 return {"error": f"Local endpoint error: {exc.response.status_code}", "details": exc.response.text}
            except json.JSONDecodeError as exc:
                 # Explicitly catch JSON errors after successful status
                 print(f"Failed to decode JSON response from {target_url}. Status: {response.status_code}, Response: {response.text}. Error: {exc}")
                 return {"error": "Invalid JSON response from local endpoint", "details": response.text}
            except Exception as e:
                 # Catch-all for other unexpected errors during HTTP call or response processing
                 print(f"An unexpected error occurred during local endpoint call. Type: {type(e)}, Details: {repr(e)}")
                 return {"error": f"Unexpected error: {str(e)}"}

        else: # SQS Mode
            print("I AM IN SQS MODE")
            if not self.queue_url or not self.sqs:
                print("SQS Error: Queue URL not configured or SQS client failed initialization. Cannot send message.") # Enhanced log
                # Optionally, return a specific error structure
                return {"error": "SQS not configured or unavailable"}

            print(f"SQS Mode: Attempting to send message to queue: {self.queue_url}") # Log before try
            print(f"SQS Mode: Message Body: {json.dumps(message_body)}") # Log message body
            try:
                response = self.sqs.send_message(
                    QueueUrl=self.queue_url,
                    MessageBody=json.dumps(message_body),
                    MessageAttributes={
                        'MessageType': {
                            'DataType': 'String',
                            'StringValue': 'UserMessage'
                        }
                    }
                )
                print(f"SQS Mode: Message sent successfully. MessageId: {response.get('MessageId')}") # Log success + ID
                return response
            except Exception as e:
                # Capture more details about the exception
                error_type = type(e).__name__
                print(f"SQS Error: Failed sending message to {self.queue_url}. Error Type: {error_type}, Details: {e}") # Enhanced log
                # Consider what to return on failure
                return {"error": f"SQS send failed: {str(e)}"}

    # --- Removed receive_message method as it was tied to mock mode --- 
    # If SQS receiving logic is needed elsewhere, it should be implemented there.

# Create singleton instance
queue_service = QueueService() 