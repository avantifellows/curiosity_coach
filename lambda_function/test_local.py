#!/usr/bin/env python3
"""
Test script for local Lambda function testing with LocalStack.
This script:
1. Creates a local SQS queue
2. Deploys the Lambda function to LocalStack
3. Sets up an event source mapping (SQS -> Lambda)
4. Sends test messages to the queue
5. Monitors Lambda execution
"""

import os
import json
import time
import uuid
import boto3
import subprocess
import argparse
from pathlib import Path

# Constants
DEFAULT_QUEUE_NAME = "local-test-queue"
DEFAULT_LAMBDA_NAME = "CuriosityCoach"
DEFAULT_REGION = "us-east-1"
LOCALSTACK_ENDPOINT = "http://localhost:4566"

def create_lambda_zip():
    """Create a Lambda deployment package"""
    print("Creating Lambda deployment package...")
    # Create a temporary directory for packaging
    package_dir = Path("./package")
    package_dir.mkdir(exist_ok=True)
    
    # Install dependencies
    print("Installing dependencies...")
    subprocess.run(["uv", "pip", "install", "--no-cache", "-t", str(package_dir), "--system", "."], check=True)
    
    # Copy Lambda code
    lambda_file = Path("lambda_function.py")
    init_file = Path("__init__.py")
    subprocess.run(["cp", str(lambda_file), str(package_dir)], check=True)
    subprocess.run(["cp", str(init_file), str(package_dir)], check=True)
    
    # Create ZIP file
    zip_path = Path("./lambda_deployment_package.zip")
    if zip_path.exists():
        zip_path.unlink()
    
    os.chdir(package_dir)
    subprocess.run(["zip", "-r", "../lambda_deployment_package.zip", "."], check=True)
    os.chdir("..")
    
    return zip_path.absolute()

def setup_aws_resources(queue_name, lambda_name, region):
    """Set up necessary AWS resources on LocalStack"""
    print(f"Setting up AWS resources on LocalStack ({LOCALSTACK_ENDPOINT})...")
    
    # Configure boto3 client for LocalStack
    session = boto3.Session(
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name=region
    )
    
    # Create SQS client and Lambda client
    sqs = session.client('sqs', endpoint_url=LOCALSTACK_ENDPOINT)
    lambda_client = session.client('lambda', endpoint_url=LOCALSTACK_ENDPOINT)
    
    # Create SQS queue
    print(f"Creating SQS queue: {queue_name}")
    queue_response = sqs.create_queue(QueueName=queue_name)
    queue_url = queue_response['QueueUrl']
    
    # Get queue ARN
    queue_attributes = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['QueueArn']
    )
    queue_arn = queue_attributes['Attributes']['QueueArn']
    print(f"Queue ARN: {queue_arn}")
    
    # Create IAM role for Lambda (note: not fully implemented in LocalStack)
    # For LocalStack, we can use a dummy ARN
    role_arn = f"arn:aws:iam::123456789012:role/lambda-role"
    
    # Create Lambda function
    zip_path = create_lambda_zip()
    
    with open(zip_path, 'rb') as zip_file:
        print(f"Creating Lambda function: {lambda_name}")
        try:
            lambda_client.delete_function(FunctionName=lambda_name)
            print(f"Deleted existing Lambda function: {lambda_name}")
        except Exception:
            # Function doesn't exist, which is fine
            pass
        
        lambda_response = lambda_client.create_function(
            FunctionName=lambda_name,
            Runtime='python3.9',
            Role=role_arn,
            Handler='lambda_function.lambda_handler',
            Code={'ZipFile': zip_file.read()},
            Timeout=30,
            MemorySize=256
        )
    
    lambda_arn = lambda_response['FunctionArn']
    print(f"Lambda ARN: {lambda_arn}")
    
    # Create event source mapping (SQS -> Lambda)
    print("Creating event source mapping...")
    try:
        mapping_response = lambda_client.create_event_source_mapping(
            EventSourceArn=queue_arn,
            FunctionName=lambda_name,
            BatchSize=1
        )
        print(f"Event source mapping created: {mapping_response['UUID']}")
    except lambda_client.exceptions.ResourceConflictException:
        print("Event source mapping already exists")
    
    return {
        'queue_url': queue_url,
        'queue_arn': queue_arn,
        'lambda_arn': lambda_arn
    }

