# Dockerfile for the Backend FastAPI application running with Mangum on Lambda

# Use an official Python runtime as a parent image
FROM python:3.9-slim as base

# Set environment variables to prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if needed (e.g., for psycopg2-binary)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gcc \
#     libpq-dev \
#  && rm -rf /var/lib/apt/lists/*

# --- Dependencies Stage ---
FROM base as dependencies

# Copy the lock file
COPY requirements.lock .

# Upgrade pip, install uv, and install dependencies from lock file using uv
RUN pip install --upgrade pip \
    && pip install uv \
    && uv pip install --system --no-cache-dir -r requirements.lock

# --- Application Stage ---
FROM dependencies as application

# Copy the application source code
COPY src/ ./src

# Specify the command to run on container start using Mangum
# This assumes your FastAPI app instance is named 'app' in 'src/main.py'
CMD ["mangum.main.handle", "src.main:app"] 