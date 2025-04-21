#!/bin/bash

# Set environment to development
export APP_ENV=development

# Load environment variables from .env.local
if [ -f ".env.local" ]; then
    echo "Loading environment variables from .env.local"
    export $(grep -v '^#' .env.local | xargs)
elif [ -f "../.env.local" ]; then
    echo "Loading environment variables from ../.env.local"
    export $(grep -v '^#' ../.env.local | xargs)
fi

# Set up virtual environment path
VENV_PATH=".venv"
VENV_ACTIVATE="$VENV_PATH/bin/activate"

# Check if venv exists, if not create it
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment using uv..."
    uv venv
    # Ensure venv is activated
    source "$VENV_ACTIVATE"
    echo "Installing dependencies from requirements.lock..."
    uv pip install -r requirements.lock
else
    # Ensure venv is activated
    source "$VENV_ACTIVATE"
fi

# Verify the virtual environment is active and has uvicorn
if ! python -c "import uvicorn" &>/dev/null; then
    echo "Error: uvicorn module not found in the virtual environment"
    echo "Attempting to install dependencies..."
    uv pip install -r requirements.lock
    # Check again
    if ! python -c "import uvicorn" &>/dev/null; then
        echo "Failed to install uvicorn. Please check your environment setup."
        exit 1
    fi
fi

# Create the database if it doesn't exist
echo "Checking database..."
PGPASSWORD=$DB_PASSWORD psql -U postgres -h localhost -c "SELECT 1 FROM pg_database WHERE datname = 'curiosity_coach'" | grep -q 1
if [ $? -ne 0 ]; then
    echo "Creating database 'curiosity_coach'..."
    PGPASSWORD=$DB_PASSWORD psql -U postgres -h localhost -c "CREATE DATABASE curiosity_coach"
fi

# Run the FastAPI app with uvicorn
echo "Starting FastAPI server..."
python -m uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload --log-level info --no-access-log 