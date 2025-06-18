import os
import json
import logging
from urllib import request, error

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    """
    Handles the Lambda invocation to trigger a POST request.
    """
    backend_base_url = os.environ.get('BACKEND_BASE_URL')
    backend_route = os.environ.get('BACKEND_ROUTE')

    if not backend_base_url or not backend_route:
        logger.error("FATAL: Environment variables BACKEND_BASE_URL and BACKEND_ROUTE must be set.")
        return {
            'statusCode': 500,
            'body': json.dumps('Internal server error: Missing required environment variables.')
        }
        
    # Ensure the base URL doesn't end with a slash and the route starts with one
    if backend_base_url.endswith('/'):
        backend_base_url = backend_base_url[:-1]
    if not backend_route.startswith('/'):
        backend_route = '/' + backend_route

    endpoint_url = f"{backend_base_url}{backend_route}"
    
    logger.info(f"Triggering POST request to: {endpoint_url}")

    # Prepare the request. We are sending an empty JSON body.
    data = json.dumps({}).encode('utf-8')
    req = request.Request(endpoint_url, data=data, method='POST')
    req.add_header('Content-Type', 'application/json')

    try:
        with request.urlopen(req) as response:
            status_code = response.getcode()
            response_body = response.read().decode('utf-8')
            logger.info(f"Response Status: {status_code}")
            logger.info(f"Response Body: {response_body}")

            return {
                'statusCode': status_code,
                'body': response_body
            }
            
    except error.HTTPError as e:
        # This catches non-2xx responses
        logger.error(f"HTTP Error received from endpoint.")
        logger.error(f"Status: {e.code}")
        logger.error(f"Body: {e.read().decode('utf-8')}")
        return {
            'statusCode': e.code,
            'body': json.dumps(f"Failed to trigger endpoint. HTTP Status: {e.code}")
        }
        
    except error.URLError as e:
        # This catches other network errors (e.g., DNS failure)
        logger.error(f"URL Error: {e.reason}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Failed to reach endpoint. Reason: {e.reason}")
        }
        
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"An unexpected error occurred: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps('An unexpected internal server error occurred.')
        } 