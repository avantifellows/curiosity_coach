# terraform/backend.tf - Infrastructure for the Backend Service (Lambda + Function URL) + RDS

# Use variables defined in variables.tf
# variable "prefix" { ... } # Removed, will use locals based on project/env
# variable "common_tags" { ... } # Removed, will use locals

# Required providers and AWS provider configuration should be in a central file (e.g., providers.tf or main.tf)
# Ensure these are configured correctly elsewhere.

# Add the random provider for password generation
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.96.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
    # Keep other providers if needed
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# Fetch default VPC and Subnets for RDS and Lambda placement
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

locals {
  # Derive resource names consistently
  backend_prefix           = "${var.project_name}-backend-${var.environment}"
  backend_ecr_repo_name    = "${local.backend_prefix}-ecr"
  backend_lambda_func_name = "${local.backend_prefix}-lambda"
  rds_instance_identifier  = "${local.backend_prefix}-rds"
  backend_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      Component   = "backend"
      ManagedBy   = "Terraform"
    },
    # var.common_tags # If you have additional common tags defined elsewhere
  )
  # Define DB settings - use variables for production if preferred
  db_port     = 5432
  db_engine   = "postgres"
  db_version  = "14" # Choose a suitable recent version
  db_username = "dbadmin"
  db_name     = "${replace(var.project_name, "-", "_")}_${var.environment}" # Ensure valid DB name format
}

# --- ECR Repository for Backend ---
resource "aws_ecr_repository" "backend_repo" {
  name                 = local.backend_ecr_repo_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true # Allows deletion of non-empty repo during destroy

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.backend_tags
}

# --- IAM Role for Backend Lambda ---
resource "aws_iam_role" "backend_lambda_exec_role" {
  name = "${local.backend_lambda_func_name}-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = local.backend_tags
}

# Basic execution role + VPC access role
resource "aws_iam_role_policy_attachment" "backend_lambda_policy_basic_execution" {
  role       = aws_iam_role.backend_lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "backend_lambda_policy_vpc_access" {
  role       = aws_iam_role.backend_lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# --- TODO: Add specific IAM policies if backend needs access to other AWS services (e.g., S3, Secrets Manager) ---
# Note: Standard DB connection doesn't typically require extra IAM policies unless using IAM DB Auth.


# --- Docker Build & Push for Backend ---
resource "null_resource" "backend_docker_build_push" {
  # Triggers re-build/push if source files or Dockerfile change
  triggers = {
    # Assuming standard structure, adjust glob patterns if needed
    src_files_hash = sha1(join("", [
      for f in fileset("${path.module}/../backend/src", "**/*.py") : filesha1("${path.module}/../backend/src/${f}")
    ]))
    requirements_hash = filemd5("${path.module}/../backend/requirements.lock") # Assumes requirements.lock exists
    dockerfile_hash   = filemd5("${path.module}/../backend/Dockerfile")      # Assumes Dockerfile exists
  }

  provisioner "local-exec" {
    # Command runs in the terraform directory context
    command = <<EOF
      # set -e # Temporarily removed for better error reporting
      echo "Setting AWS Profile for Backend..."
      export AWS_PROFILE=${var.aws_profile}

      echo "Logging into ECR for ${aws_ecr_repository.backend_repo.name}..."
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

      echo "Building Backend Docker image ${aws_ecr_repository.backend_repo.repository_url}:${var.docker_image_tag}..."
      # Ensure Dockerfile path and build context are correct
      docker build --platform linux/amd64 -t ${aws_ecr_repository.backend_repo.repository_url}:${var.docker_image_tag} -f ${path.module}/../backend/Dockerfile ${path.module}/../backend
      build_exit_code=$?
      if [ $build_exit_code -ne 0 ]; then
        echo "Docker build failed with exit code $build_exit_code" >&2
        exit $build_exit_code
      fi

      echo "Pushing Backend Docker image ${aws_ecr_repository.backend_repo.repository_url}:${var.docker_image_tag}..."
      docker push ${aws_ecr_repository.backend_repo.repository_url}:${var.docker_image_tag}
      push_exit_code=$?
      if [ $push_exit_code -ne 0 ]; then
        echo "Docker push failed with exit code $push_exit_code" >&2
        exit $push_exit_code
      fi

      echo "Backend Docker build and push completed successfully."
    EOF
  }

  depends_on = [aws_ecr_repository.backend_repo]
}

# --- ECR Image Data Source for Backend ---
data "aws_ecr_image" "latest_backend_image" {
  repository_name = aws_ecr_repository.backend_repo.name
  image_tag       = var.docker_image_tag # Use the same tag as build/push

  depends_on = [
    null_resource.backend_docker_build_push # Ensure this runs after the push completes
  ]
}

# --- External Data Source for Backend .env.prod ---
data "external" "backend_dotenv_prod" {
  program = ["python3", "${path.module}/parse_env.py"] # Assuming the script is in the terraform directory

  query = {
    # Path relative to the terraform directory
    dotenv_path    = "${path.module}/../backend/.env.prod"
    # Ensure re-evaluation on apply
    _rerun_trigger = timestamp()
  }

  # No explicit depends_on needed here, it reads the file as-is at plan/apply time
  # It does NOT depend on the null_resource that used to update the file.
}

# --- Security Group for Lambda ---
resource "aws_security_group" "lambda_sg" {
  name        = "${local.backend_lambda_func_name}-sg"
  description = "Allow all outbound traffic for Lambda, control inbound via other SGs"
  vpc_id      = data.aws_vpc.default.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" # All protocols
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.backend_tags, { Name = "${local.backend_lambda_func_name}-sg" })
}


# --- Security Group for RDS ---
resource "aws_security_group" "rds_sg" {
  name        = "${local.rds_instance_identifier}-sg"
  description = "Allow access to RDS instance"
  vpc_id      = data.aws_vpc.default.id

  # Allow Public Access (temporary, restrict in production)
  ingress {
    description = "Allow PostgreSQL access from anywhere (Public)"
    from_port   = local.db_port
    to_port     = local.db_port
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # WARNING: Insecure, restrict to specific IPs or Bastion host
  }

  # Allow access from Lambda
  ingress {
    description     = "Allow PostgreSQL access from Lambda SG"
    from_port       = local.db_port
    to_port         = local.db_port
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id] # Allow from Lambda SG
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" # Allow all outbound traffic
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.backend_tags, { Name = "${local.rds_instance_identifier}-sg" })
}

