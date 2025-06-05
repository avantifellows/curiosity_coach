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
  description = "The URL to invoke the Lambda function."
  value       = aws_lambda_function_url.app_lambda_url.function_url
}

output "lambda_iam_role_arn" {
  description = "The ARN of the IAM role created for the Lambda function."
  value       = aws_iam_role.lambda_exec_role.arn
}

output "sqs_queue_url" {
  description = "The URL of the SQS queue."
  value       = aws_sqs_queue.app_queue.id # .id gives the URL
}

output "sqs_queue_arn" {
  description = "The ARN of the SQS queue."
  value       = aws_sqs_queue.app_queue.arn
}

output "cloudfront_distribution_id" {
  description = "The ID of the CloudFront distribution for the frontend."
  value       = aws_cloudfront_distribution.frontend_distribution.id
} 