#!/bin/bash

# Set environment to development
export APP_ENV=development

echo "Running in Brain component. Current working directory: $(pwd)"

# Define .env and .env.example paths relative to the script's location (Brain/)
ENV_FILE_PATH="src/.env"
ENV_EXAMPLE_PATH="src/.env.example"

# Check if .env exists, if not, copy from .env.example
if [ ! -f "$ENV_FILE_PATH" ]; then
    echo "$ENV_FILE_PATH not found."
    if [ -f "$ENV_EXAMPLE_PATH" ]; then
        echo "Creating $ENV_FILE_PATH from $ENV_EXAMPLE_PATH..."
        cp "$ENV_EXAMPLE_PATH" "$ENV_FILE_PATH"
        if [ $? -ne 0 ]; then
            echo "Error: Failed to copy $ENV_EXAMPLE_PATH to $ENV_FILE_PATH." >&2
            exit 1
        fi
    else
        echo "Error: $ENV_EXAMPLE_PATH not found. Cannot create $ENV_FILE_PATH." >&2
        echo "Please create $ENV_EXAMPLE_PATH or $ENV_FILE_PATH manually with the required environment variables." >&2
        exit 1
    fi
fi

# Load environment variables from .env
if [ -f "$ENV_FILE_PATH" ]; then
    echo "Loading environment variables from $ENV_FILE_PATH..."
    set -o allexport
    source "./$ENV_FILE_PATH" # Source with relative path
    set +o allexport
else
    # This case should ideally not be reached if the above block works.
    echo "Critical Error: $ENV_FILE_PATH not found after attempting to create it. Cannot load environment variables." >&2
    exit 1
fi


# Check for empty string values in .env (e.g., KEY="" or KEY='')
echo "Validating $ENV_FILE_PATH for empty string values..."
EMPTY_VALUE_ERRORS=0
if [ -f "$ENV_FILE_PATH" ]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip comments and truly empty lines
        if [[ "$line" =~ ^\s*# ]] || [[ "$line" =~ ^\s*$ ]]; then
            continue
        fi

        # Extract key and value, trimming whitespace
        key_name=$(echo "$line" | cut -d '=' -f1 | sed 's/^[ \t]*//;s/[ \t]*$//')
        value_part=$(echo "$line" | cut -d '=' -f2- | sed 's/^[ \t]*//;s/[ \t]*$//')

        if [[ "$value_part" == "\"\"" ]] || [[ "$value_part" == "''" ]]; then # Check for "" or ''
            echo "Error: Variable '$key_name' in $ENV_FILE_PATH has an empty string value ($value_part). Please provide a valid value." >&2
            EMPTY_VALUE_ERRORS=$((EMPTY_VALUE_ERRORS + 1))
        fi
    done < "$ENV_FILE_PATH"
else
    echo "Warning: $ENV_FILE_PATH not found during validation phase. This should not happen." >&2
    # This indicates a problem earlier, but we'll count it as an error state.
    EMPTY_VALUE_ERRORS=$((EMPTY_VALUE_ERRORS + 1))
fi

if [ $EMPTY_VALUE_ERRORS -ne 0 ]; then
  echo "Environment variable validation failed ($EMPTY_VALUE_ERRORS errors due to empty string values). Please check your $ENV_FILE_PATH file." >&2
  exit 1
fi
echo "$ENV_FILE_PATH validated successfully for empty string values."


# Set up virtual environment path
VENV_PATH="venv" # As requested, not .venv
VENV_ACTIVATE="$VENV_PATH/bin/activate"
REQUIREMENTS_TXT="requirements.txt" # Assumed to be in Brain/

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 command not found. Please install Python 3." >&2
    exit 1
fi

# Check if venv exists, if not create it
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment using python3 at $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment at $VENV_PATH." >&2
        exit 1
    fi
    echo "Activating virtual environment..."
    source "$VENV_ACTIVATE"
    echo "Installing dependencies from $REQUIREMENTS_TXT..."
    python -m pip install -r "$REQUIREMENTS_TXT"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to install dependencies from $REQUIREMENTS_TXT into new venv." >&2
        exit 1
    fi
else
    echo "Virtual environment $VENV_PATH exists. Activating..."
    source "$VENV_ACTIVATE"
    echo "Installing/updating dependencies from $REQUIREMENTS_TXT..."
    python -m pip install -r "$REQUIREMENTS_TXT"
    if [ $? -ne 0 ]; then
        echo "Warning: Failed to install/update dependencies from $REQUIREMENTS_TXT. Continuing with existing state, but this might cause issues." >&2
    fi
fi

# Verify the virtual environment has uvicorn
if ! python -c "import uvicorn" &>/dev/null; then
    echo "Error: uvicorn module not found in the virtual environment $VENV_PATH." >&2
    echo "This could be due to uvicorn not being in $REQUIREMENTS_TXT or an installation issue." >&2
    echo "Attempting to install dependencies again from $REQUIREMENTS_TXT..."
    python -m pip install -r "$REQUIREMENTS_TXT"
    if [ $? -ne 0 ]; then
        echo "Critical Error: Failed to install dependencies during uvicorn check retry." >&2
        exit 1
    fi
    if ! python -c "import uvicorn" &>/dev/null; then
        echo "Critical Error: Failed to ensure uvicorn is installed after retry. Please check $REQUIREMENTS_TXT and your environment setup." >&2
        exit 1
    fi
fi
echo "Uvicorn check passed."

# Define the port
# PORT may have been set by sourcing .env. If not, use default.
DEFAULT_APP_PORT=8000
# Use parameter expansion: If PORT is unset or null, use DEFAULT_APP_PORT. If PORT is set (even to empty string, handled by earlier check), use its value.
FINAL_APP_PORT="${PORT:-$DEFAULT_APP_PORT}"
# Export it for the application
export PORT="$FINAL_APP_PORT"

TIMEOUT_SECONDS=10

# Check if port is in use and potentially kill the process
echo "Checking if port $FINAL_APP_PORT is in use..."
PID=$(lsof -ti :$FINAL_APP_PORT)

if [ -n "$PID" ]; then
  echo "Port $FINAL_APP_PORT is in use by PID(s): $PID. Attempting to kill..."
  kill -9 $PID
  # Wait for a moment to allow the OS to release the port
  sleep 1 # Give a brief moment for the port to free up after kill
  echo "Waiting up to $TIMEOUT_SECONDS seconds for port $FINAL_APP_PORT to become free..."

  SECONDS_WAITED=0
  while [ $SECONDS_WAITED -lt $TIMEOUT_SECONDS ]; do
    if ! lsof -ti :$FINAL_APP_PORT > /dev/null; then
      echo "Port $FINAL_APP_PORT is now free."
      PID="" # Clear PID to signal success
      break
    fi
    sleep 1
    SECONDS_WAITED=$((SECONDS_WAITED + 1))
  done

  if [ -n "$PID" ]; then # If PID is still set, port didn't free up
      echo "Error: Port $FINAL_APP_PORT did not become free after $TIMEOUT_SECONDS seconds." >&2
      exit 1
  fi
else
  echo "Port $FINAL_APP_PORT is initially free."
fi

# Run the FastAPI app
# User specified "python main.py". Assuming it's in src/ and handles PORT from env.
echo "Starting application: python -m src.main on port $FINAL_APP_PORT..."
python -m src.main 