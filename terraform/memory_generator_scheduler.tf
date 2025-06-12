# terraform/memory_generator_scheduler.tf

# Note: EventBridge Scheduler is the newer service, but to target an API Destination
# via Terraform, we currently still use the "aws_cloudwatch_event_*" resources.
# This setup achieves the same goal: running a target on a schedule.

# 1. IAM Role for the Event Rule to invoke the API Destination
resource "aws_iam_role" "memory_generator_event_rule_role" {
  name = "${var.app_name}-memory-generator-event-rule-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = local.tags
}

# 2. Connection for the API Destination (handles authorization)
resource "aws_cloudwatch_event_connection" "memory_generator_connection" {
  name               = "${var.app_name}-memory-generator-connection"
  authorization_type = "API_KEY"
  description        = "Connection for memory generation endpoint"

  auth_parameters {
    api_key {
      key   = "x-api-key"       # Placeholder, not used since lambda is public
      value = "placeholder-key" # Placeholder, not used
    }
  }
}

# 3. API Destination (the endpoint to call)
resource "aws_cloudwatch_event_api_destination" "memory_generator_api_destination" {
  name                             = "${var.app_name}-memory-generator-api-destination"
  description                      = "API Destination for triggering memory generation"
  connection_arn                   = aws_cloudwatch_event_connection.memory_generator_connection.arn
  invocation_endpoint              = "${aws_lambda_function_url.app_lambda_url.function_url}api/tasks/trigger-memory-generation"
  http_method                      = "POST"
  invocation_rate_limit_per_second = 1 # Limit to 1 call per second
}

# 4. IAM Policy to allow the rule to invoke the destination
resource "aws_iam_policy" "memory_generator_invoke_policy" {
  name        = "${var.app_name}-memory-generator-invoke-policy"
  description = "Allow EventBridge rule to invoke the API destination"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = "events:InvokeApiDestination"
        Effect   = "Allow"
        Resource = aws_cloudwatch_event_api_destination.memory_generator_api_destination.arn
      },
    ]
  })
}

resource "aws_iam_role_policy_attachment" "memory_generator_invoke_attachment" {
  role       = aws_iam_role.memory_generator_event_rule_role.name
  policy_arn = aws_iam_policy.memory_generator_invoke_policy.arn
}

# 5. The scheduled rule itself
resource "aws_cloudwatch_event_rule" "memory_generator_rule" {
  name                = "${var.app_name}-trigger-memory-generation-rule"
  description         = "Fires every 10 minutes to trigger memory generation"
  schedule_expression = "rate(10 minutes)"
  tags                = local.tags
}

# 6. Target to link the rule to the API destination
resource "aws_cloudwatch_event_target" "memory_generator_target" {
  rule     = aws_cloudwatch_event_rule.memory_generator_rule.name
  arn      = aws_cloudwatch_event_api_destination.memory_generator_api_destination.arn
  role_arn = aws_iam_role.memory_generator_event_rule_role.arn
} 