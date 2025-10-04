output "s3_bucket_name" {
  description = "Name of the S3 bucket storing cost data"
  value       = aws_s3_bucket.cost_data.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.cost_data.arn
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.cost_collector.function_name
}

output "lambda_function_arn" {
  description = "ARN of the Lambda function"
  value       = aws_lambda_function.cost_collector.arn
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule"
  value       = aws_cloudwatch_event_rule.daily_cost_check.name
}

output "iam_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.cost_lambda_role.arn
}

output "cost_threshold" {
  description = "Current cost threshold for alerts"
  value       = var.cost_threshold
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

output "slack_secret_name" {
  description = "Name of the Slack webhook secret in Secrets Manager"
  value       = var.slack_secret_name
}