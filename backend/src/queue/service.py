import os
import json
import boto3
import time
import uuid
import httpx  # Import httpx
from botocore.exceptions import NoCredentialsError, ClientError # Import exceptions
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

        if self.local_mode:
            print(f"Using local mode (APP_ENV={settings.APP_ENV}, LOCAL_BRAIN_ENDPOINT_URL is set). Sending messages to: {self.local_brain_url}")
        else: # SQS Mode
            if not self.queue_url:
                print("Warning: SQS_QUEUE_URL is not set. SQS mode will likely fail.")
                return # Exit init if no queue URL

            try:
                # Check if running in AWS Lambda environment
                is_lambda_env = os.getenv('AWS_LAMBDA_FUNCTION_NAME') is not None

                if is_lambda_env:
                    self.sqs = boto3.client('sqs', region_name=settings.AWS_REGION)
                else:
                    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                        self.sqs = boto3.client(
                            'sqs',
                            region_name=settings.AWS_REGION,
                            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
                        )
                    else:
                        self.sqs = boto3.client('sqs', region_name=settings.AWS_REGION)

                # Basic check if client was created
                if self.sqs is None:
                     raise Exception("SQS client initialization failed after conditional check.")

            except NoCredentialsError:
                 print("AWS Credentials Error: Could not find AWS credentials. Ensure your environment is configured correctly (e.g., IAM role in Lambda, ~/.aws/credentials locally).")
                 self.sqs = None
            except ClientError as ce:
                 # Catch potential client errors during init (e.g., invalid region)
                 print(f"AWS Client Error during initialization: {ce}")
                 self.sqs = None
            except Exception as e:
                print(f"Unexpected error during AWS client initialization: {e}")
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
            'conversation_id': str(conversation_id),
            'message_content': message_content,
            'timestamp': time.time()
        }

        if self.local_mode:
            if not self.local_brain_url: # Check the value from settings
                 print("Error: Local mode is enabled but LOCAL_BRAIN_ENDPOINT_URL is not set in settings.")
                 return {"error": "Local endpoint URL not configured"}
            try:
                async with httpx.AsyncClient() as client:
                    target_url = f"{self.local_brain_url.rstrip('/')}/query"
                    response = await client.post(target_url, json=message_body)
                    response.raise_for_status()
                    try:
                         return response.json()
                    except json.JSONDecodeError:
                         return {"status_code": response.status_code, "content": response.text}
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
            if not self.queue_url or not self.sqs:
                print("SQS Error: Queue URL not configured or SQS client failed initialization. Cannot send message.")
                return {"error": "SQS not configured or unavailable"}

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
                return response
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

# Create singleton instance
queue_service = QueueService() 