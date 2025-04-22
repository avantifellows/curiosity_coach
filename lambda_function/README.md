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
- `pyproject.toml`: Project configuration and dependencies
- `test_lambda_function.py`: Unit tests for the Lambda function
- `deploy.sh`: Deployment script using uv for package management
- `.env.example`: Template for environment variables
- `.env`: Environment variables for deployment (not checked into version control)

## Prerequisites

- AWS Account
- AWS CLI configured
- Python 3.9+
- uv (will be auto-installed if not available)

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

## Local Development

### Setting Up with uv

[uv](https://github.com/astral-sh/uv) is a modern Python package installer and resolver that's significantly faster than pip.

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create a virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Running Tests

```bash
python -m unittest test_lambda_function.py
```

## Deployment

The included `deploy.sh` script handles packaging and deploying the Lambda function using uv:

```bash
# Make the script executable if needed
chmod +x deploy.sh

# Run the deployment script
./deploy.sh
```

The script will:
1. Load configuration from your `.env` file
2. Install dependencies using uv
3. Package the Lambda function and dependencies
4. Create or update the Lambda function in AWS
5. Set up an SQS trigger if specified in the `.env` file
6. Configure any specified aliases

## CI/CD Integration

For CI/CD pipelines, you can:

1. Store environment variables in your CI/CD system's secrets management
2. Create the `.env` file dynamically during the build process:
   ```yaml
   # Example GitHub Actions step
   - name: Create .env file
     run: |
       echo "AWS_REGION=${{ secrets.AWS_REGION }}" > .env
       echo "AWS_ACCOUNT_ID=${{ secrets.AWS_ACCOUNT_ID }}" >> .env
       echo "LAMBDA_NAME=${{ secrets.LAMBDA_NAME }}" >> .env
       # Add other environment variables as needed
   ```

3. Run the deployment script as part of your pipeline:
   ```yaml
   - name: Deploy Lambda function
     run: |
       cd lambda_function
       chmod +x deploy.sh
       ./deploy.sh
   ```

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