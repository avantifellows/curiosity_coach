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

## Setup

### Prerequisites

- Node.js 14+ and npm
- Python 3.8+
- PostgreSQL database
- AWS account (optional for development)

### Running the Application

1. Frontend development:
   ```
   cd curiosity-coach-frontend
   npm start
   ```

2. Backend development:
   ```
   cd backend
   python app.py
   ```

3. Both together:
   ```
   cd curiosity-coach-frontend
   npm run dev
   ```

## Documentation

- [Frontend Documentation](./curiosity-coach-frontend/README.md)
- [Backend Documentation](./backend/README.md)

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](./LICENSE) file for details. 