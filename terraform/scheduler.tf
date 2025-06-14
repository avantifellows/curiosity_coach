# terraform/scheduler.tf

data "archive_file" "scheduler_lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/scheduler_lambda/main.py"
  output_path = "${path.module}/scheduler_lambda.zip"
}

resource "aws_iam_role" "scheduler_lambda_role" {
  name = "${var.project_name}-scheduler-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Component   = "scheduler"
  }
}

resource "aws_iam_role_policy_attachment" "scheduler_lambda_basic_execution" {
  role       = aws_iam_role.scheduler_lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "scheduler_lambda" {
  function_name = "${var.project_name}-scheduler-lambda-${var.environment}"
  role          = aws_iam_role.scheduler_lambda_role.arn
  handler       = "main.handler"
  runtime       = "python3.11"
  timeout       = 60

  filename         = data.archive_file.scheduler_lambda_zip.output_path
  source_code_hash = data.archive_file.scheduler_lambda_zip.output_base64sha256

  environment {
    variables = {
      BACKEND_BASE_URL = aws_apigatewayv2_api.backend_api.api_endpoint
    }
  }

  tags = {
    Project     = var.project_name
    Environment = var.environment
    Component   = "scheduler"
  }

  depends_on = [
    aws_iam_role.scheduler_lambda_role,
    data.archive_file.scheduler_lambda_zip,
    aws_cloudwatch_event_rule.scheduler_rule,
    aws_apigatewayv2_api.backend_api
  ]
}

resource "aws_cloudwatch_event_rule" "scheduler_rule" {
  name                = "${var.project_name}-scheduler-rule-${var.environment}"
  description         = "Fires every 10 minutes to trigger the scheduler lambda"
  schedule_expression = "rate(10 minutes)"
}

resource "aws_cloudwatch_event_target" "scheduler_target" {
  rule = aws_cloudwatch_event_rule.scheduler_rule.name
  arn  = aws_lambda_function.scheduler_lambda.arn
}

resource "aws_lambda_permission" "allow_eventbridge_to_call_scheduler" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.scheduler_rule.arn
} 