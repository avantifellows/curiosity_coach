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
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
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

# --- Removed Default VPC/Subnet Data Sources ---
# data "aws_vpc" "default" {
#   default = true
# }
# data "aws_subnets" "default" {
#   filter {
#     name   = "vpc-id"
#     values = [data.aws_vpc.default.id]
#   }
# }

# --- Added Specific VPC Data Source ---
data "aws_vpc" "selected" {
  id = "vpc-0a25a54c34b446c2d" # The VPC ID we identified
}

# --- Data source to find private subnets ---
data "aws_subnets" "private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.selected.id]
  }
  filter {
    name   = "tag:aws-cdk:subnet-type"
    values = ["Private"]
  }
}

# --- Define the Public Subnet IDs ---
# Identified public subnets in vpc-0a25a54c34b446c2d
locals {
  public_subnet_ids = [
    "subnet-08bdce0ea3ad1826e", # ap-south-1a
    "subnet-017c528c08e874a5f"  # ap-south-1b
  ]
  private_subnet_ids = data.aws_subnets.private.ids

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

  # When create_rds_instance is true, use the new RDS instance's details.
  # Otherwise, use the data source for the existing RDS instance.
  rds_details = {
    address   = var.create_rds_instance ? aws_db_instance.rds_instance[0].address : data.aws_db_instance.existing_rds[0].address
    port      = var.create_rds_instance ? aws_db_instance.rds_instance[0].port : data.aws_db_instance.existing_rds[0].port
    db_name   = var.create_rds_instance ? aws_db_instance.rds_instance[0].db_name : (var.existing_rds_db_name != "" ? var.existing_rds_db_name : data.aws_db_instance.existing_rds[0].db_name)
    username  = var.create_rds_instance ? aws_db_instance.rds_instance[0].username : var.existing_rds_username
    password  = var.create_rds_instance ? random_password.db_password[0].result : var.existing_rds_password
  }
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

# Define policy for SQS SendMessage
data "aws_iam_policy_document" "backend_lambda_sqs_send_policy_doc" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.app_queue.arn] # Reference the queue ARN from the variable
    effect    = "Allow"
  }
}

resource "aws_iam_policy" "backend_lambda_sqs_send_policy" {
  name        = "${local.backend_lambda_func_name}-sqs-send-policy"
  description = "Allow backend lambda to send messages to the SQS queue"
  policy      = data.aws_iam_policy_document.backend_lambda_sqs_send_policy_doc.json
}

# Attach the new SQS policy
resource "aws_iam_role_policy_attachment" "backend_lambda_policy_sqs_send" {
  role       = aws_iam_role.backend_lambda_exec_role.name
  policy_arn = aws_iam_policy.backend_lambda_sqs_send_policy.arn
}

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
  vpc_id      = data.aws_vpc.selected.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" # All protocols
    cidr_blocks = ["0.0.0.0/0"]
  }

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.backend_tags, { Name = "${local.backend_lambda_func_name}-sg" })
}


