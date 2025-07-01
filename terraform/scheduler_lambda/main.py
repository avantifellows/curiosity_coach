import os
import json
import logging
from urllib import request, error

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Handles the Lambda invocation to trigger a POST request based on the event payload.
    """
    backend_base_url = os.environ.get('BACKEND_BASE_URL')
    task_type = event.get('task')

    if not backend_base_url:
        logger.error("FATAL: Environment variable BACKEND_BASE_URL must be set.")
        return {'statusCode': 500, 'body': json.dumps('Internal server error: Missing required environment variables.')}

    if not task_type:
        logger.error("FATAL: 'task' not found in invocation event.")
        return {'statusCode': 400, 'body': json.dumps("Bad request: 'task' not specified in event.")}

    # Ensure the base URL doesn't end with a slash
    if backend_base_url.endswith('/'):
        backend_base_url = backend_base_url[:-1]

    # Determine endpoint and query params based on task type
    if task_type == "memory_generation":
        backend_route = "/api/tasks/trigger-memory-generation"
        query_params = "clamp=5"
        endpoint_url = f"{backend_base_url}{backend_route}?{query_params}"
    elif task_type == "persona_generation":
        backend_route = "/api/tasks/trigger-user-persona-generation"
        query_params = "clamp=5"
        endpoint_url = f"{backend_base_url}{backend_route}?{query_params}"
    else:
        logger.error(f"Unknown task type received: {task_type}")
        return {'statusCode': 400, 'body': json.dumps(f"Bad request: Unknown task type '{task_type}'.")}

    logger.info(f"Triggering POST request for task '{task_type}' to: {endpoint_url}")

    # Prepare the request. An empty JSON body is suitable for both endpoints.
    data = json.dumps({}).encode('utf-8')
    req = request.Request(endpoint_url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')

    try:
        with request.urlopen(req) as response:
            status_code = response.getcode()
            response_body = response.read().decode('utf-8')
            logger.info(f"Response Status: {status_code}")
            logger.info(f"Response Body: {response_body}")
            return {'statusCode': status_code, 'body': response_body}
            
    except error.HTTPError as e:
        logger.error(f"HTTP Error received from endpoint.")
        logger.error(f"Status: {e.code}")
        logger.error(f"Body: {e.read().decode('utf-8')}")
        return {'statusCode': e.code, 'body': json.dumps(f"Failed to trigger endpoint. HTTP Status: {e.code}")}
        
    except error.URLError as e:
        logger.error(f"URL Error: {e.reason}")
        return {'statusCode': 500, 'body': json.dumps(f"Failed to reach endpoint. Reason: {e.reason}")}
        
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps('An unexpected internal server error occurred.')} 