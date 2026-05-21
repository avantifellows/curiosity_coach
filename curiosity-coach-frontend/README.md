# Curiosity Coach Frontend

A React-based frontend for the Curiosity Coach chatbot application.

## Features

- Modern React with TypeScript
- Material UI for beautiful UI components
- User authentication with phone number
- Real-time chat interface
- Message history persistence
- Integration with backend API for message processing

## Architecture

The application follows a layered architecture:

- **Frontend (this repo)**: React-based UI
- **Backend API**: Handles message storage and sends messages to a queue
- **Processing Lambda**: Processes messages from the queue (currently simulated)
- **Database**: PostgreSQL for message and user storage


## Setup

### Prerequisites

- Node.js 18+ and npm
- Python 3.9+ (for the backend)
- PostgreSQL database

### Installation

1. Install frontend dependencies:
   ```
   npm install
   ```

2. Prepare the backend:
   ```
   cd ../backend
   ./run.sh
   ```
   Stop the backend after the first successful startup if you only wanted dependency setup. Run migrations separately with `uv run alembic upgrade head`.

### Configuration

1. Set up environment variables:
   - Copy `.env.example` to `.env` in the backend folder
   - Update with your PostgreSQL and AWS credentials

2. Set up the database:
   - Create a PostgreSQL database
   - Run backend migrations with `cd ../backend && uv run alembic upgrade head`

### Running the Application

#### Development mode (Frontend + Backend)

```
npm run dev
```

This script is stale for the current backend entrypoint. Prefer running the backend with `cd ../backend && ./run.sh`, the Brain with `cd ../Brain && ./run.sh`, and the frontend with `npm start` in this directory.

#### Frontend only

```
npm start
```

#### Backend only

```
cd ../backend
./run.sh
```

## API Integration

The frontend communicates with the backend through RESTful API endpoints:

- `/api/auth/login` - User authentication
- `/api/messages` - Send messages
- `/api/messages/history` - Get chat history

## Deployment

To build the application for production:

```
npm run build
```

This creates a `build` folder with optimized production assets that can be deployed to a static hosting service.

## Project Structure

- `src/components/` - React UI components
- `src/services/` - API service functions
- `src/context/` - React context providers
- `src/types/` - TypeScript interfaces