# --- RDS Subnet Group ---
resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "${local.rds_instance_identifier}-subnet-group"
  subnet_ids = data.aws_subnets.default.ids # Use subnets from the default VPC

  tags = merge(local.backend_tags, { Name = "${local.rds_instance_identifier}-subnet-group" })
}

# --- RDS Password ---
resource "random_password" "db_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# --- RDS Database Instance ---
resource "aws_db_instance" "rds_instance" {
  identifier             = local.rds_instance_identifier
  engine                 = local.db_engine
  engine_version         = local.db_version
  instance_class         = "db.t4g.micro" # Smallest ARM instance
  allocated_storage      = 20             # Minimum storage in GB
  storage_type           = "gp3"          # General Purpose SSD v3
  db_name                = local.db_name
  username               = local.db_username
  password               = random_password.db_password.result
  port                   = local.db_port
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  publicly_accessible    = true           # Make it publicly accessible as requested
  skip_final_snapshot    = true           # Set to false in production
  apply_immediately      = true           # Apply changes immediately (useful for dev/test)

  tags = merge(local.backend_tags, { Name = local.rds_instance_identifier })

  depends_on = [aws_db_subnet_group.rds_subnet_group]
}

# --- Update backend/.env.prod with RDS Details ---
/*
resource "null_resource" "update_backend_env_with_rds" {
  # Ensure this runs only after the RDS instance and password exist
  depends_on = [aws_db_instance.rds_instance, random_password.db_password]

  # Trigger re-run if RDS details change
  triggers = {
    db_address    = aws_db_instance.rds_instance.address
    db_port       = aws_db_instance.rds_instance.port
    db_name       = aws_db_instance.rds_instance.db_name
    db_user       = aws_db_instance.rds_instance.username
    db_password   = random_password.db_password.result
    # Ensure path is relative to the terraform directory
    env_file_path = "${path.module}/../backend/.env.prod"
  }

  provisioner "local-exec" {
    # Use sed to replace the DB_* lines in the .env.prod file
    # Uses '#' as the sed delimiter to avoid issues with special characters.
    # The -i '' option modifies the file in place without a backup (macOS compatible).
    # It's crucial that ../backend/.env.prod exists before terraform apply.
    command = <<EOF
      set -e
      ENV_FILE="${self.triggers.env_file_path}"
      # Check if file exists before attempting to modify
      if [ ! -f "$ENV_FILE" ]; then
        echo "Error: Environment file $ENV_FILE not found. Cannot update RDS details." >&2
        exit 1
      fi
      echo "Updating RDS details in $ENV_FILE..."

      # Escape function for sed replacement string
      escape_sed_replacement() {
        printf '%s\n' "$1" | sed -e 's/[&\/]/\\&/g'
      }

      DB_ADDRESS_ESC=$(escape_sed_replacement "${self.triggers.db_address}")
      DB_PORT_ESC=$(escape_sed_replacement "${self.triggers.db_port}")
      DB_NAME_ESC=$(escape_sed_replacement "${self.triggers.db_name}")
      DB_USER_ESC=$(escape_sed_replacement "${self.triggers.db_user}")
      DB_PASSWORD_ESC=$(escape_sed_replacement "${self.triggers.db_password}")

      # Use grep to check if keys exist before using sed, prevents creating keys if they dont exist
      grep -q '^DB_HOST=' "$ENV_FILE" && sed -i '' "s#^DB_HOST=.*#DB_HOST=$DB_ADDRESS_ESC#" "$ENV_FILE" || echo "DB_HOST not found in $ENV_FILE, skipping update."
      grep -q '^DB_PORT=' "$ENV_FILE" && sed -i '' "s#^DB_PORT=.*#DB_PORT=$DB_PORT_ESC#" "$ENV_FILE" || echo "DB_PORT not found in $ENV_FILE, skipping update."
      grep -q '^DB_NAME=' "$ENV_FILE" && sed -i '' "s#^DB_NAME=.*#DB_NAME=$DB_NAME_ESC#" "$ENV_FILE" || echo "DB_NAME not found in $ENV_FILE, skipping update."
      grep -q '^DB_USER=' "$ENV_FILE" && sed -i '' "s#^DB_USER=.*#DB_USER=$DB_USER_ESC#" "$ENV_FILE" || echo "DB_USER not found in $ENV_FILE, skipping update."
      grep -q '^DB_PASSWORD=' "$ENV_FILE" && sed -i '' "s#^DB_PASSWORD=.*#DB_PASSWORD=$DB_PASSWORD_ESC#" "$ENV_FILE" || echo "DB_PASSWORD not found in $ENV_FILE, skipping update."

      echo "Finished updating RDS details in $ENV_FILE."
    EOF
    interpreter = ["bash", "-c"] # Explicitly use bash
  }
}
*/


