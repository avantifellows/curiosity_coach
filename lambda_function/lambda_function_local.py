"""
Modified version of the Lambda function for local testing with LocalStack.
This version uses the mock_db module instead of actual AWS services.
"""

import json
import logging
import boto3
import requests
import uuid
from mock_db import get_message_from_db, save_message_to_db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def call_llm_api(content, purpose, model_params=None):
    """
    Mock function to call an LLM API. This simulates different responses based on purpose.
    """
    logger.info(f"Calling mock LLM API for purpose: {purpose}")
    
    # Simulate different responses based on purpose
    if purpose == "test_generation":
        response = {
            "response": f"Here's a test about: {content}\n\n1. Question one?\n2. Question two?\n3. Question three?",
            "purpose": purpose
        }
    elif purpose == "doubt_solver":
        response = {
            "response": f"To answer your doubt about '{content}', here's an explanation: This is a simulated explanation that would normally come from an actual LLM API. The key concept here is that we're just demonstrating how the Lambda function handles different purposes.",
            "purpose": purpose
        }
    else:  # Default chat
        response = {
            "response": f"You said: {content}\n\nThis is a simulated chat response. In a real implementation, this would come from an actual LLM API call.",
            "purpose": purpose
        }
    
    # Log the model parameters that would be used
    if model_params:
        logger.info(f"Using model parameters: {model_params}")
    
    return response

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
    logger.info("Processing local SQS event")
    logger.info(f"Event: {json.dumps(event)}")
    
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
            logger.info(f"Conversation ID: {conversation_id}")
            
            # Get full message details from database
            message_data = get_message_from_db(message_id)
            content = message_data.get('content')
            additional_params = message_data.get('additional_params', {})
            
            logger.info(f"Retrieved content: {content}")
            if additional_params:
                logger.info(f"Additional parameters: {additional_params}")
            
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
                "purpose": purpose,
                "response": llm_response['response'][:50] + "..." if len(llm_response['response']) > 50 else llm_response['response']
            })
            
    except Exception as e:
        logger.error(f"Error processing SQS message: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # In local testing, we'll just raise the exception to see what went wrong
        raise e
    
    result = {
        "statusCode": 200,
        "body": json.dumps({
            "message": "Processing complete",
            "processed_messages": responses
        })
    }
    
    logger.info(f"Returning result: {json.dumps(result)}")
    return result

# For local testing outside of Lambda
if __name__ == "__main__":
    # Create a sample event
    test_event = {
        "Records": [
            {
                "body": json.dumps({
                    "user_id": "test_user_123",
                    "message_id": "test_message_456",
                    "purpose": "chat",
                    "conversation_id": "test_conversation_789"
                })
            }
        ]
    }
    
    # Call the handler
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2)) 