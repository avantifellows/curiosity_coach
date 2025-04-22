# Curiosity Coach Lambda Function

This Lambda function processes messages from an SQS queue, calls an LLM API based on the message purpose, and saves the responses to a database.

## Structure

The SQS message structure expected by this Lambda function is:

```json
{
  "user_id": "user123",
  "message_id": "db_message_789",
  "purpose": "test_generation",
  "conversation_id": "conv_456"
}
```

## Components

- `lambda_function.py`: Main Lambda handler function
- `requirements.txt`: Dependencies required for the Lambda function
- `test_lambda_function.py`: Unit tests for the Lambda function
- `Dockerfile`: Docker configuration for building the Lambda package
- `docker-deploy.sh`: Deploy the Lambda using Docker (recommended method)
- `zip-deploy.sh`: Deploy the Lambda as a zip archive directly with uv

## Prerequisites

- AWS Account
- AWS CLI configured
- Python 3.9+
- Docker (for Docker-based deployment)
- uv (for zip-based deployment - will be auto-installed if not available)

## Environment Setup

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your specific settings:
   ```
   # AWS Configuration
   AWS_REGION=ap-south-1                  # Your AWS region
   AWS_ACCOUNT_ID=123456789012           # Your AWS account ID
   LAMBDA_NAME=CuriosityCoach            # Name of the Lambda function
   LAMBDA_TIMEOUT=30                     # Timeout in seconds
   LAMBDA_MEMORY=256                     # Memory allocation in MB
   
   # Lambda IAM Role
   LAMBDA_ROLE_NAME=lambda-sqs-role      # Name of the IAM role for Lambda
   
   # SQS Configuration (optional)
   SQS_QUEUE_NAME=curiosity-coach-queue  # SQS queue to attach as trigger
   SQS_BATCH_SIZE=10                     # Number of messages to process in batch
   ```

## Deployment

### Step 1: Set Up IAM Role

Before deploying the Lambda function, you need to create an IAM role with the proper permissions and trust relationship:

```bash
# Make the script executable
chmod +x create-iam-role.sh

# Run the IAM role creation script
./create-iam-role.sh
```

This script will:
1. Create the IAM role if it doesn't exist or update the existing one
2. Set up the correct trust relationship to allow Lambda to assume the role
3. Attach necessary policies for Lambda to access CloudWatch Logs and SQS

### Step 2: Deploy the Lambda Function

### Option 1: Docker-Based Deployment (Recommended)

The recommended way to deploy the Lambda function is using Docker following the [official uv AWS Lambda guide](https://docs.astral.sh/uv/guides/integration/aws-lambda/):

```bash
# Make the script executable
chmod +x docker-deploy.sh

# Run the Docker-based deployment
./docker-deploy.sh
```

This approach:
1. Uses the official AWS Lambda Python base image
2. Installs dependencies with uv directly to the Lambda task root
3. Creates a proper deployment structure following AWS best practices
4. Works consistently across different operating systems

### Option 2: Zip-Based Deployment

You can also deploy as a zip archive following the AWS Lambda guide approach:

```bash
# Make the script executable
chmod +x zip-deploy.sh

# Run the zip deployment script
./zip-deploy.sh
```

This method:
1. Uses uv to install dependencies directly
2. Sets the correct platform target for AWS Lambda compatibility
3. Creates a zip archive with dependencies and function code
4. Is useful for simpler deployments or if Docker isn't available

## Local Testing with LocalStack

You can test the Lambda function locally using [LocalStack](https://localstack.cloud/), which provides a mock AWS environment running in Docker.

### Running the Local Test

1. Use the provided script to run a full test:

```bash
# Make the script executable
chmod +x run_local_test.sh

# Run the local test
./run_local_test.sh
```

This script will:
- Start LocalStack in a Docker container
- Create a mock SQS queue
- Deploy the Lambda function to LocalStack
- Send test messages to the queue
- Monitor the execution

## Implementation Notes

- The function currently uses placeholder implementations for database operations and LLM API calls
- These need to be replaced with actual implementations based on your infrastructure
- Different model parameters are used based on the message purpose

## Custom Configuration

To modify the Lambda behavior:
- Edit the model parameters in `lambda_function.py` for different purposes
- Implement the `call_llm_api()` function to use your specific LLM service
- Implement database functions to work with your database system

## Local Testing with LocalStack

You can test the Lambda function locally using [LocalStack](https://localstack.cloud/), which provides a mock AWS environment running in Docker.

### Prerequisites for Local Testing

- Docker and Docker Compose
- Python 3.9+
- uv or pip

### Running the Local Test

1. Use the provided script to run a full test:

```bash
# Make the script executable
chmod +x run_local_test.sh

# Run the local test
./run_local_test.sh
```

This script will:
- Start LocalStack in a Docker container
- Create a mock SQS queue
- Deploy the Lambda function to LocalStack
- Send test messages to the queue
- Monitor the execution

### Test Components

The local testing setup includes:

- `docker-compose.yml`: Configuration for LocalStack
- `test_local.py`: Script to test the Lambda function with LocalStack
- `mock_db.py`: A simple file-based mock database
- `lambda_function_local.py`: Modified Lambda function for local testing
- `run_local_test.sh`: Script to run the entire test workflow

### Manual Testing

You can also test individual components:

1. Start LocalStack:
```bash
docker-compose up -d
```

2. Run the local test script with custom parameters:
```bash
python test_local.py --messages 5 --monitor 20
```

3. Test the Lambda function directly without SQS:
```bash
python lambda_function_local.py
```

4. View the mock database:
```bash
cat mock_db.json
```

5. Stop LocalStack when done:
```bash
docker-compose down
``` 