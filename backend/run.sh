#!/bin/bash

# Set environment to development
export APP_ENV=development

# Check if .env.local exists, if not, copy from .env.example
if [ ! -f ".env.local" ]; then
    echo ".env.local not found."
    if [ -f ".env.example" ]; then
        echo "Creating .env.local from .env.example..."
        cp .env.example .env.local
    else
        echo "Warning: .env.example not found. Cannot create .env.local."
        # Optionally exit here if .env.local is strictly required
        # exit 1
    fi
elif [ -f "../.env.local" ]; then
    # Check if .env.local exists in parent directory
    if [ ! -f ".env.local" ]; then
        echo ".env.local not found in current directory, checking parent directory..."
        if [ -f "../.env.example" ]; then
            echo "Creating .env.local from ../.env.example..."
            cp ../.env.example .env.local
        else
             echo "Warning: ../.env.example not found. Cannot create .env.local."
        fi
    fi
fi

# Load environment variables from .env.local
if [ -f ".env.local" ]; then
    echo "Loading environment variables from .env.local"
    export $(grep -v '^#' .env.local | xargs)
elif [ -f "../.env.local" ]; then
    echo "Loading environment variables from ../.env.local"
    export $(grep -v '^#' ../.env.local | xargs)
fi

# --- AWS Credential Validation ---
echo "Validating AWS credentials..."
AWS_ENV_ERRORS=0
KEY_AUTH_VALID=0

# Determine expected .env.example path based on where .env.local was found/created
ENV_EXAMPLE_PATH=".env.example"
if [ ! -f ".env.local" ] && [ -f "../.env.local" ]; then
  ENV_EXAMPLE_PATH="../.env.example"
elif [ ! -f ".env.local" ] && [ ! -f "../.env.local" ] && [ -f "../.env.example" ]; then
  # Case where .env.local was created from ../.env.example
  ENV_EXAMPLE_PATH="../.env.example"
fi

# Read default values from the example file if it exists
DEFAULT_AWS_ACCESS_KEY_ID=""
DEFAULT_AWS_SECRET_ACCESS_KEY=""
if [ -f "$ENV_EXAMPLE_PATH" ]; then
    DEFAULT_AWS_ACCESS_KEY_ID=$(grep '^AWS_ACCESS_KEY_ID=' "$ENV_EXAMPLE_PATH" | cut -d '=' -f2- | tr -d '"' | tr -d "'")
    DEFAULT_AWS_SECRET_ACCESS_KEY=$(grep '^AWS_SECRET_ACCESS_KEY=' "$ENV_EXAMPLE_PATH" | cut -d '=' -f2- | tr -d '"' | tr -d "'")
fi

# 1. Check AWS_REGION (Required)
if [ -z "$AWS_REGION" ]; then
  echo "Error: AWS_REGION is not set or is empty in .env.local." >&2
  AWS_ENV_ERRORS=$((AWS_ENV_ERRORS + 1))
fi

# 2. Evaluate Key Authentication
KEY_AUTH_CHECKS_PASSED=1 # Assume keys are valid until a check fails

# Check Access Key ID
if [ -z "$AWS_ACCESS_KEY_ID" ]; then
    echo "Error: AWS_ACCESS_KEY_ID is not set or is empty." >&2
    AWS_ENV_ERRORS=$((AWS_ENV_ERRORS + 1))
    KEY_AUTH_CHECKS_PASSED=0
elif [ -n "$DEFAULT_AWS_ACCESS_KEY_ID" ] && [ "$AWS_ACCESS_KEY_ID" == "$DEFAULT_AWS_ACCESS_KEY_ID" ]; then
    echo "Error: AWS_ACCESS_KEY_ID in .env.local must not match the default value in $ENV_EXAMPLE_PATH." >&2
    AWS_ENV_ERRORS=$((AWS_ENV_ERRORS + 1))
    KEY_AUTH_CHECKS_PASSED=0
fi

# Check Secret Access Key
if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    echo "Error: AWS_SECRET_ACCESS_KEY is not set or is empty." >&2
    AWS_ENV_ERRORS=$((AWS_ENV_ERRORS + 1))
    KEY_AUTH_CHECKS_PASSED=0
elif [ -n "$DEFAULT_AWS_SECRET_ACCESS_KEY" ] && [ "$AWS_SECRET_ACCESS_KEY" == "$DEFAULT_AWS_SECRET_ACCESS_KEY" ]; then
    echo "Error: AWS_SECRET_ACCESS_KEY in .env.local must not match the default value in $ENV_EXAMPLE_PATH." >&2
    AWS_ENV_ERRORS=$((AWS_ENV_ERRORS + 1))
    KEY_AUTH_CHECKS_PASSED=0
fi

if [ $KEY_AUTH_CHECKS_PASSED -eq 1 ]; then
    KEY_AUTH_VALID=1
fi


