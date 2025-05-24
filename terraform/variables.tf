variable "project_name" {
  description = "The overall project name used for resource naming and tagging."
  type        = string
  default     = "curiosity-coach" 
}

variable "environment" {
  description = "The deployment environment (e.g., dev, staging, prod)."
  type        = string
  default     = "dev" # Defaulting to 'dev', change as needed
}

variable "aws_region" {
  description = "The AWS region to deploy resources in."
  type        = string
  default     = "ap-south-1" 
}

variable "app_name" {
  description = "A name prefix for resources (e.g., ECR repository, Lambda function)."
  type        = string
  default     = "curiosity-coach-brain" 
}

variable "ecr_repo_name" {
  description = "The name of the ECR repository."
  type        = string
  default     = "curiosity-coach-brain-ecr"
}

variable "lambda_function_name" {
  description = "The name of the Lambda function."
  type        = string
  default     = "curiosity-coach-brain-lambda"
}

variable "docker_image_tag" {
  description = "The tag for the Docker image in ECR (e.g., 'latest' or a specific version)."
  type        = string
  default     = "latest"
}

variable "aws_profile" {
  description = "AWS profile to use for CLI commands during Docker push."
  type        = string
  default     = "deepansh-af" # Or leave empty to prompt/use environment default
}

variable "flow_config_s3_bucket_name" {
  description = "The name of the S3 bucket to store flow_config.json. If not provided, a new bucket will be created."
  type        = string
  default     = "111766607077-curiosity-coach-flow-config" # If empty, a new bucket will be created by Terraform
}

variable "flow_config_s3_key" {
  description = "The S3 object key for the flow configuration JSON file."
  type        = string
  default     = "flow_config.json"
}

# Default values for ecr_repo_name and lambda_function_name are set in locals block in main.tf
# to use the app_name variable for consistency. 

# --- Cloudflare Configuration Variables ---
variable "cloudflare_email" {
  description = "The Cloudflare email address for account authentication."
  type        = string
  sensitive   = true
  default     = "" # Will be provided via .tfvars or environment variable
}

variable "cloudflare_api_key" {
  description = "The Cloudflare Global API Key for account authentication."
  type        = string
  sensitive   = true
  default     = "" # Will be provided via .tfvars or environment variable
}

variable "cloudflare_domain_name" {
  description = "The base domain name managed by Cloudflare (e.g., avantifellows.org)."
  type        = string
  default     = "" # Will be provided via .tfvars or environment variable
}

variable "cloudflare_subdomain" {
  description = "The subdomain to create for the frontend (e.g., 'cc' for cc.example.com)."
  type        = string
  default     = "cc"
}

# --- SSL Certificate Configuration ---
variable "acm_certificate_arn" {
  description = "The ARN of the SSL certificate in AWS Certificate Manager (must be in us-east-1 region for CloudFront)."
  type        = string
  default     = "" # Will be provided via .tfvars or environment variable
} 