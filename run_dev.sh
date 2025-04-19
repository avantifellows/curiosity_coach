#!/bin/bash

# Start the backend server in the background
echo "Starting backend server..."
cd backend
./run.sh &
BACKEND_PID=$!

# Give the backend a moment to start
sleep 2

# Start the frontend server
echo "Starting frontend server..."
cd ../curiosity-coach-frontend
npm start

# When the frontend is terminated, also terminate the backend
kill $BACKEND_PID 