# --- Security Group for RDS ---
resource "aws_security_group" "rds_sg" {
  name        = "${local.rds_instance_identifier}-sg"
  description = "Allow access to RDS instance"
  vpc_id      = data.aws_vpc.selected.id

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

# --- NAT Gateway for Private Subnet Egress ---

# Allocate an Elastic IP for the NAT Gateway
resource "aws_eip" "nat" {
  domain = "vpc"

  tags = merge(local.backend_tags, { Name = "${local.backend_prefix}-nat-eip" })
}

# Create the NAT Gateway in a public subnet
resource "aws_nat_gateway" "nat" {
  allocation_id = aws_eip.nat.id
  # NAT Gateway must be in a public subnet to have a route to the Internet Gateway.
  # We'll place it in the first public subnet from our list.
  subnet_id = local.public_subnet_ids[0]

  tags = merge(local.backend_tags, { Name = "${local.backend_prefix}-nat-gw" })

  # Explicit dependency on the Internet Gateway being available,
  # though in this case the IG is part of the pre-existing VPC.
  # This is good practice if Terraform were managing the IG.
  # depends_on = [aws_internet_gateway.igw]
}

# --- Route Table for Private Subnets ---

# Create a new route table for our private subnets
resource "aws_route_table" "private" {
  vpc_id = data.aws_vpc.selected.id

  route {
    # This route directs all outbound internet traffic (0.0.0.0/0)
    # to the new NAT Gateway.
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.nat.id
  }

  tags = merge(local.backend_tags, { Name = "${local.backend_prefix}-private-rt" })
}

# Associate the new private route table with each of our private subnets
resource "aws_route_table_association" "private" {
  # Create an association for each private subnet found by our data source
  for_each = toset(local.private_subnet_ids)

  subnet_id      = each.value
  route_table_id = aws_route_table.private.id
}

# --- RDS Subnet Group ---
resource "aws_db_subnet_group" "rds_subnet_group" {
  name       = "${local.rds_instance_identifier}-subnet-group"
  subnet_ids = local.public_subnet_ids

  tags = merge(local.backend_tags, { Name = "${local.rds_instance_identifier}-subnet-group" })
}

# --- RDS Password ---
resource "random_password" "db_password" {
  count           = var.create_rds_instance ? 1 : 0
  length           = 16
}

# --- RDS Database Instance ---
resource "aws_db_instance" "rds_instance" {
  count                  = var.create_rds_instance ? 1 : 0
  identifier             = local.rds_instance_identifier
  engine                 = local.db_engine
  engine_version         = local.db_version
  instance_class         = "db.t4g.micro" # Smallest ARM instance
  allocated_storage      = 20             # Minimum storage in GB
  storage_type           = "gp3"          # General Purpose SSD v3
  db_name                = local.db_name
  username               = local.db_username
  password               = random_password.db_password[0].result
  port                   = local.db_port
  db_subnet_group_name   = aws_db_subnet_group.rds_subnet_group.name
  vpc_security_group_ids = [aws_security_group.rds_sg.id]
  publicly_accessible    = true           # Make it publicly accessible as requested
  skip_final_snapshot    = true           # Set to false in production
  apply_immediately      = true           # Apply changes immediately (useful for dev/test)

  tags = merge(local.backend_tags, { Name = local.rds_instance_identifier })

  depends_on = [aws_db_subnet_group.rds_subnet_group]
}

# --- Data source to get existing RDS instance ---
data "aws_db_instance" "existing_rds" {
  count = var.create_rds_instance ? 0 : 1
  db_instance_identifier = var.existing_rds_instance_id
}

# --- Update backend/.env.prod with RDS Details ---
/*
resource "null_resource" "update_backend_env_with_rds" {
  # Ensure this runs only after the RDS instance and password exist
  depends_on = [aws_db_instance.rds_instance, random_password.db_password]

  # Trigger re-run if RDS details change
  triggers = {
    db_address    = local.rds_details.address
    db_port       = local.rds_details.port
    db_name       = local.rds_details.db_name
    db_user       = local.rds_details.username
    db_password   = local.rds_details.password
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

  timeout     = 300 # Adjust as needed
  memory_size = 2048 # Adjust based on backend needs

  environment {
    variables = merge(
      # Load static variables from the .env.prod file first, filtering out reserved AWS keys
      {
        for k, v in data.external.backend_dotenv_prod.result : k => v
        if k != "AWS_REGION" && k != "AWS_ACCESS_KEY_ID" && k != "AWS_SECRET_ACCESS_KEY" && k != "AWS_SESSION_TOKEN" # Added AWS_SESSION_TOKEN just in case
      },
      # Then merge/overwrite with dynamic variables defined in Terraform
      {
        DB_HOST         = local.rds_details.address
        DB_PORT         = local.rds_details.port
        DB_NAME         = local.rds_details.db_name
        DB_USER         = local.rds_details.username
        DB_PASSWORD     = local.rds_details.password
        SQS_QUEUE_URL     = aws_sqs_queue.app_queue.id # Ensure brain.tf defines aws_sqs_queue.app_queue
        FRONTEND_URL      = "https://${aws_cloudfront_distribution.frontend_distribution.domain_name}"
        S3_WEBSITE_URL    = "http://${aws_s3_bucket_website_configuration.frontend_website.website_endpoint}"
        ALLOW_ALL_ORIGINS = "true" # For now, allow all origins as requested
      }
    )
  }

  # Configure VPC access for the Lambda function
  vpc_config {
    subnet_ids         = local.private_subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  tags = local.backend_tags

  depends_on = [
    aws_iam_role_policy_attachment.backend_lambda_policy_basic_execution,
    aws_iam_role_policy_attachment.backend_lambda_policy_vpc_access,
    aws_iam_role_policy_attachment.backend_lambda_policy_sqs_send,
    null_resource.backend_docker_build_push,
    aws_sqs_queue.app_queue,
    aws_security_group.lambda_sg,
    data.external.backend_dotenv_prod,
    aws_cloudfront_distribution.frontend_distribution,
    aws_s3_bucket_website_configuration.frontend_website
  ]
}

# --- Backend Lambda Function URL ---
resource "aws_lambda_function_url" "backend_lambda_url" {
  function_name      = aws_lambda_function.backend_lambda.function_name
  authorization_type = "NONE" # Public access

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
  value       = local.rds_details.address
}

output "rds_instance_port" {
  description = "The port the RDS instance is listening on"
  value       = local.rds_details.port
}

output "rds_database_name" {
  description = "The name of the database created in the RDS instance"
  value       = local.rds_details.db_name
}

output "rds_database_user" {
  description = "The username for the database"
  value       = local.rds_details.username
}

output "rds_database_password" {
  description = "The password for the database"
  value       = local.rds_details.password
  sensitive   = true
}


# --- TODOs & Next Steps ---
# 1. Review Security Groups: **Crucially**, restrict `aws_security_group.rds_sg` ingress `cidr_blocks = ["0.0.0.0/0"]` in production. Only allow necessary IPs (e.g., specific developer IPs, Bastion host SG). The Lambda access via its SG is already configured more securely.
# 2. CORS Origins: Update `

# --- Security Group for SQS VPC Endpoint ---
resource "aws_security_group" "sqs_vpce_sg" {
  count  = var.create_vpc_endpoints ? 1 : 0
  name        = "${local.backend_prefix}-sqs-vpce-sg"
  description = "Allow inbound HTTPS from Lambda SG to SQS VPC Endpoint"
  vpc_id      = data.aws_vpc.selected.id

  ingress {
    description     = "Allow HTTPS from Lambda"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id] # Allow from Lambda SG
  }

  # Egress is typically not needed for interface endpoints unless specific requirements exist
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.backend_tags, { Name = "${local.backend_prefix}-sqs-vpce-sg" })
}

resource "aws_vpc_endpoint" "sqs_endpoint" {
  count = var.create_vpc_endpoints ? 1 : 0
  vpc_id              = data.aws_vpc.selected.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.sqs"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.sqs_vpce_sg[0].id]
  subnet_ids          = local.private_subnet_ids

  tags = merge(local.backend_tags, { Name = "${local.backend_prefix}-sqs-vpce" })
}

# --- Security Group for STS VPC Endpoint ---
resource "aws_security_group" "sts_vpce_sg" {
  count = var.create_vpc_endpoints ? 1 : 0
  name        = "${local.backend_prefix}-sts-vpce-sg"
  description = "Allow inbound HTTPS from Lambda SG to STS VPC Endpoint"
  vpc_id      = data.aws_vpc.selected.id

  ingress {
    description     = "Allow HTTPS from Lambda"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.lambda_sg.id] # Allow from Lambda SG
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(local.backend_tags, { Name = "${local.backend_prefix}-sts-vpce-sg" })
}

# --- STS VPC Endpoint ---
resource "aws_vpc_endpoint" "sts_endpoint" {
  count = var.create_vpc_endpoints ? 1 : 0
  vpc_id              = data.aws_vpc.selected.id
  service_name        = "com.amazonaws.${data.aws_region.current.name}.sts"
  vpc_endpoint_type   = "Interface"
  private_dns_enabled = true
  security_group_ids  = [aws_security_group.sts_vpce_sg[0].id]
  subnet_ids          = local.private_subnet_ids

  tags = merge(local.backend_tags, { Name = "${local.backend_prefix}-sts-vpce" })
}