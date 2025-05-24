# Backend Service for Curiosity Coach

This backend service is a FastAPI application designed to power Curiosity Coach. It handles business logic, data storage, and interactions with external services like AWS.

## Project Overview

The application is built using Python and FastAPI, leveraging SQLAlchemy for database interactions with a PostgreSQL database, and Alembic for managing database migrations. It is designed to be deployable on AWS Lambda using Mangum.

Key features and modules include:
- User authentication and authorization (`src/auth/`)
- Management of conversations (`src/conversations/`)
- Handling of messages (`src/messages/`)
- A queueing system (implied by `src/queue/`)
- Health checks (`src/health/`)
- Application and database configuration (`src/config/`, `src/database.py`, `src/models.py`)

## Prerequisites

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) (for environment and package management). Please install this by following the provided link.
- Docker (for building the containerized application if you are planning to deploy from your local machine)
- `.env.local` file in the `backend` directory. Take the file from a team member.
- [**Optional**] `.env.prod` file in the `backend` directory. If you want to apply the DB migrations to the production database.
- AWS CLI configured (if planning to deploy from your local machine)


## Environment Setup

1.  **Clone the repository (if not already done):**
    ```bash
    # git clone <repository-url>
    cd backend
    ```

2.  **Configuration File:**
    The application uses a `.env.local` file for environment-specific configurations.
    - If `.env.example` exists in the `backend` directory, the `run.sh` script will attempt to copy it to `.env.local`. But it will throw an error and ask you to update the placeholder values.
    - Or you can manually copy `.env.example` to `.env.local` if needed and update the placeholder values:
      ```bash
      cp .env.example .env.local
      ```
    - Key variables to configure include:
      - `APP_ENV`: Set to `development` or `production`.
      - `PORT`: Default is 5000, let it be.
      - `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`: PostgreSQL connection details.
      - `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`: AWS credentials.
      - `SQS_QUEUE_URL`: URL of the SQS queue. Let this be empty if you're running the app locally. Locally the backend directly talks to the Brain instead of using SQS.

## Running Locally

The `run.sh` script automates most of the setup and execution steps for local development.

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
- Ensure `.env.local` is present (copies from `.env.example` if necessary).
- Load environment variables from `.env.local`.
- Validate AWS credentials.
- Set up a Python virtual environment in `./venv` using `uv`.
- Compile `requirements.txt` to `requirements.lock` if needed.
- Install dependencies from `requirements.lock` using `uv`.
- Check if the PostgreSQL database (default: `curiosity_coach`) exists and create it if not.
- Check if port 5000 is in use, attempt to kill the process if it is.
- Start the FastAPI application using Uvicorn on `0.0.0.0:5000` with auto-reload.

You should see output indicating the server is running, typically:
`INFO:     Uvicorn running on http://0.0.0.0:5000 (Press CTRL+C to quit)`
`INFO:     Started reloader process [...] using StatReload`

## Database Migrations (Alembic)

Alembic is used for managing database schema migrations. The configuration is in `alembic.ini` and migration scripts are in `alembic/versions/`.

**To initialize a freshly created database with up to date migrations or even an existing db, we'll use an alembic command (after setting up `.env.local` and ensuring the database exists):**
First, ensure your virtual environment is active:
```bash
source venv/bin/activate
```

Then make sure in `backend/src/config/settings.py` file, the env file being used in the local one. Look for this line
```
env_file = '.env.local'
```

This means the db we'll run migrations on is the local db.
Apply migrations:
```bash
alembic upgrade head
```

**To create a new migration:**
After making changes to SQLAlchemy models in `src/models.py`:
```bash
alembic revision -m "your_migration_message" --autogenerate
```
Review the generated script in `alembic/versions/` and then apply it:
```bash
alembic upgrade head
```

## Dependencies

Key Python dependencies are listed in `requirements.txt`. The `run.sh` script manages their installation into a virtual environment using `uv` and a `requirements.lock` file.

