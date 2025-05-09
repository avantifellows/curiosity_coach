# Brain Service for Curiosity Coach

The Brain service is a core intelligent component of Curiosity Coach. It receives user queries, processes them using Large Language Models (LLMs) and relevant data (potentially fetched from the backend service), and formulates thoughtful responses to guide users in a coaching-like manner.

## Project Overview

This application is built using Python and FastAPI (for local development) and is designed for deployment on AWS Lambda. It leverages LLMs (e.g., Groq, OpenAI) to understand and respond to user inputs. The service is responsible for the primary cognitive tasks of the Curiosity Coach.

Key features and modules include:
- Processing user queries via `src/process_query_entrypoint.py`.
- LLM integration and configuration (see `config/llm_config.json`, `src/services/`).
- Serving requests locally via Uvicorn through `src/main.py`.
- Handling AWS Lambda invocations via `src/lambda_function.py`.
- Structured data handling with Pydantic models (e.g., `src/schemas.py`, `src/config_models.py`).
- Core logic, utilities, and potentially prompt templates in `src/core/`, `src/utils/`, `src/prompts/`, and `src/templates/`.

## Prerequisites

- Python 3.11 (as per Dockerfile)
- `pip` for package management.
- Docker (for building the containerized application if deploying or testing with Docker).
- An `.env` file located in `Brain/src/` for environment-specific configurations. See "Environment Setup" below.

## Environment Setup

1.  **Clone the repository (if not already done):**
    ```bash
    # git clone <repository-url>
    cd Brain
    ```

2.  **Configuration File (`src/.env`):**
    The application requires an environment file at `src/.env`.
    - If `src/.env.example` exists, the `run.sh` script will attempt to copy it to `src/.env` on its first run.
    - You may need to manually create or populate `src/.env` based on `src/.env.example` or team-provided values.
    - This file should contain necessary configurations such as API keys for LLM services, `PORT` for local development (defaults to 8000), and other operational parameters.
    - The `run.sh` script validates that no environment variables in `src/.env` have empty string values (e.g., `KEY=""`).
    - Key environment variables include:
        - `OPENAI_API_KEY`: Your API key for accessing OpenAI's services (e.g., GPT models).
        - `GROQ_API_KEY`: Your API key for accessing Groq's LPU inference engine.
        - `BACKEND_CALLBACK_BASE_URL`: The base URL of the backend service that the Brain will send its results to. For local development, this is typically `http://localhost:5000`.
        - `BACKEND_CALLBACK_ROUTE`: The specific API route on the backend service where the Brain sends its responses (e.g., `/api/internal/brain_response`).
        - `FLOW_CONFIG_S3_BUCKET_NAME`: The S3 bucket name where the `flow_config.json` file is stored. This configuration likely defines the conversation flows or decision logic for the Brain.
        - `FLOW_CONFIG_S3_KEY`: The S3 object key (path within the bucket) for the `flow_config.json` file.

## Running Locally

The `run.sh` script automates the setup and execution steps for local development.

1.  **Make the script executable:**
    ```bash
    chmod +x run.sh
    ```

2.  **Run the script:**
    ```bash
    ./run.sh
    ```

The script will perform the following actions:
- Set `APP_ENV` to `development`.
- Ensure `src/.env` is present and load environment variables from it.
- Set up a Python virtual environment in `./venv`.
- Install dependencies from `requirements.txt` using `pip`.
- Check for and ensure `uvicorn` is installed.
- Check if the specified port (default 8000) is in use and attempt to kill the occupying process.
- Start the FastAPI application using Uvicorn, running `python -m src.main`.

You should see output indicating the server is running, typically:
`INFO:     Uvicorn running on http://0.0.0.0:[PORT] (Press CTRL+C to quit)` (where `[PORT]` is 8000 or as set in `src/.env`)

## Dependencies

Key Python dependencies are listed in `requirements.txt` and managed by `pip` via the `run.sh` script.
Major dependencies include:
- **FastAPI**: For building the API (used locally).
- **Uvicorn**: ASGI server for FastAPI.
- **Jinja2**: Templating engine.
- **Requests & HTTPX**: For making HTTP requests (e.g., to backend or external services).
- **python-dotenv**: For loading environment variables from `.env` files.
- **Groq & OpenAI**: SDKs for interacting with LLM providers.
- **Mangum**: To run FastAPI applications on AWS Lambda.
- **Boto3**: AWS SDK for Python (likely for SQS, S3, or other AWS services integration).
- **Pydantic**: Data validation and settings management.

## Deployment (AWS Lambda)

The service is designed to be deployed as an AWS Lambda function, as configured in the `Dockerfile`.
- The Lambda handler is `src.lambda_function.lambda_handler`.
- The Docker image uses `public.ecr.aws/lambda/python:3.11`.
- Application code from `src/` and configurations from `config/` are included in the deployment package.

## Project Structure

```
Brain/
├── config/                 # Configuration files (e.g., llm_config.json)
│   └── llm_config.json
├── src/                    # Main application source code
│   ├── core/               # Core logic and functionalities
│   ├── prompts/            # Prompt templates for LLMs
│   ├── services/           # Services, e.g., for LLM interaction, backend communication
│   ├── templates/          # HTML or other templates (e.g., for chat_interface)
│   ├── utils/              # Utility functions
│   ├── __init__.py
│   ├── chat_interface.py   # Likely a simple UI or test interface
│   ├── config_models.py    # Pydantic models for configuration
│   ├── lambda_function.py  # AWS Lambda handler
│   ├── main.py             # FastAPI application entry point (local development)
│   ├── process_query_entrypoint.py # Core logic for query processing
│   └── schemas.py          # Pydantic schemas for data validation
├── venv/                   # Python virtual environment (created by run.sh)
├── .gitignore
├── Dockerfile              # For building the application container for AWS Lambda
├── README.md               # This file
├── requirements.txt        # Python dependencies
└── run.sh                  # Script for local development setup and execution
``` 