# 3. Final Decision
if [ $KEY_AUTH_VALID -eq 0 ]; then
    # If key auth is not valid, and we haven't already reported errors about *specific* invalid values (like matching defaults)
    # then it must be because required values were missing entirely.
    if [ $AWS_ENV_ERRORS -eq 0 ] || { [ -z "$AWS_ACCESS_KEY_ID" ] && [ -z "$AWS_SECRET_ACCESS_KEY" ]; }; then
       echo "Error: No valid AWS authentication method found. Please configure both AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (non-default) in your .env.local file." >&2
       # Ensure error count is at least 1 if we reach here without prior specific errors
       if [ $AWS_ENV_ERRORS -eq 0 ]; then AWS_ENV_ERRORS=1; fi
    fi
fi

# Exit if any errors were found during validation
if [ $AWS_ENV_ERRORS -ne 0 ]; then
  echo "AWS credential validation failed ($AWS_ENV_ERRORS errors). Please check your .env.local file." >&2
  exit 1
fi

# If we reach here, keys are valid
echo "AWS credentials validated successfully (using Access Keys)."
# --- End AWS Credential Validation ---

# Set up virtual environment path
VENV_PATH="venv"
VENV_ACTIVATE="$VENV_PATH/bin/activate"
REQUIREMENTS_TXT="requirements.txt"
REQUIREMENTS_LOCK="requirements.lock"

# Function to check if uv is installed
check_uv_installed() {
    if ! command -v uv &> /dev/null
    then
        echo "Error: uv command not found."
        echo "Please install uv by following the instructions at: https://github.com/astral-sh/uv"
        exit 1
    fi
}

# Check if venv exists, if not create it
if [ ! -d "$VENV_PATH" ]; then
    echo "Checking if uv is installed..."
    check_uv_installed
    echo "Creating virtual environment using uv..."
    uv venv --python=3.9 "$VENV_PATH" # Explicitly name the venv directory
    # Ensure venv is activated
    source "$VENV_ACTIVATE"
    echo "Compiling dependencies to $REQUIREMENTS_LOCK..."
    uv pip compile "$REQUIREMENTS_TXT" -o "$REQUIREMENTS_LOCK"
    echo "Installing dependencies from $REQUIREMENTS_LOCK..."
    uv pip install -r "$REQUIREMENTS_LOCK"
else
    # Ensure venv is activated
    source "$VENV_ACTIVATE"
    # Check if requirements need recompiling
    if [ "$REQUIREMENTS_TXT" -nt "$REQUIREMENTS_LOCK" ] || [ ! -f "$REQUIREMENTS_LOCK" ]; then
        echo "$REQUIREMENTS_TXT is newer than $REQUIREMENTS_LOCK or $REQUIREMENTS_LOCK does not exist."
        echo "Checking if uv is installed..."
        check_uv_installed
        echo "Recompiling dependencies to $REQUIREMENTS_LOCK..."
        uv pip compile "$REQUIREMENTS_TXT" -o "$REQUIREMENTS_LOCK"
        echo "Installing dependencies from $REQUIREMENTS_LOCK..."
        uv pip install -r "$REQUIREMENTS_LOCK"
    else
        echo "$REQUIREMENTS_LOCK is up to date. Checking installed packages..."
        # Optionally, add a check here to ensure lock file matches installed packages
        # uv pip check # This might be too slow for startup
    fi
fi

# Verify the virtual environment is active and has uvicorn
if ! python -c "import uvicorn" &>/dev/null; then
    echo "Error: uvicorn module not found in the virtual environment"
    echo "Attempting to install dependencies..."
    pip install -r requirements.lock
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

# Define the port
PORT=5000
TIMEOUT_SECONDS=10 # Wait up to 10 seconds for the port to free up

# Check if port is in use and potentially kill the process
echo "Checking if port $PORT is in use..."
PID=$(lsof -ti :$PORT)

if [ -n "$PID" ]; then
  echo "Port $PORT is in use by PID(s): $PID. Attempting to kill..."
  kill -9 $PID
  echo "Waiting up to $TIMEOUT_SECONDS seconds for port $PORT to become free..."

  SECONDS=0
  while [ $SECONDS -lt $TIMEOUT_SECONDS ]; do
    if ! lsof -ti :$PORT > /dev/null; then
      echo "Port $PORT is now free."
      PID="" # Clear PID to signal success
      break
    fi
    sleep 1
    SECONDS=$((SECONDS + 1))
  done

  # Check if the loop finished because the port is free or timed out
  if [ -n "$PID" ]; then
      echo "Error: Port $PORT did not become free after $TIMEOUT_SECONDS seconds."
      exit 1
  fi
else
  echo "Port $PORT is initially free."
fi

# Run the FastAPI app with uvicorn
echo "Starting FastAPI server on port $PORT..."
python -m uvicorn src.main:app --host 0.0.0.0 --port $PORT --reload --log-level info --no-access-log