def send_test_messages(queue_url, num_messages, region):
    """Send test messages to the SQS queue"""
    # Configure boto3 client for LocalStack
    session = boto3.Session(
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name=region
    )
    
    sqs = session.client('sqs', endpoint_url=LOCALSTACK_ENDPOINT)
    
    print(f"Sending {num_messages} test messages to queue: {queue_url}")
    
    for i in range(num_messages):
        # Create a sample message that matches the expected format
        message_id = f"test_message_{uuid.uuid4()}"
        user_id = f"test_user_{uuid.uuid4()}"
        conversation_id = f"test_conversation_{uuid.uuid4()}"
        
        # Alternate between different purposes for testing
        purposes = ["chat", "test_generation", "doubt_solver"]
        purpose = purposes[i % len(purposes)]
        
        message = {
            "user_id": user_id,
            "message_id": message_id,
            "purpose": purpose,
            "conversation_id": conversation_id
        }
        
        # Send message to SQS
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message)
        )
        
        print(f"Message {i+1} sent with ID: {response['MessageId']}")
        print(f"  Purpose: {purpose}")
        print(f"  Message ID: {message_id}")
        print(f"  User ID: {user_id}")
        
        # Small delay between messages to make logs easier to follow
        time.sleep(0.5)

def monitor_lambda_logs(lambda_name, duration, region):
    """Monitor CloudWatch logs for the Lambda function (simplified for LocalStack)"""
    print(f"Monitoring Lambda execution for {duration} seconds...")
    
    # For LocalStack, we can just watch the container logs
    # In a real AWS environment, we would use CloudWatch logs
    
    print("Check the LocalStack container logs to see Lambda execution details:")
    print("  docker logs -f localstack")
    
    # Wait for the specified duration
    for i in range(duration):
        print(f"Waiting... {i+1}/{duration} seconds elapsed", end="\r")
        time.sleep(1)
    print("\nMonitoring complete.")

def parse_args():
    """Parse command-line arguments"""
    parser = argparse.ArgumentParser(description="Test Lambda function with LocalStack")
    parser.add_argument("--queue", default=DEFAULT_QUEUE_NAME, help="SQS queue name")
    parser.add_argument("--lambda-name", default=DEFAULT_LAMBDA_NAME, help="Lambda function name")
    parser.add_argument("--region", default=DEFAULT_REGION, help="AWS region to use")
    parser.add_argument("--messages", type=int, default=3, help="Number of test messages to send")
    parser.add_argument("--monitor", type=int, default=10, help="Duration in seconds to monitor logs")
    return parser.parse_args()

def main():
    """Main function"""
    # Parse command-line arguments
    args = parse_args()
    
    # Check if LocalStack is running
    try:
        subprocess.run(
            ["curl", "-s", f"{LOCALSTACK_ENDPOINT}/health"], 
            check=True, 
            stdout=subprocess.PIPE
        )
    except subprocess.CalledProcessError:
        print("LocalStack is not running. Please start it with: docker-compose up -d")
        return
    
    # Set up AWS resources
    resources = setup_aws_resources(args.queue, args.lambda_name, args.region)
    
    # Send test messages
    send_test_messages(resources['queue_url'], args.messages, args.region)
    
    # Monitor Lambda execution
    monitor_lambda_logs(args.lambda_name, args.monitor, args.region)
    
    print("\nTest complete!")
    print("Check the Lambda function logs for details.")
    print(f"Queue URL: {resources['queue_url']}")
    print(f"Lambda ARN: {resources['lambda_arn']}")

if __name__ == "__main__":
    main() 