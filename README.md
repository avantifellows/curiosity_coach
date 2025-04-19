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

This script starts both the backend and frontend development servers.

#### Option 2: Run Backend and Frontend Separately

**Terminal 1 - Backend:**
```bash
cd backend
./run.sh
# Or manually:
source venv/bin/activate
export FLASK_ENV=development
python app.py
```

**Terminal 2 - Frontend:**
```bash
cd curiosity-coach-frontend
npm start
```

### 5. Access the Application

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