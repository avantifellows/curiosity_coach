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
if [ -z "$AWS_REGION" ] || [ -z "$AWS_ACCOUNT_ID" ] || [ -z "$LAMBDA_ROLE_NAME" ]; then
    echo "Error: Required environment variables are not set. Please check your $ENV_FILE file."
    exit 1
fi

# Create the full IAM role ARN
IAM_ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/${LAMBDA_ROLE_NAME}"

# Create trust policy document for Lambda
TRUST_POLICY='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}'

# Create execution policy document for Lambda (basic execution + SQS)
EXECUTION_POLICY='{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ],
      "Resource": "arn:aws:sqs:*:*:*"
    }
  ]
}'

# Check if the role already exists
if aws iam get-role --role-name "$LAMBDA_ROLE_NAME" 2>/dev/null; then
    echo "Role $LAMBDA_ROLE_NAME already exists. Updating trust relationship..."
    
    # Update the trust relationship
    aws iam update-assume-role-policy \
        --role-name "$LAMBDA_ROLE_NAME" \
        --policy-document "$TRUST_POLICY"
    
    echo "Trust relationship updated successfully."
else
    echo "Creating new IAM role: $LAMBDA_ROLE_NAME"
    
    # Create the role with trust policy
    aws iam create-role \
        --role-name "$LAMBDA_ROLE_NAME" \
        --assume-role-policy-document "$TRUST_POLICY"
    
    echo "IAM role created successfully."
    
    # Wait a moment for role to be available
    echo "Waiting for role to be available..."
    sleep 10
fi

# Attach the Lambda basic execution policy
echo "Attaching Lambda execution policies..."

# Create a policy for Lambda execution with SQS permissions
POLICY_NAME="${LAMBDA_ROLE_NAME}-policy"

# Check if policy exists, create or update it
if aws iam get-policy --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}" 2>/dev/null; then
    echo "Policy $POLICY_NAME already exists. Creating new version..."
    
    # Create a new version of the policy
    aws iam create-policy-version \
        --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}" \
        --policy-document "$EXECUTION_POLICY" \
        --set-as-default
else
    echo "Creating new policy: $POLICY_NAME"
    
    # Create a new policy
    aws iam create-policy \
        --policy-name "$POLICY_NAME" \
        --policy-document "$EXECUTION_POLICY"
    
    # Attach the policy to the role
    aws iam attach-role-policy \
        --role-name "$LAMBDA_ROLE_NAME" \
        --policy-arn "arn:aws:iam::${AWS_ACCOUNT_ID}:policy/${POLICY_NAME}"
fi

# Also attach the AWS managed Lambda basic execution role for good measure
aws iam attach-role-policy \
    --role-name "$LAMBDA_ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

echo "IAM role $LAMBDA_ROLE_NAME is ready for Lambda use."
echo "Role ARN: $IAM_ROLE_ARN" 