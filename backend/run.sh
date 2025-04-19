#!/bin/bash

# Set environment to development
export FLASK_ENV=development

# Check if venv exists, if not create it
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Create the database if it doesn't exist
echo "Checking database..."
PGPASSWORD=$DB_PASSWORD psql -U postgres -h localhost -c "SELECT 1 FROM pg_database WHERE datname = 'curiosity_coach'" | grep -q 1
if [ $? -ne 0 ]; then
    echo "Creating database 'curiosity_coach'..."
    PGPASSWORD=$DB_PASSWORD psql -U postgres -h localhost -c "CREATE DATABASE curiosity_coach"
fi

# Run the Flask app
echo "Starting Flask server..."
python app.py 