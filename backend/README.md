# Curiosity Coach Backend API

A FastAPI-based backend API for the Curiosity Coach chatbot application, structured according to best practices.

## Features

- RESTful API with FastAPI
- Interactive API documentation with Swagger UI
- Modular project structure following FastAPI best practices
- PostgreSQL database integration
- User authentication with phone number
- Message storage and retrieval
- AWS SQS integration for message queuing
- Simulated Lambda processing

## Project Structure

```
backend/
├── src/                   # Source code
│   ├── auth/              # Authentication module
│   │   ├── router.py      # API endpoints for authentication
│   │   ├── schemas.py     # Pydantic models for request/response
│   │   ├── service.py     # Business logic for auth
│   │   └── dependencies.py# Auth dependencies (e.g., get_user_id)
│   ├── messages/          # Messages module
│   │   ├── router.py      # API endpoints for messages
│   │   ├── schemas.py     # Pydantic models for messages
│   │   └── service.py     # Business logic for messages
│   ├── health/            # Health check module
│   │   ├── router.py      # API endpoint for health check
│   │   └── schemas.py     # Pydantic models for health check
│   ├── config/            # Configuration
│   │   └── settings.py    # Application settings
│   ├── database.py        # Database connection and setup
│   ├── models.py          # Database models and operations
│   ├── queue_service.py   # SQS queue service
│   └── main.py            # Main application entry point
├── schema.sql             # Database schema
├── requirements.txt       # Project dependencies
├── run.sh                 # Script to run the application
└── .env.local             # Environment variables (development)
```

## API Endpoints

### Documentation

- **GET /api/docs**
  - Interactive API documentation with Swagger UI
  - Test API endpoints directly from the browser

### Authentication

- **POST /api/auth/login**
  - Authenticates a user with a phone number
  - Creates a new user if the phone number doesn't exist
  - Returns a user object with ID for subsequent authenticated requests

### Messages

- **POST /api/messages**
  - Sends a new message
  - Requires authentication header: `Authorization: Bearer <user_id>`
  - Saves the message to the database
  - Sends the message to SQS queue
  - Returns the saved message and a simulated response

- **GET /api/messages/history**
  - Gets chat history for the authenticated user
  - Requires authentication header: `Authorization: Bearer <user_id>`
  - Returns an array of messages

## Setup

### Prerequisites

- Python 3.8+
- PostgreSQL database
- AWS account for SQS (optional for development)
- `uv` package installer: `pip install uv`

### Installation

1. Install dependencies:
   ```
   ./run.sh
   ```
   
   This will:
   - Create a virtual environment using `uv` (in `.venv` directory)
   - Install dependencies from the lock file
   - Set up the database
   - Start the FastAPI server

2. Configure environment variables:
   - Copy `.env.example` to `.env.local`
   - Update with your database and AWS credentials

3. Run the server:
   ```
   ./run.sh
   ```

The server will run on http://localhost:5000 by default.
API documentation will be available at http://localhost:5000/api/docs

### Dependency Management

This project uses `uv` for dependency management, which provides faster and more reliable dependency resolution than pip.

We provide a dependency management script to help with common tasks:

```bash
# Update all dependencies
./dependencies.sh update

# Add a new package
./dependencies.sh add package-name

# Remove a package
./dependencies.sh remove package-name

# Install dependencies from lock file
./dependencies.sh install

# Show help
./dependencies.sh help
```

The workflow is:
1. Packages are listed in `requirements.txt`
2. The exact versions are locked in `requirements.lock`
3. Installation happens from the lock file for reproducible builds

## Database

The application uses PostgreSQL with the following schema:

- **users** - Stores user information
  - id (primary key)
  - phone_number (unique)
  - created_at

- **messages** - Stores chat messages
  - id (primary key)
  - user_id (foreign key to users)
  - content
  - is_user (boolean - true if from user, false if from bot)
  - timestamp

## AWS Integration

The backend integrates with AWS services:

- **SQS** - For message queuing
  - Messages are sent to an SQS queue for processing by a Lambda function
  - In development, Lambda processing is simulated for simplicity

## Development

To run the backend in development mode:

```
./run.sh
```

This will start the FastAPI server with hot reload enabled. 