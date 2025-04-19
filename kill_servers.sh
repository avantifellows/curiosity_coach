#!/bin/bash

echo "Stopping Curiosity Coach servers..."

# Kill the Node.js frontend process
echo "Stopping React frontend..."
pkill -f "node.*react-scripts"

# Kill the Python backend process
echo "Stopping Flask backend..."
pkill -f "python.*app.py"

# Check if processes were killed successfully
if pgrep -f "node.*react-scripts" > /dev/null; then
    echo "Warning: Frontend server still running. Attempting to force kill..."
    pkill -9 -f "node.*react-scripts"
fi

if pgrep -f "python.*app.py" > /dev/null; then
    echo "Warning: Backend server still running. Attempting to force kill..."
    pkill -9 -f "python.*app.py"
fi

# Final check
if pgrep -f "node.*react-scripts" > /dev/null || pgrep -f "python.*app.py" > /dev/null; then
    echo "Error: Some servers could not be stopped. Try running the following commands manually:"
    echo "  pkill -9 -f \"node.*react-scripts\""
    echo "  pkill -9 -f \"python.*app.py\""
    exit 1
else
    echo "All servers stopped successfully."
    exit 0
fi 