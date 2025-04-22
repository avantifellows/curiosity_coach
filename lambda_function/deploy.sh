#!/bin/bash
set -e

# Load environment variables from .env file
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE"
    export $(grep -v '^#' "$ENV_FILE" | xargs)
else
    echo "Error: $ENV_FILE not found. Please create it from .env.example"
    exit 1
fi

# Check for required environment variables
if [ -z "$AWS_REGION" ] || [ -z "$AWS_ACCOUNT_ID" ] || [ -z "$LAMBDA_NAME" ]; then
    echo "Error: Required environment variables are not set. Please check your $ENV_FILE file."
    exit 1
fi

# Create the full IAM role ARN
LAMBDA_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${LAMBDA_ROLE_NAME}"

echo "Deploying Lambda function: $LAMBDA_NAME"
echo "Region: $AWS_REGION"
echo "Python version: $PYTHON_VERSION"

# Ensure uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Create a temporary directory for packaging
TEMP_DIR=$(mktemp -d)
echo "Using temporary directory: $TEMP_DIR"

# Clean up on exit
cleanup() {
    echo "Cleaning up temporary directory..."
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Install dependencies using uv
echo "Installing dependencies using uv..."
uv pip install --no-cache -t "$TEMP_DIR" --system .

# Copy Lambda function code
echo "Copying Lambda function code..."
cp lambda_function.py "$TEMP_DIR/"
cp __init__.py "$TEMP_DIR/"

# Create deployment package
echo "Creating deployment package..."
cd "$TEMP_DIR"
zip -r lambda_deployment_package.zip .
cd -
mv "$TEMP_DIR/lambda_deployment_package.zip" .

# Check if Lambda function exists
if aws lambda get-function --function-name "$LAMBDA_NAME" --region "$AWS_REGION" &> /dev/null; then
    echo "Updating existing Lambda function..."
    aws lambda update-function-code \
        --function-name "$LAMBDA_NAME" \
        --zip-file fileb://lambda_deployment_package.zip \
        --region "$AWS_REGION"
    
    # Update configuration if specified
    aws lambda update-function-configuration \
        --function-name "$LAMBDA_NAME" \
        --timeout "${LAMBDA_TIMEOUT:-30}" \
        --memory-size "${LAMBDA_MEMORY:-128}" \
        --region "$AWS_REGION"
    
    echo "Lambda function $LAMBDA_NAME updated successfully"
else
    echo "Creating new Lambda function..."
    aws lambda create-function \
        --function-name "$LAMBDA_NAME" \
        --runtime "python${PYTHON_VERSION}" \
        --handler "lambda_function.lambda_handler" \
        --role "$LAMBDA_ROLE_ARN" \
        --zip-file fileb://lambda_deployment_package.zip \
        --region "$AWS_REGION" \
        --timeout "${LAMBDA_TIMEOUT:-30}" \
        --memory-size "${LAMBDA_MEMORY:-128}"
    
    echo "Lambda function $LAMBDA_NAME created successfully"
fi

# Set up SQS trigger if specified
if [ ! -z "$SQS_QUEUE_NAME" ]; then
    # Get the SQS queue ARN
    SQS_QUEUE_ARN=$(aws sqs get-queue-url --queue-name "$SQS_QUEUE_NAME" --region "$AWS_REGION" --query 'QueueUrl' --output text | xargs -I{} aws sqs get-queue-attributes --queue-url {} --attribute-names QueueArn --region "$AWS_REGION" --query 'Attributes.QueueArn' --output text)
    
    if [ ! -z "$SQS_QUEUE_ARN" ]; then
        echo "Setting up SQS trigger from queue: $SQS_QUEUE_NAME"
        
        # Check if mapping already exists
        EXISTING_MAPPING=$(aws lambda list-event-source-mappings --function-name "$LAMBDA_NAME" --region "$AWS_REGION" --query "EventSourceMappings[?EventSourceArn=='$SQS_QUEUE_ARN'] | [0].UUID" --output text)
        
        if [ "$EXISTING_MAPPING" != "None" ] && [ ! -z "$EXISTING_MAPPING" ]; then
            echo "Updating existing SQS trigger..."
            aws lambda update-event-source-mapping \
                --uuid "$EXISTING_MAPPING" \
                --batch-size "${SQS_BATCH_SIZE:-10}" \
                --region "$AWS_REGION"
        else
            echo "Creating new SQS trigger..."
            aws lambda create-event-source-mapping \
                --function-name "$LAMBDA_NAME" \
                --event-source-arn "$SQS_QUEUE_ARN" \
                --batch-size "${SQS_BATCH_SIZE:-10}" \
                --region "$AWS_REGION"
        fi
    else
        echo "Warning: SQS queue $SQS_QUEUE_NAME not found. Skipping trigger setup."
    fi
fi

# Create or update function alias if specified
if [ ! -z "$LAMBDA_ALIAS" ]; then
    LATEST_VERSION=$(aws lambda publish-version \
        --function-name "$LAMBDA_NAME" \
        --region "$AWS_REGION" \
        --query 'Version' \
        --output text)
    
    # Check if alias exists
    if aws lambda get-alias --function-name "$LAMBDA_NAME" --name "$LAMBDA_ALIAS" --region "$AWS_REGION" &> /dev/null; then
        echo "Updating alias $LAMBDA_ALIAS to version $LATEST_VERSION..."
        aws lambda update-alias \
            --function-name "$LAMBDA_NAME" \
            --name "$LAMBDA_ALIAS" \
            --function-version "$LATEST_VERSION" \
            --region "$AWS_REGION"
    else
        echo "Creating alias $LAMBDA_ALIAS pointing to version $LATEST_VERSION..."
        aws lambda create-alias \
            --function-name "$LAMBDA_NAME" \
            --name "$LAMBDA_ALIAS" \
            --function-version "$LATEST_VERSION" \
            --region "$AWS_REGION"
    fi
fi

echo "Deployment complete. Lambda package: lambda_deployment_package.zip" 