import json
import logging
import os
import sys
import asyncio

# Add Mangum for FastAPI integration
from mangum import Mangum

# Since Dockerfile copies contents of src/ to LAMBDA_TASK_ROOT,
# main.py and lambda_function.py are in the same directory.
# Add the src directory's parent (Brain) to the path for local execution
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

# Import the FastAPI app and the dequeue function
from src.main import (
    app, dequeue, MessagePayload, process_memory_generation_batch,
    process_class_analysis_task, process_student_analysis_task,
)
from src.core.user_persona_generator import generate_persona_for_user
from pydantic import ValidationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create the Mangum handler for the FastAPI app
asgi_handler = Mangum(app)

def lambda_handler(event, context):
    """
    AWS Lambda handler function.

    - If invoked by SQS, processes messages using the dequeue function.
    - If invoked by API Gateway/Function URL (HTTP), handles the request using the FastAPI app via Mangum.
    """
    logger.info(f"Received event: {json.dumps(event)}")

    # Check if the event is likely from SQS
    # SQS events typically have a 'Records' list with 'eventSource': 'aws:sqs'
    if 'Records' in event and event['Records'] and event['Records'][0].get('eventSource') == 'aws:sqs':
        logger.info("Detected SQS event. Processing messages...")
        processed_messages = 0
        failed_messages = 0

        for record in event['Records']:
            try:
                message_body_str = record.get('body')
                if not message_body_str:
                    logger.warning(f"Record {record.get('messageId')} has no body. Skipping.")
                    failed_messages += 1
                    continue

                try:
                    message_body = json.loads(message_body_str)
                except json.JSONDecodeError:
                    logger.info(f"Message body for {record.get('messageId')} is not JSON. Passing as string.")
                    # If it's not JSON, it can't be parsed into MessagePayload, skip
                    logger.warning(f"Skipping non-JSON message body for ID {record.get('messageId')}")
                    failed_messages += 1
                    continue # Skip to the next record

                # --- Task-based routing ---
                task_type = message_body.get("task_type")

                if task_type == "GENERATE_MEMORY_BATCH":
                    conversation_ids = message_body.get("conversation_ids", [])
                    if conversation_ids:
                        logger.info(f"Detected GENERATE_MEMORY_BATCH task for {len(conversation_ids)} conversations.")
                        asyncio.run(process_memory_generation_batch(conversation_ids))
                        processed_messages += 1
                    else:
                        logger.warning("GENERATE_MEMORY_BATCH task received with no conversation_ids.")
                        failed_messages += 1
                    continue # Move to the next record
                
                elif task_type == "USER_PERSONA_GENERATION":
                    user_id = message_body.get("user_id")
                    if user_id:
                        logger.info(f"Detected USER_PERSONA_GENERATION task for user_id: {user_id}.")
                        asyncio.run(generate_persona_for_user(user_id))
                        processed_messages += 1
                    else:
                        logger.warning("USER_PERSONA_GENERATION task received with no user_id.")
                        failed_messages += 1
                    continue

                elif task_type == "CLASS_ANALYSIS":
                    job_id = message_body.get("job_id")
                    school = message_body.get("school")
                    grade = message_body.get("grade")
                    section = message_body.get("section")
                    last_message_hash = message_body.get("last_message_hash")
                    if job_id and school and grade is not None:
                        logger.info(f"Detected CLASS_ANALYSIS task for job_id: {job_id}")
                        asyncio.run(process_class_analysis_task(job_id, school, grade, section, last_message_hash))
                        processed_messages += 1
                    else:
                        logger.warning("CLASS_ANALYSIS task received with missing job_id, school, or grade.")
                        failed_messages += 1
                    continue

                elif task_type == "STUDENT_ANALYSIS":
                    job_id = message_body.get("job_id")
                    student_id = message_body.get("student_id")
                    last_message_hash = message_body.get("last_message_hash")
                    if job_id and student_id:
                        logger.info(f"Detected STUDENT_ANALYSIS task for job_id: {job_id}")
                        asyncio.run(process_student_analysis_task(job_id, student_id, last_message_hash))
                        processed_messages += 1
                    else:
                        logger.warning("STUDENT_ANALYSIS task received with missing job_id or student_id.")
                        failed_messages += 1
                    continue

                # --- Regular message processing ---
                # Parse the dictionary into the Pydantic model
                try:
                    parsed_message = MessagePayload(**message_body)
                except ValidationError as ve:
                    logger.error(f"Validation error parsing message body for ID {record.get('messageId')}: {ve}", exc_info=True)
                    failed_messages += 1
                    continue # Skip to the next record
                except Exception as parse_exc: # Catch other potential parsing errors
                    logger.error(f"Unexpected error parsing message body for ID {record.get('messageId')}: {parse_exc}", exc_info=True)
                    failed_messages += 1
                    continue # Skip to the next record

                logger.info(f"Processing message ID: {record.get('messageId')}")
                # Pass the parsed Pydantic object to dequeue
                # Use asyncio.run() to call the async dequeue function
                asyncio.run(dequeue(parsed_message))
                processed_messages += 1

            except Exception as e:
                logger.error(f"Error processing SQS message ID {record.get('messageId')}: {e}", exc_info=True)
                failed_messages += 1

        logger.info(f"SQS processing complete. Processed: {processed_messages}, Failed: {failed_messages}.")

        # Return structure for SQS doesn't necessarily need statusCode/body unless
        # specifically configured for Lambda failure destinations or similar.
        # A simple success/failure log might suffice, or return failed message IDs if needed.
        # For now, let's keep the previous return style for consistency.
        if failed_messages == 0:
            # Note: SQS triggers typically don't use the return value unless there's an error.
            return {'statusCode': 200, 'body': json.dumps(f'Successfully processed {processed_messages} SQS messages.')}
        else:
            # Raise an exception or return a specific structure if you want SQS to retry failed messages.
            # Returning a 500 might not automatically trigger retries depending on config.
            # For simplicity, we log errors and report partial success/failure here.
             return {'statusCode': 500, 'body': json.dumps(f'Processed {processed_messages} SQS messages, failed {failed_messages}.')}

    # Otherwise, assume it's an API Gateway/Function URL event and handle with Mangum
    else:
        logger.info("Detected non-SQS event (likely HTTP). Handling with FastAPI/Mangum...")
        
        # Ensure an event loop is available for the current thread for Mangum.
        # This is necessary for Python 3.10+ where asyncio.get_event_loop()
        # raises a RuntimeError if no loop is set and one isn't automatically created.
        # Mangum's LifespanCycle needs an active event loop.
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                # If the existing loop is closed (e.g., from a previous invocation in a reused environment),
                # create and set a new one.
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            # If no event loop exists at all for this thread, create and set one.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Now, call the Mangum handler. It will use the current event loop.
        return asgi_handler(event, context)

