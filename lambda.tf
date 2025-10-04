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
    aws_cloudwatch_log_group.lambda_logs
  ]
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