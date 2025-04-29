# Curiosity Coach

A modern chatbot application with a React frontend and Flask backend, using PostgreSQL for data storage and AWS SQS for message processing.

## Architecture

The application follows a modern, scalable architecture:

- **Frontend**: React application with TypeScript and Material UI
- **Backend**: Flask RESTful API 
- **Database**: PostgreSQL for message and user storage
- **Queue**: AWS SQS for message processing
- **Processing**: AWS Lambda for message processing (simulated during development)

## Features

- User authentication with phone number
- Real-time chat interface with message history
- PostgreSQL database for persistent storage
- Message queue integration for scalable processing
- Responsive Material UI design

## Project Structure

```
curiosity-coach/
├── backend/               # Flask backend API
│   ├── app.py             # Main Flask application
│   ├── database.py        # Database interaction module
│   ├── queue_service.py   # AWS SQS integration
│   └── requirements.txt   # Python dependencies
│
├── lambda_function/       # AWS Lambda function
│   ├── lambda_function.py # Main Lambda handler
│   ├── pyproject.toml     # Dependencies and project config
│   ├── test_lambda_function.py # Unit tests
│   └── deploy.sh          # Deployment script
│
└── curiosity-coach-frontend/  # React frontend
    ├── public/            # Static assets
    ├── src/               # Source code
    │   ├── components/    # React components
    │   ├── context/       # React context providers
    │   ├── services/      # API services
    │   └── types/         # TypeScript type definitions
    └── package.json       # Node.js dependencies
```

## Setup and Running Instructions

### Prerequisites

- Node.js 14+ and npm
- Python 3.8+
- PostgreSQL 14+
- AWS account (optional for development)

### 1. PostgreSQL Setup

#### Starting PostgreSQL Server (macOS)

**Using Homebrew:**
```bash
# Start PostgreSQL
brew services start postgresql@14

# Check status
brew services list | grep postgres
```

**Using PostgreSQL.app:**
1. Open PostgreSQL.app from Applications folder
2. Click "Start" button

**Troubleshooting PostgreSQL:**

If you see a port conflict with AirPlay Receiver on port 5000:
1. Go to System Settings → Sharing
2. Turn off "AirPlay Receiver"

If PostgreSQL requires a password:
```bash
export PGPASSWORD=yourpassword
```

#### Create the Database
```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE curiosity_coach;

# Exit psql
\q
```

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env.local file
cp .env.example .env.local
# Edit .env.local with your PostgreSQL credentials
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd curiosity-coach-frontend

# Install dependencies
npm install
```

### 4. Running the Application

#### Option 1: Run Both Frontend and Backend Together

```bash
# From project root
./run_dev.sh
```

This script starts both the backend and frontend development servers. Use `Ctrl+C` to gracefully stop both servers.

#### Option 2: Run Backend and Frontend Separately

**Terminal 1 - Backend:**
```bash
cd backend
./run.sh
```

**Terminal 2 - Frontend:**
```bash
cd curiosity-coach-frontend
npm start
```

### 5. Stopping the Servers

If you need to forcefully stop the servers at any time:

```bash
# From project root
./kill_servers.sh
```

This script kills both the frontend and backend processes.

### 6. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:5000
- API Health Check: http://localhost:5000/api/health

### Common Issues and Solutions

- **Port 5000 already in use:** Change the port in backend/.env.local (PORT=5001) and update the proxy in curiosity-coach-frontend/package.json
- **Database connection error:** Ensure PostgreSQL is running and credentials are correct
- **Module not found errors:** Verify all dependencies are installed properly

## Documentation

- [Frontend Documentation](./curiosity-coach-frontend/README.md)
- [Backend Documentation](./backend/README.md)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](./LICENSE) file for details.

## Lambda Function

The AWS Lambda function for processing messages is located in the `lambda_function/` directory. See the specific [Lambda README](./lambda_function/README.md) for details on setup and deployment.

# Curiosity Coach Lambda Function

This Lambda function processes messages from an SQS queue, calls an LLM API based on the message purpose, and saves the responses to a database.

## Structure

The SQS message structure expected by this Lambda function is:

```json
{
  "user_id": "user123",
  "message_id": "db_message_789",
  "purpose": "test_generation",
  "conversation_id": "conv_456"
}
```

## Components

- `lambda_function.py`: Main Lambda handler function
- `requirements.txt`: Dependencies required for the Lambda function
- `test_lambda_function.py`: Unit tests for the Lambda function

## Setup and Deployment

### Prerequisites

- AWS Account
- AWS CLI configured
- Python 3.8+

### Local Testing

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the unit tests:

```bash
python -m unittest test_lambda_function.py
```

### Deployment to AWS Lambda

1. Create a deployment package:

```bash
pip install -r requirements.txt -t ./package
cp *.py ./package/
cd package
zip -r ../lambda_deployment_package.zip .
```

2. Create the Lambda function using AWS CLI:

```bash
aws lambda create-function \
  --function-name CuriosityCoach \
  --runtime python3.9 \
  --handler lambda_function.lambda_handler \
  --role arn:aws:iam::<account-id>:role/lambda-sqs-role \
  --zip-file fileb://lambda_deployment_package.zip
```

3. Create an SQS trigger for the Lambda function:

```bash
aws lambda create-event-source-mapping \
  --function-name CuriosityCoach \
  --event-source-arn arn:aws:sqs:<region>:<account-id>:<queue-name> \
  --batch-size 10
```

## Implementation Notes

- The function currently uses placeholder implementations for database operations and LLM API calls
- These need to be replaced with actual implementations based on your infrastructure
- Different model parameters are used based on the message purpose

## Future Improvements

- Implement actual database integration
- Add more robust error handling and retry logic
- Support for more purpose types and model parameters
- Add CloudWatch metrics and alarms 