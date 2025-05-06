# Use an official AWS Lambda Python runtime base image
FROM public.ecr.aws/lambda/python:3.11

# Set the working directory in the container
WORKDIR ${LAMBDA_TASK_ROOT}

# Copy requirements.txt first to leverage Docker layer caching
COPY requirements.txt .

# Install dependencies
# Using --no-cache-dir makes the image smaller
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire src directory contents into the container
# Adjust if your code dependencies are outside 'src'
COPY src/ ${LAMBDA_TASK_ROOT}/src/

# Copy the config directory contents into the container
COPY config/ ${LAMBDA_TASK_ROOT}/config/

# Set the command for Lambda to execute the handler
# Format is <module_path>.<handler_function_name>
CMD ["src.lambda_function.lambda_handler"] 