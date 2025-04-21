#!/bin/bash

# Track process IDs
BACKEND_PID=""
FRONTEND_PID=""
TAIL_PID=""

# Function to kill processes on exit
cleanup() {
    echo "Shutting down servers..."
    if [ -n "$TAIL_PID" ]; then
        kill $TAIL_PID 2>/dev/null
    fi
    
    if [ -n "$FRONTEND_PID" ]; then
        echo "Stopping frontend (PID: $FRONTEND_PID)..."
        kill $FRONTEND_PID 2>/dev/null || kill -9 $FRONTEND_PID 2>/dev/null
    fi
    
    if [ -n "$BACKEND_PID" ]; then
        echo "Stopping backend (PID: $BACKEND_PID)..."
        kill $BACKEND_PID 2>/dev/null || kill -9 $BACKEND_PID 2>/dev/null
    fi
    
    # Additional cleanup to ensure all related processes are stopped
    pkill -f "node.*react-scripts" 2>/dev/null
    pkill -f "python.*uvicorn" 2>/dev/null
    
    echo "All servers stopped."
    exit 0
}

# Set up trap to catch interruptions (Ctrl+C) and call cleanup
trap cleanup INT TERM

# Start the backend server in the background with output redirected to terminal
echo "Starting backend server..."
cd backend

# Clean up any previous log file
rm -f backend.log

# Start the backend using run.sh but redirect output to backend.log and run in background
(PYTHONUNBUFFERED=1 ./run.sh > backend.log 2>&1) &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"
echo "API Documentation available at: http://localhost:5000/api/docs"

# Show backend logs in real-time
echo "Displaying backend logs:"
tail -f backend.log &
TAIL_PID=$!

# Give the backend a moment to start
sleep 2

# Start the frontend server (also in background so we can monitor both)
echo "Starting frontend server..."
cd ../curiosity-coach-frontend
npm start &
FRONTEND_PID=$!
echo "Frontend started with PID: $FRONTEND_PID"

echo "Both servers are now running."
echo "Press Ctrl+C to stop both servers."
echo "Backend logs will be shown below."
echo "-------------------------------"

# Wait for either process to exit
wait $FRONTEND_PID $BACKEND_PID

# If we get here, one of the processes exited on its own
echo "One of the servers has stopped. Shutting down all servers..."
cleanup 