- **FastAPI**: For building the API.
- **Uvicorn**: ASGI server for FastAPI.
- **SQLAlchemy**: ORM for database interaction.
- **Psycopg2-binary**: PostgreSQL adapter for Python.
- **Alembic**: Database migration tool.
- **Pydantic**: Data validation and settings management.
- **Boto3**: AWS SDK for Python.
- **Mangum**: To run FastAPI on AWS Lambda.
- **python-dotenv**: For loading environment variables from `.env` files.
- **Passlib & python-jose**: For password hashing and JWT token handling.
- **uv**: For fast Python package installation and venv management.

## Terraform Infrastructure

The backend infrastructure is managed using Terraform. The definitions for the AWS resources, including AWS Lambda, RDS for PostgreSQL, ECR, SQS, and necessary IAM roles and security groups, are located in the `terraform` directory at the root of the project.

Key files in the `terraform` directory:
- `terraform/backend.tf`: Contains the main configuration for the backend resources, such as the Lambda function, RDS database instance, ECR repository, and related networking components.
- `terraform/variables.tf`: Defines variables used within the Terraform configurations, such as `project_name`, `environment`, `aws_region`, and `aws_profile`. You can customize these variables to suit your deployment needs.
- `terraform/outputs.tf`: Specifies the outputs from the Terraform configuration, such as the Lambda function URL and RDS connection details.

### Managing Infrastructure

To manage the infrastructure, navigate to the `terraform` directory in your terminal. Ensure you have [Terraform installed](https://learn.hashicorp.com/tutorials/terraform/install-cli) and your AWS credentials configured (matching the `aws_profile` specified in `terraform/variables.tf` or your environment).

Common Terraform commands:

1.  **Initialize Terraform:**
    This command initializes the working directory, downloading necessary provider plugins.
    ```bash
    cd ../terraform  # Assuming you are in the backend directory
    terraform init
    ```

2.  **Plan Changes:**
    This command creates an execution plan, showing you what actions Terraform will take to achieve the desired state defined in the configuration files.
    ```bash
    terraform plan
    ```

3.  **Apply Changes:**
    This command applies the changes required to reach the desired state of the configuration.
    ```bash
    terraform apply
    ```
    You will be prompted to confirm the changes before they are applied.

4.  **Destroy Infrastructure:**
    This command will destroy all the resources managed by the Terraform configuration in this directory. Use with caution.
    ```bash
    terraform destroy
    ```

The `terraform/backend.tf` file also includes a `null_resource` named `backend_docker_build_push` which handles building and pushing the backend Docker image to ECR as part of the `terraform apply` process. The Lambda function is then configured to use this image.

The RDS instance details (host, port, name, user, password) are dynamically generated or configured by Terraform and injected as environment variables into the backend Lambda function. Refer to the `aws_lambda_function` resource block in `terraform/backend.tf` for details on how environment variables are set.

## Project Structure

```
backend/
├── alembic/                  # Alembic migration scripts and environment
│   ├── versions/             # Individual migration files - Check migrations here
│   ├── env.py                # Alembic environment setup - No need to touch
│   └── script.py.mako        # Migration script template - No need to touch
├── src/                      # Main application source code
│   ├── auth/                 # Authentication module
│   ├── config/               # Configuration files/logic
│   ├── conversations/        # Conversations module
│   ├── health/               # Health check endpoint(s)
│   ├── messages/             # Messages module
│   ├── queue/                # Queue interaction module
│   ├── __init__.py
│   ├── database.py           # Database session and engine setup
│   ├── main.py               # FastAPI application entry point
│   └── models.py             # SQLAlchemy ORM models
├── venv/                     # Python virtual environment (created by run.sh)
├── .env.example              # Example environment variables
├── .gitignore
├── alembic.ini               # Alembic configuration file - No need to touch
├── Dockerfile                # For building the application container
├── README.md                 # This file
├── requirements.lock         # Pinned dependencies (generated by uv)
├── requirements.txt          # Main Python dependencies
└── run.sh                    # Script for local development setup and execution
```