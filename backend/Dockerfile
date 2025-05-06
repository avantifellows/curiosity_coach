# Dockerfile for the Backend FastAPI application running with Mangum on Lambda

# Use an official AWS Lambda Python runtime base image
FROM public.ecr.aws/lambda/python:3.11 as base

# Set environment variables to prevent Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set the working directory in the container (standard for AWS base images)
WORKDIR ${LAMBDA_TASK_ROOT}

# Install system dependencies if needed (e.g., for psycopg2-binary)
# RUN yum update -y && yum install -y gcc postgresql-devel && yum clean all
# Note: Base image might be Amazon Linux based, use yum instead of apt-get

# --- Dependencies Stage ---
FROM base as dependencies

# Copy the lock file first to leverage Docker layer caching
COPY requirements.txt .

# Upgrade pip, install uv, and install dependencies from lock file using uv
# Using --no-cache-dir makes the image smaller
RUN pip install --upgrade pip \
    && pip install uv \
    && uv pip install --system --no-cache-dir -r requirements.txt

# --- Application Stage ---
FROM dependencies as application

# Copy the application source code into the Lambda task root
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Specify the command for Lambda to execute the handler
# This assumes your FastAPI app instance is named 'app' in 'src/main.py'
# The AWS base image's entrypoint handles invoking this correctly with Mangum.
CMD ["src.main.app"] 