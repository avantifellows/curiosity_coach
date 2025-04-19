# Curiosity Coach Backend API

A Flask-based backend API for the Curiosity Coach chatbot application.

## Features

- RESTful API with Flask
- PostgreSQL database integration
- User authentication with phone number
- Message storage and retrieval
- AWS SQS integration for message queuing
- Simulated Lambda processing

## API Endpoints

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

### Installation

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update with your database and AWS credentials

3. Run the server:
   ```
   python app.py
   ```

The server will run on http://localhost:5000 by default.

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
python app.py
```

This will start the Flask server with debug mode enabled. 