# Example usage section remains for local testing of SQS path,
# but won't test the FastAPI path directly without simulating an API Gateway event.
if __name__ == '__main__':
    # Simulate an SQS event
    test_event_sqs = {
        "Records": [
            {
                "messageId": "19dd0b57-b21e-4ac1-bd88-01bbb068cb78",
                "receiptHandle": "MessageReceiptHandle",
                "body": "{\"key1\": \"value1\", \"key2\": \"value2\"}",
                "attributes": { "ApproximateReceiveCount": "1", "SentTimestamp": "1523232000000", "SenderId": "AROAIASKVA53I22X3PE7S:test", "ApproximateFirstReceiveTimestamp": "1523232000001" },
                "messageAttributes": {},
                "md5OfBody": "{{{md5_of_body}}}",
                "eventSource": "aws:sqs",
                "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:MyQueue",
                "awsRegion": "us-east-1"
            },
            {
                 "messageId": "20dd0b57-b21e-4ac1-bd88-01bbb068cb79",
                 "receiptHandle": "MessageReceiptHandle2",
                 "body": "This is a plain text message.",
                 "attributes": { "ApproximateReceiveCount": "1", "SentTimestamp": "1523232000000", "SenderId": "AROAIASKVA53I22X3PE7S:test", "ApproximateFirstReceiveTimestamp": "1523232000001" },
                 "messageAttributes": {},
                 "md5OfBody": "{{{md5_of_body_2}}}",
                 "eventSource": "aws:sqs",
                 "eventSourceARN": "arn:aws:sqs:us-east-1:123456789012:MyQueue",
                 "awsRegion": "us-east-1"
            }
        ]
    }
    print("Testing SQS event:")
    result_sqs = lambda_handler(test_event_sqs, None) # Changed back to direct call
    print(f"SQS Result: {result_sqs}")

    # To test the HTTP path locally, you'd need to simulate an API Gateway event payload.
    # Example (very basic, real payloads are more complex):
    test_event_http = {
        "version": "2.0",
        "routeKey": "$default",
        "rawPath": "/",
        "rawQueryString": "",
        "headers": { "accept": "text/html,...", "host": "lambda-url.aws...", "user-agent": "curl/7.79.1", "x-amzn-trace-id": "Root=...", "x-forwarded-for": "1.2.3.4", "x-forwarded-proto": "https" },
        "requestContext": {
            "accountId": "anonymous", "apiId": "...", "domainName": "lambda-url.aws...", "domainPrefix": "...",
            "http": { "method": "GET", "path": "/", "protocol": "HTTP/1.1", "sourceIp": "1.2.3.4", "userAgent": "curl/7.79.1" },
            "requestId": "...", "routeKey": "$default", "stage": "$default", "time": "...", "timeEpoch": 1678886400000
        },
        "isBase64Encoded": False
    }
    # print("Testing HTTP GET event (requires mangum and FastAPI setup):")
    # result_http = lambda_handler(test_event_http, None) # This would call asgi_handler
    # print(f"HTTP Result: {result_http}")