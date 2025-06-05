locals {
  # Derive resource names from the app_name variable if specific names are not provided
  ecr_repo_name      = coalesce(var.ecr_repo_name, "${var.app_name}-repo")
  lambda_function_name = coalesce(var.lambda_function_name, "${var.app_name}-lambda")
  tags = {
    Project = var.app_name
    ManagedBy = "Terraform"
  }
}

# --- ECR Repository --- 
resource "aws_ecr_repository" "app_repo" {
  name                 = local.ecr_repo_name
  image_tag_mutability = "MUTABLE" # Or IMMUTABLE if preferred
  force_delete         = true # Added to allow deletion of non-empty repo

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.tags
}

# --- IAM Role for Lambda --- 
resource "aws_iam_role" "lambda_exec_role" {
  name = "${local.lambda_function_name}-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Sid    = ""
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      },
    ]
  })

  tags = local.tags
}

resource "aws_iam_role_policy_attachment" "lambda_policy_basic" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Policy allowing Lambda to interact with the SQS queue
resource "aws_iam_policy" "lambda_sqs_policy" {
  name        = "${local.lambda_function_name}-sqs-policy"
  description = "IAM policy for Lambda to interact with SQS queue"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "sqs:ReceiveMessage",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes"
        ]
        Effect   = "Allow"
        Resource = aws_sqs_queue.app_queue.arn # Grant access only to this specific queue
      },
    ]
  })

  tags = local.tags
}

# Attach the SQS policy to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_sqs_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_sqs_policy.arn
}

# --- S3 Bucket for Flow Configuration (Optional: Creates if name not provided) ---
resource "aws_s3_bucket" "flow_config_bucket" {

  bucket = "${var.flow_config_s3_bucket_name}"
  force_destroy = true
  # ACL no longer recommended, use bucket policies for fine-grained control if needed beyond Lambda access
  # acl    = "private" # This is deprecated for new buckets

  tags = merge(local.tags, {
    Name = "${local.lambda_function_name}-flow-config"
  })
}

resource "aws_s3_bucket_ownership_controls" "flow_config_bucket_ownership" {
  bucket = aws_s3_bucket.flow_config_bucket.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "flow_config_bucket_public_access" {
  bucket = aws_s3_bucket.flow_config_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Determine the bucket name to use: either the newly created one or the provided one
locals {
  actual_flow_config_s3_bucket_name = var.flow_config_s3_bucket_name
}

# IAM Policy for Lambda to access S3 flow config
resource "aws_iam_policy" "lambda_s3_config_policy" {
  name        = "${local.lambda_function_name}-s3-config-policy"
  description = "IAM policy for Lambda to read flow configuration from S3"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:GetObject"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:s3:::${local.actual_flow_config_s3_bucket_name}/${var.flow_config_s3_key}" # Specific object access
      },
      {
        # Optional: If you want to allow listing the bucket to check existence (though the app currently doesn't do this, might be useful for debugging)
        Action = ["s3:ListBucket"]
        Effect = "Allow"
        Resource = "arn:aws:s3:::${local.actual_flow_config_s3_bucket_name}"
      }
    ]
  })

  tags = local.tags
}

# Attach the S3 config policy to the Lambda role
resource "aws_iam_role_policy_attachment" "lambda_s3_config_attachment" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_s3_config_policy.arn
}

# Add other policy attachments if your lambda needs more permissions (e.g., S3, DynamoDB)

# --- Docker Build & Push --- 
resource "null_resource" "docker_build_push" {
  # Triggers re-build/push if source files or Dockerfile change
  triggers = {
    # Calculate a hash based on all .py files in the src directory
    # This ensures changes in any .py file trigger a rebuild.
    src_files_hash = sha1(join("", [
      for f in fileset("${path.module}/../Brain/src", "**/*") : filesha1("${path.module}/../Brain/src/${f}")
    ]))
    requirements_hash = filemd5("${path.module}/../Brain/requirements.txt")
    dockerfile_hash   = filemd5("${path.module}/../Brain/Dockerfile")
  }

  provisioner "local-exec" {
    command = <<EOF
      # set -e # Temporarily removed for better error reporting
      echo "Setting AWS Profile for Brain..."
      export AWS_PROFILE=${var.aws_profile}

      echo "Logging into ECR for ${aws_ecr_repository.app_repo.name}..."
      # Attempt login and capture output/error
      login_output=$(aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com 2>&1)
      login_exit_code=$?
      # Check if login failed
      if [ $login_exit_code -ne 0 ]; then
        # Check if the failure was the specific keychain error
        if echo "$login_output" | grep -q "The specified item already exists in the keychain"; then
          echo "Docker login skipped: Credentials already exist in keychain."
        else
          # If it was a different error, print the error and exit
          echo "Docker login failed:" >&2
          echo "$login_output" >&2
          exit $login_exit_code
        fi
      else
        echo "Docker login successful or skipped."
      fi

      echo "Building Brain Docker image ${aws_ecr_repository.app_repo.repository_url}:${var.docker_image_tag}..."
      # Ensure Dockerfile path and build context are correct
      docker build --platform linux/amd64 -t ${aws_ecr_repository.app_repo.repository_url}:${var.docker_image_tag} -f ${path.module}/../Brain/Dockerfile ${path.module}/../Brain
      build_exit_code=$?
      if [ $build_exit_code -ne 0 ]; then
        echo "Docker build failed with exit code $build_exit_code" >&2
        exit $build_exit_code
      fi

      echo "Pushing Brain Docker image ${aws_ecr_repository.app_repo.repository_url}:${var.docker_image_tag}..."
      docker push ${aws_ecr_repository.app_repo.repository_url}:${var.docker_image_tag}
      push_exit_code=$?
      if [ $push_exit_code -ne 0 ]; then
        echo "Docker push failed with exit code $push_exit_code" >&2
        exit $push_exit_code
      fi

      echo "Brain Docker build and push completed successfully."
    EOF
  }

  depends_on = [aws_ecr_repository.app_repo]
}

