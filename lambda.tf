# Lambda Function for Cost Collection and Alerting
resource "aws_lambda_function" "cost_collector" {
  filename      = "lambda_deployment.zip"
  function_name = "aws-cost-collector-${var.environment}"
  role          = aws_iam_role.cost_lambda_role.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 256

  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  # Route failed invocations to the DLQ so silent drops are visible
  dead_letter_config {
    target_arn = aws_sqs_queue.lambda_dlq.arn
  }

  environment {
    variables = {
      BUCKET_NAME       = aws_s3_bucket.cost_data.bucket
      COST_THRESHOLD    = var.cost_threshold
      SLACK_SECRET_NAME = var.slack_secret_name
      ENVIRONMENT       = var.environment
    }
  }

  depends_on = [
    aws_iam_role_policy.cost_lambda_policy,
    aws_cloudwatch_log_group.lambda_logs,
  ]
}

# SQS Dead Letter Queue for failed Lambda invocations
resource "aws_sqs_queue" "lambda_dlq" {
  name                      = "cost-collector-dlq-${var.environment}"
  message_retention_seconds = 1209600 # 14 days

  tags = {
    Name = "cost-collector-dlq-${var.environment}"
  }
}

# CloudWatch alarm fires when any message lands in the DLQ
resource "aws_cloudwatch_metric_alarm" "dlq_depth" {
  alarm_name          = "cost-collector-dlq-depth-${var.environment}"
  alarm_description   = "Lambda DLQ has messages — cost alert delivery may have failed"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ApproximateNumberOfMessagesVisible"
  namespace           = "AWS/SQS"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    QueueName = aws_sqs_queue.lambda_dlq.name
  }
}

# CloudWatch alarm for Lambda errors (distinct from DLQ — covers timeouts etc.)
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "cost-collector-errors-${var.environment}"
  alarm_description   = "Lambda function returned an error"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 0
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.cost_collector.function_name
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_logs" {
  name              = "/aws/lambda/aws-cost-collector-${var.environment}"
  retention_in_days = 14
}

# Archive Lambda code for deployment
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/lambda"
  output_path = "${path.module}/lambda_deployment.zip"
}