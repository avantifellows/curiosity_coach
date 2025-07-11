output "ecr_repository_url" {
  description = "The URL of the ECR repository."
  value       = aws_ecr_repository.app_repo.repository_url
}

output "lambda_function_name" {
  description = "The name of the Lambda function."
  value       = aws_lambda_function.app_lambda.function_name
}

output "lambda_function_arn" {
  description = "The ARN of the Lambda function."
  value       = aws_lambda_function.app_lambda.arn
}

output "lambda_function_url" {
  description = "The URL for the brain lambda function"
  value       = aws_apigatewayv2_api.app_api.api_endpoint
}

output "lambda_iam_role_arn" {
  description = "The ARN of the IAM role created for the Lambda function."
  value       = aws_iam_role.lambda_exec_role.arn
}

output "sqs_queue_url" {
  description = "The URL of the SQS queue."
  value       = aws_sqs_queue.app_queue.id # .id gives the URL
}

output "cloudfront_distribution_id" {
  description = "The ID of the CloudFront distribution for the frontend."
  value       = aws_cloudfront_distribution.frontend_distribution.id
}

output "s3_website_url" {
  description = "The S3 static website endpoint URL for the frontend."
  value       = "http://${aws_s3_bucket_website_configuration.frontend_website.website_endpoint}"
  sensitive   = true
} 