# --- Backend Lambda Function (using Docker Image) ---
resource "aws_lambda_function" "backend_lambda" {
  function_name = local.backend_lambda_func_name
  role          = aws_iam_role.backend_lambda_exec_role.arn
  package_type  = "Image"

  # Use the specific image digest from the data source
  image_uri = "${aws_ecr_repository.backend_repo.repository_url}@${data.aws_ecr_image.latest_backend_image.image_digest}"

  timeout     = 30  # Adjust as needed
  memory_size = 512 # Adjust based on backend needs

  environment {
    variables = merge(
      # Load static variables from the .env.prod file first, filtering out reserved AWS keys
      {
        for k, v in data.external.backend_dotenv_prod.result : k => v
        if k != "AWS_REGION" && k != "AWS_ACCESS_KEY_ID" && k != "AWS_SECRET_ACCESS_KEY" && k != "AWS_SESSION_TOKEN" # Added AWS_SESSION_TOKEN just in case
      },
      # Then merge/overwrite with dynamic variables defined in Terraform
      {
        DB_HOST       = aws_db_instance.rds_instance.address
        DB_PORT       = aws_db_instance.rds_instance.port
        DB_NAME       = aws_db_instance.rds_instance.db_name
        DB_USER       = aws_db_instance.rds_instance.username
        DB_PASSWORD   = random_password.db_password.result
        SQS_QUEUE_URL = aws_sqs_queue.app_queue.id # Ensure brain.tf defines aws_sqs_queue.app_queue
      }
    )
  }

  # Configure VPC access for the Lambda function
  vpc_config {
    subnet_ids         = data.aws_subnets.default.ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tags = local.backend_tags

  depends_on = [
    aws_iam_role_policy_attachment.backend_lambda_policy_basic_execution,
    aws_iam_role_policy_attachment.backend_lambda_policy_vpc_access, # Added VPC access policy
    null_resource.backend_docker_build_push, # Ensure lambda is updated after new image push
    aws_db_instance.rds_instance,            # Ensure RDS is available before Lambda starts
    aws_sqs_queue.app_queue,                 # <<< Ensure SQS Queue from brain.tf is available
    aws_security_group.lambda_sg,            # Ensure Lambda SG exists
    # data.external.backend_dotenv_prod      # Ensure .env read happens after update and before lambda creation # <<< REMOVED
    data.external.backend_dotenv_prod      # <<< Ensure lambda waits for the data source to read the env file
  ]
}

# --- Backend Lambda Function URL ---
resource "aws_lambda_function_url" "backend_lambda_url" {
  function_name      = aws_lambda_function.backend_lambda.function_name
  authorization_type = "NONE" # Public access

  cors {
    allow_credentials = true
    allow_origins     = ["*"] # IMPORTANT: Restrict this in production!
    allow_methods     = ["*"]
    allow_headers     = ["*"]
    expose_headers    = ["keep-alive", "date"]
    max_age           = 86400
  }

  depends_on = [aws_lambda_function.backend_lambda]
}

# --- Lambda Permission for Public Function URL Invocation ---
resource "aws_lambda_permission" "allow_public_backend_lambda_url" {
  statement_id           = "AllowPublicInvokeBackendFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.backend_lambda.function_name
  principal              = "*"
  function_url_auth_type = "NONE"

  depends_on = [aws_lambda_function_url.backend_lambda_url]
}


# --- Removed API Gateway Resources ---
# aws_apigatewayv2_api.backend_api
# aws_apigatewayv2_integration.backend_lambda_integration
# aws_apigatewayv2_route.backend_default_route
# aws_apigatewayv2_stage.backend_api_stage
# aws_lambda_permission.api_gateway_invoke_backend_lambda

# --- Output the Lambda Function URL ---
output "backend_lambda_function_url" {
  description = "The public invocation URL for the backend Lambda function"
  value       = aws_lambda_function_url.backend_lambda_url.function_url
}

# --- Output RDS Connection Details ---
output "rds_instance_address" {
  description = "The hostname of the RDS instance"
  value       = aws_db_instance.rds_instance.address
}

output "rds_instance_port" {
  description = "The port the RDS instance is listening on"
  value       = aws_db_instance.rds_instance.port
}

output "rds_database_name" {
  description = "The name of the database created in the RDS instance"
  value       = aws_db_instance.rds_instance.db_name
}

output "rds_database_user" {
  description = "The master username for the RDS instance"
  value       = aws_db_instance.rds_instance.username
}

output "rds_database_password" {
  description = "The generated master password for the RDS instance (store securely!)"
  value       = random_password.db_password.result
  sensitive   = true # Mark the password output as sensitive
}


# --- TODOs & Next Steps ---
# 1. Review Security Groups: **Crucially**, restrict `aws_security_group.rds_sg` ingress `cidr_blocks = ["0.0.0.0/0"]` in production. Only allow necessary IPs (e.g., specific developer IPs, Bastion host SG). The Lambda access via its SG is already configured more securely.
# 2. CORS Origins: Update `aws_lambda_function_url.cors.allow_origins` from `["*"]` to your specific frontend domain(s) for production.
# 3. Variables & Providers: Ensure `project_name`, `environment`, `aws_region`, `docker_image_tag`, `aws_profile` are defined correctly and provider configurations are centralized if needed. You will likely need to add the `random` provider to your main Terraform configuration block.
# 4. Database Schema: This Terraform code creates the RDS instance, but you'll need a separate process (e.g., using Alembic migrations triggered from your application or a setup script) to create tables within the database. Your `backend/schema.sql` might be relevant here. Ensure your application uses the environment variables (DB_HOST, DB_PORT, etc.) for its database connection.
# 5. Final Snapshot: Change `skip_final_snapshot = true` to `false` for production RDS instances.
# 6. Run `terraform init -upgrade` (to add the random provider) and `terraform apply`. Remember to handle the sensitive password output securely.
# 7. Verify Paths: Ensure `../backend/Dockerfile`, `../backend/requirements.txt`, and `../backend/src/.env.prod` paths are correct. Create these files if they don't exist.
# 8. Dockerfile: Ensure `backend/Dockerfile` correctly installs dependencies (including Mangum) and defines the `CMD` or `ENTRYPOINT` to run the FastAPI app via Mangum.
# 9. Run `terraform init` and `terraform apply`. 