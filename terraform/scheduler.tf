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
    aws_apigatewayv2_api.backend_api
  ]
}

# Rule for Memory Generation
resource "aws_cloudwatch_event_rule" "memory_generation_rule" {
  name                = "${var.project_name}-memory-generation-rule-${var.environment}"
  description         = "Fires every 3 hours to trigger memory generation"
  schedule_expression = "rate(3 hours)"
}

resource "aws_cloudwatch_event_target" "memory_generation_target" {
  rule  = aws_cloudwatch_event_rule.memory_generation_rule.name
  arn   = aws_lambda_function.scheduler_lambda.arn
  input = jsonencode({
    "task" : "memory_generation"
  })
}

resource "aws_lambda_permission" "allow_eventbridge_to_call_for_memory" {
  statement_id  = "AllowEventBridgeInvokeMemory"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.memory_generation_rule.arn
}

# Rule for User Persona Generation
resource "aws_cloudwatch_event_rule" "user_persona_generation_rule" {
  name                = "${var.project_name}-user-persona-generation-rule-${var.environment}"
  description         = "Fires every 4 hours to trigger user persona generation"
  schedule_expression = "rate(4 hours)"
}

resource "aws_cloudwatch_event_target" "user_persona_generation_target" {
  rule  = aws_cloudwatch_event_rule.user_persona_generation_rule.name
  arn   = aws_lambda_function.scheduler_lambda.arn
  input = jsonencode({
    "task" : "persona_generation"
  })
}

resource "aws_lambda_permission" "allow_eventbridge_to_call_for_persona" {
  statement_id  = "AllowEventBridgeInvokePersona"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scheduler_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.user_persona_generation_rule.arn
} 