# --- ECR Image Data Source --- 
# Reads the digest of the image pushed by the null_resource
data "aws_ecr_image" "latest_app_image" {
  repository_name = aws_ecr_repository.app_repo.name
  image_tag       = var.docker_image_tag # Use the same tag as build/push

  depends_on = [
    null_resource.docker_build_push # Ensure this runs after the push completes
  ]
}

# --- External Data Source for .env.prod ---
data "external" "dotenv_prod" {
  program = ["python3", "${path.module}/parse_env.py"]

  # Pass the path to the .env.prod file as JSON input to the script
  # Also pass the timestamp to ensure the data source is re-evaluated on every apply
  query = {
    # Path relative to the terraform directory
    dotenv_path    = "${path.module}/../Brain/src/.env.prod"
    # This dummy timestamp ensures the query changes on each run, forcing re-evaluation
    _rerun_trigger = timestamp()
  }
}

# --- Lambda Function (using Docker Image) --- 
# Note: This assumes the Docker image has been built and pushed to ECR separately.
# Terraform will use the image URI provided.
resource "aws_lambda_function" "app_lambda" {
  function_name = local.lambda_function_name
  role          = aws_iam_role.lambda_exec_role.arn
  package_type  = "Image"

  # Use the specific image digest from the data source to ensure updates
  image_uri = "${aws_ecr_repository.app_repo.repository_url}@${data.aws_ecr_image.latest_app_image.image_digest}"

  # Removed source_code_hash as image_uri with digest handles updates for container images

  timeout     = 300 # Adjust as needed
  memory_size = 2048 # Adjust as needed

  # Optional: Define environment variables for the Lambda function
  environment {
    # Use the parsed variables from the external data source
    variables = merge(data.external.dotenv_prod.result, {
      FLOW_CONFIG_S3_BUCKET_NAME = local.actual_flow_config_s3_bucket_name
      FLOW_CONFIG_S3_KEY         = var.flow_config_s3_key
    })
  }

  tags = local.tags

  depends_on = [
    aws_iam_role_policy_attachment.lambda_policy_basic,
    aws_iam_role_policy_attachment.lambda_sqs_attachment, # Ensure policy is attached before lambda creation/update
    aws_iam_role_policy_attachment.lambda_s3_config_attachment, # Ensure S3 config policy is attached
    null_resource.docker_build_push # Ensure lambda is created/updated after image push
  ]
}

# --- SQS Queue ---
resource "aws_sqs_queue" "app_queue" {
  name                        = "${local.lambda_function_name}-queue" # Name based on lambda name
  delay_seconds               = 0
  max_message_size            = 262144 # 256 KiB
  message_retention_seconds   = 86400  # 1 day, adjust as needed
  receive_wait_time_seconds   = 10     # Enable long polling
  visibility_timeout_seconds  = 360    # Lambda timeout (300s) + buffer (60s)

  tags = local.tags
}

# --- Lambda SQS Trigger ---
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.app_queue.arn
  function_name    = aws_lambda_function.app_lambda.arn
  batch_size       = 1 # Process one message at a time, adjust if needed

  depends_on = [
      aws_lambda_function.app_lambda, 
      aws_sqs_queue.app_queue,
      aws_iam_role_policy_attachment.lambda_sqs_attachment # Ensure role has SQS permissions before mapping
  ]
}

# --- Lambda Function URL --- 
resource "aws_lambda_function_url" "app_lambda_url" {
  function_name      = aws_lambda_function.app_lambda.function_name
  authorization_type = "NONE" # Changed to NONE for public access

}

# Grant invoke permission because authorization_type is NONE
resource "aws_lambda_permission" "allow_public_access" {
  action        = "lambda:InvokeFunctionUrl"
  function_name = aws_lambda_function.app_lambda.function_name
  principal     = "*"
  function_url_auth_type = "NONE"
} 