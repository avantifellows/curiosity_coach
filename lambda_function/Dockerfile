FROM ghcr.io/astral-sh/uv:0.6.16 AS uv

# First, bundle the dependencies into the task root
FROM public.ecr.aws/lambda/python:3.9 AS builder

# Enable bytecode compilation, to improve cold-start performance
ENV UV_COMPILE_BYTECODE=1

# Disable installer metadata, to create a deterministic layer
ENV UV_NO_INSTALLER_METADATA=1

# Enable copy mode to support bind mount caching
ENV UV_LINK_MODE=copy

# Bundle the dependencies into the Lambda task root via `uv pip install --target`
RUN --mount=from=uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    uv pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

FROM public.ecr.aws/lambda/python:3.9

# Copy the runtime dependencies from the builder stage
COPY --from=builder ${LAMBDA_TASK_ROOT} ${LAMBDA_TASK_ROOT}

# Copy the Lambda function code
COPY lambda_function.py ${LAMBDA_TASK_ROOT}/
COPY __init__.py ${LAMBDA_TASK_ROOT}/

# Set the AWS Lambda handler
CMD ["lambda_function.lambda_handler"] 