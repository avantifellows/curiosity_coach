#!/bin/bash
set -e

echo "Running Lambda function local test with LocalStack"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if LocalStack is already running
if docker ps | grep -q localstack; then
    echo "LocalStack is already running"
else
    echo "Starting LocalStack with docker-compose..."
    docker-compose up -d
    
    # Wait for LocalStack to be ready
    echo "Waiting for LocalStack to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:4566/health > /dev/null; then
            echo "LocalStack is ready!"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "Error: LocalStack failed to start within 30 seconds"
            exit 1
        fi
        echo -n "."
        sleep 1
    done
fi

# Ensure uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Installing..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Create and activate virtual environment if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment using uv..."
    uv venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies using uv..."
uv pip install boto3 requests

# Clear any previous test data
if [ -f "mock_db.json" ]; then
    echo "Clearing previous test data..."
    rm mock_db.json
fi

# Run the test script
echo "Running test script..."
python test_local.py "$@"

# Option to view the mock database
if [ -f "mock_db.json" ]; then
    echo ""
    echo "Mock database content:"
    echo "----------------------------------------"
    cat mock_db.json
    echo "----------------------------------------"
fi

echo ""
echo "Test completed!"
echo "To view LocalStack logs: docker logs -f localstack"
echo "To stop LocalStack: docker-compose down" 