import os
import json
import boto3
from dotenv import load_dotenv
import time

# Load environment variables
env_file = '.env.local' if os.getenv('FLASK_ENV') == 'development' else '.env'
load_dotenv(env_file)

# Check if we should use mock mode (for local development)
MOCK_MODE = os.getenv('FLASK_ENV') == 'development' or os.getenv('AWS_ACCESS_KEY_ID') == 'dummy'

class QueueService:
    """Service for interacting with SQS queue, with fallback for local development"""
    
    def __init__(self):
        """Initialize SQS client and queue URL, with fallback for local development"""
        self.queue_url = os.getenv('SQS_QUEUE_URL')
        self.mock_mode = MOCK_MODE
        
        if not self.mock_mode:
            try:
                self.sqs = boto3.client(
                    'sqs',
                    region_name=os.getenv('AWS_REGION', 'us-west-2'),
                    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
                    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
                )
                # Test the connection
                self.sqs.list_queues()
            except Exception as e:
                print(f"AWS SQS connection failed: {e}")
                print("Falling back to mock mode")
                self.mock_mode = True
        
        if self.mock_mode:
            print("Using mock SQS mode for local development")
            self.mock_messages = []
            
    def send_message(self, user_id, message_content, message_id=None):
        """
        Send a message to the SQS queue (or mock storage in local development)
        
        Args:
            user_id (int): ID of the user sending the message
            message_content (str): Content of the message
            message_id (int, optional): ID of the message in the database
            
        Returns:
            dict: Response from SQS or mock response
        """
        message_body = {
            'user_id': user_id,
            'content': message_content,
            'message_id': message_id,
            'timestamp': time.time()
        }
        
        if self.mock_mode:
            # In mock mode, just store the message locally
            self.mock_messages.append(message_body)
            print(f"MOCK SQS: Message sent - {json.dumps(message_body)}")
            return {
                'MessageId': f'mock-{len(self.mock_messages)}',
                'MD5OfMessageBody': 'mock-md5'
            }
            
        if not self.queue_url:
            print("SQS Queue URL not configured. Message not sent to queue.")
            return None
            
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
        except Exception as e:
            print(f"Error sending message to SQS: {e}")
            # Fall back to mock mode for this message
            self.mock_messages.append(message_body)
            print(f"MOCK SQS (fallback): Message sent - {json.dumps(message_body)}")
            return {
                'MessageId': f'mock-fallback-{len(self.mock_messages)}',
                'MD5OfMessageBody': 'mock-md5'
            }
            
    def receive_message(self):
        """
        Receive a message from the SQS queue (or mock storage in local development)
        
        Returns:
            dict: Message from the queue or None if no message or error
        """
        if self.mock_mode:
            # In mock mode, return the oldest message if any exist
            if self.mock_messages:
                message = self.mock_messages.pop(0)
                print(f"MOCK SQS: Message received - {json.dumps(message)}")
                return message
            return None
            
        if not self.queue_url:
            print("SQS Queue URL not configured. Cannot receive messages.")
            return None
            
        try:
            response = self.sqs.receive_message(
                QueueUrl=self.queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=1,
                MessageAttributeNames=['All']
            )
            
            if 'Messages' in response:
                message = response['Messages'][0]
                receipt_handle = message['ReceiptHandle']
                
                # Delete the message from the queue
                self.sqs.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=receipt_handle
                )
                
                # Parse the message body
                message_body = json.loads(message['Body'])
                return message_body
            
            return None
        except Exception as e:
            print(f"Error receiving message from SQS: {e}")
            return None

# Create singleton instance
queue_service = QueueService() 