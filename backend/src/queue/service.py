import os
import json
import boto3
import time
import uuid
import httpx  # Import httpx
import asyncio
import concurrent.futures
from botocore.exceptions import NoCredentialsError, ClientError # Import exceptions
from botocore.config import Config  # Import Config for timeout settings
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
        self.sqs = None
        self.sqs_available = False

        if self.local_mode:
            print(f"Using local mode (APP_ENV={settings.APP_ENV}, LOCAL_BRAIN_ENDPOINT_URL is set). Sending messages to: {self.local_brain_url}")
        else: # SQS Mode
            if not self.queue_url:
                print("Warning: SQS_QUEUE_URL is not set. SQS mode will likely fail.")
                return # Exit init if no queue URL

            try:
                # Check if running in AWS Lambda environment
                is_lambda_env = os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None

                # Configure timeout settings for boto3 - more aggressive timeouts to prevent hanging
                boto3_config = Config(
                    region_name=settings.AWS_REGION,
                    retries={'max_attempts': 2, 'mode': 'adaptive'},  # Reduced retries
                    read_timeout=15,  # Reduced from 30 to 15 seconds
                    connect_timeout=5   # Reduced from 10 to 5 seconds
                )

                if is_lambda_env:
                    self.sqs = boto3.client('sqs', config=boto3_config)
                else:
                    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                        self.sqs = boto3.client(
                            'sqs',
                            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                            config=boto3_config
                        )
                    else:
                        self.sqs = boto3.client('sqs', config=boto3_config)

                # Basic check if client was created
                if self.sqs is None:
                     raise Exception("SQS client initialization failed after conditional check.")
                
                self.sqs_available = True
                print(f"SQS client initialized successfully. Queue URL: {self.queue_url}")

            except NoCredentialsError:
                 print("AWS Credentials Error: Could not find AWS credentials. Ensure your environment is configured correctly (e.g., IAM role in Lambda, ~/.aws/credentials locally).")
                 self.sqs = None
                 self.sqs_available = False
            except ClientError as ce:
                 # Catch potential client errors during init (e.g., invalid region)
                 print(f"AWS Client Error during initialization: {ce}")
                 self.sqs = None
                 self.sqs_available = False
            except Exception as e:
                print(f"Unexpected error during AWS client initialization: {e}")
                self.sqs = None # Ensure sqs is None if setup fails
                self.sqs_available = False


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

        if purpose == "test":
            print("Skipping message sending for test purpose.")
            return {"status": "skipped_for_test"}

        message_body = {
            'user_id': str(user_id),
            'message_id': str(message_id) if message_id else f"msg_{uuid.uuid4().hex[:8]}",
            'purpose': purpose,
            'conversation_id': str(conversation_id),
            'message_content': message_content,
            'timestamp': time.time()
        }

        if self.local_mode:
            if not self.local_brain_url: # Check the value from settings
                 print("Error: Local mode is enabled but LOCAL_BRAIN_ENDPOINT_URL is not set in settings.")
                 return {"error": "Local endpoint URL not configured"}
            try:
                # Configure timeout for httpx client - more aggressive timeout
                timeout = httpx.Timeout(15.0)  # Reduced from 30 to 15 seconds
                async with httpx.AsyncClient(timeout=timeout) as client:
                    target_url = f"{self.local_brain_url.rstrip('/')}/query"
                    print(f"Sending HTTP request to: {target_url}")
                    response = await client.post(target_url, json=message_body)
                    response.raise_for_status()
                    print(f"HTTP request completed successfully. Status: {response.status_code}")
                    try:
                         return response.json()
                    except json.JSONDecodeError:
                         return {"status_code": response.status_code, "content": response.text}
            except httpx.TimeoutException as exc:
                target_url = f"{self.local_brain_url.rstrip('/')}/query"
                print(f"Timeout error sending message to {target_url}. Details: {repr(exc)}")
                return {"error": f"Timeout connecting to local endpoint: {exc}"}
            except httpx.RequestError as exc:
                target_url = f"{self.local_brain_url.rstrip('/')}/query" # Ensure target_url is defined for error message
                print(f"Caught httpx.RequestError sending message to {target_url}. Type: {type(exc)}, Details: {repr(exc)}")
                return {"error": f"Failed to connect/read from local endpoint: {exc}"}
            except httpx.HTTPStatusError as exc:
                 print(f"Local endpoint returned error status {exc.response.status_code}. Response: {exc.response.text}")
                 return {"error": f"Local endpoint error: {exc.response.status_code}", "details": exc.response.text}
            except json.JSONDecodeError as exc:
                 print(f"Failed to decode JSON response from {target_url}. Status: {response.status_code}, Response: {response.text}. Error: {exc}")
                 return {"error": "Invalid JSON response from local endpoint", "details": response.text}
            except Exception as e:
                 print(f"An unexpected error occurred during local endpoint call. Type: {type(e)}, Details: {repr(e)}")
                 return {"error": f"Unexpected error: {str(e)}"}
        else: # SQS Mode
            if not self.sqs_available or not self.queue_url or not self.sqs:
                print("SQS Error: Queue URL not configured or SQS client failed initialization. Cannot send message.")
                return {"error": "SQS not configured or unavailable"}

            try:
                print(f"Attempting to send SQS message to queue: {self.queue_url}")
                print(f"Message body size: {len(json.dumps(message_body))} bytes")
                
                # Add a hard timeout using asyncio to prevent indefinite hanging
                # Wrap the synchronous SQS call in an executor with timeout
                loop = asyncio.get_event_loop()
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
                
                def send_sqs_message():
                    return self.sqs.send_message(
                        QueueUrl=self.queue_url,
                        MessageBody=json.dumps(message_body),
                        MessageAttributes={
                            'MessageType': {
                                'DataType': 'String',
                                'StringValue': 'UserMessage'
                            }
                        }
                    )
                
                # Use asyncio.wait_for to add an additional timeout layer
                response = await asyncio.wait_for(
                    loop.run_in_executor(executor, send_sqs_message),
                    timeout=20.0  # 20 second total timeout
                )
                
                print(f"SQS message sent successfully. Response: {response}")
                return response
                
            except asyncio.TimeoutError:
                print(f"SQS send operation timed out after 20 seconds. Queue: {self.queue_url}")
                return {"error": "SQS send operation timed out"}
            except ClientError as e: # Catch ClientError specifically
                error_code = e.response.get('Error', {}).get('Code')
                error_message = e.response.get('Error', {}).get('Message')
                print(f"SQS ClientError: Code={error_code}, Message={error_message}. Failed sending message to {self.queue_url}.")
                return {"error": f"SQS send failed: {error_code} - {error_message}"}
            except Exception as e:
                # Catch other potential exceptions
                error_type = type(e).__name__
                print(f"SQS Error (Non-ClientError): Failed sending message to {self.queue_url}. Error Type: {error_type}, Details: {e}")
                return {"error": f"SQS send failed: {str(e)}"}

    async def send_user_persona_generation_task(self, user_id: int):
        """
        Sends a task to generate a user persona.
        """
        task_body = {
            "task_type": "USER_PERSONA_GENERATION",
            "user_id": user_id
        }
        return await self.send_batch_task(task_body)

    async def send_batch_task(self, task_body: dict):
        """
        Sends a batch task message to the SQS queue or a local HTTP endpoint.
        This is an async version suitable for FastAPI endpoints.
        """
        # import ipdb; ipdb.set_trace()
        if self.local_mode:
            if not self.local_brain_url:
                print("Error: Local mode is enabled but LOCAL_BRAIN_ENDPOINT_URL is not set.")
                return {"error": "Local endpoint URL not configured"}
            try:
                # The local brain should have a generic task endpoint like /tasks
                target_url = f"{self.local_brain_url.rstrip('/')}/tasks"
                print(f"Sending batch task via HTTP to: {target_url}")
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(target_url, json=task_body)
                    response.raise_for_status()
                    print(f"HTTP request for batch task completed. Status: {response.status_code}")
                    try:
                        return response.json()
                    except json.JSONDecodeError:
                        return {"status_code": response.status_code, "content": response.text}
            except httpx.RequestError as exc:
                print(f"Error sending batch task to local brain: {exc}")
                return {"error": f"Failed to connect to local brain: {exc}"}
            except httpx.HTTPStatusError as exc:
                print(f"Local brain returned error for batch task: {exc.response.status_code}")
                return {"error": "Local brain task endpoint error", "details": exc.response.text}
        else: # SQS Mode
            if not self.sqs_available or not self.queue_url or not self.sqs:
                print("SQS Error: Queue not configured or unavailable.")
                return {"error": "SQS not configured or unavailable"}
            try:
                print(f"Attempting to send batch task SQS message to queue: {self.queue_url}")
                
                # SQS sending logic is synchronous in boto3, run in executor
                loop = asyncio.get_event_loop()
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

                def send_sqs_message_sync():
                    return self.sqs.send_message(
                        QueueUrl=self.queue_url,
                        MessageBody=json.dumps(task_body)
                    )

                response = await asyncio.wait_for(
                    loop.run_in_executor(executor, send_sqs_message_sync),
                    timeout=20.0
                )
                print(f"SQS batch task message sent successfully. Response: {response}")
                return response
            except asyncio.TimeoutError:
                print("SQS send operation for batch task timed out.")
                return {"error": "SQS send operation timed out"}
            except ClientError as e:
                print(f"SQS ClientError sending batch task: {e}")
                return {"error": f"SQS send failed: {e.response.get('Error', {}).get('Code')}"}


# Create singleton instance
queue_service = QueueService()

def get_queue_service() -> QueueService:
    """FastAPI dependency provider for the queue service."""
    return queue_service