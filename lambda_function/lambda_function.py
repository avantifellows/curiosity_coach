import json
import os
import boto3
import requests
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize database client (placeholder - implement with actual DB client later)
# db_client = boto3.client('dynamodb')  # Example using DynamoDB

def call_llm_api(content, purpose, model_params=None):
    """
    Dummy function to call an LLM API. This will be implemented later.
    """
    logger.info(f"Calling LLM API for purpose: {purpose}")
    # Placeholder for actual API call
    return {
        "response": f"This is a dummy response for: {content}",
        "purpose": purpose
    }

def save_message_to_db(user_id, content, is_user=False, purpose=None):
    """
    Save message to database. This is a placeholder function to be implemented.
    """
    logger.info(f"Saving message to DB for user: {user_id}")
    # Placeholder for actual DB saving logic
    return True

def get_message_from_db(message_id):
    """
    Retrieve full message details from database using message_id.
    """
    logger.info(f"Retrieving message details for ID: {message_id}")
    # Placeholder - implement actual database query
    return {
        "content": "Sample message content",
        "additional_params": {}
    }

def lambda_handler(event, context):
    """
    Lambda function to process SQS messages.
    Expected message format:
    {
        "user_id": "user123",
        "message_id": "db_message_789",
        "purpose": "test_generation",
        "conversation_id": "conv_456"
    }
    """
    logger.info("Processing SQS event")
    
    responses = []
    
    try:
        for record in event['Records']:
            # Parse the SQS message
            payload = json.loads(record['body'])
            
            # Extract message details
            user_id = payload.get('user_id')
            message_id = payload.get('message_id')
            purpose = payload.get('purpose', 'chat')  # Default to 'chat' if purpose not specified
            conversation_id = payload.get('conversation_id')
            
            logger.info(f"Processing message: {message_id} for user: {user_id} with purpose: {purpose}")
            
            # Get full message details from database
            message_data = get_message_from_db(message_id)
            content = message_data.get('content')
            additional_params = message_data.get('additional_params', {})
            
            # Get model parameters based on purpose
            model_params = {}
            if purpose == 'test_generation':
                model_params = {"temperature": 0.2}
            elif purpose == 'doubt_solver':
                model_params = {"temperature": 0.7, "max_tokens": 1000}
            
            # Call the appropriate LLM API
            llm_response = call_llm_api(content, purpose, model_params)
            
            # Save response to database
            save_message_to_db(
                user_id=user_id,
                content=llm_response['response'],
                is_user=False,
                purpose=purpose
            )
            
            responses.append({
                "message_id": message_id,
                "status": "processed",
                "purpose": purpose
            })
            
    except Exception as e:
        logger.error(f"Error processing SQS message: {str(e)}")
        # Returning the error allows the message to remain in the queue for retry
        raise e
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Processing complete",
            "processed_messages": responses
        })
    } 