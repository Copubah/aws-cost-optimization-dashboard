terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

resource "random_id" "suffix" {
  byte_length = 4
}

# S3 bucket for cost data
resource "aws_s3_bucket" "cost_data" {
  bucket = "aws-cost-data-${random_id.suffix.hex}"
  acl    = "private"

  versioning {
    enabled = true
  }

  server_side_encryption_configuration {
    rule {
      apply_server_side_encryption_by_default {
        sse_algorithm = "AES256"
      }
    }
  }

  tags = {
    Project = "AWS Cost Optimization Dashboard"
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "cost-lambda-role"
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
}

# Policy for Lambda to access Cost Explorer, S3, Secrets Manager, and Logs
resource "aws_iam_role_policy" "lambda_policy" {
  name = "cost-lambda-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "ce:GetCostAndUsage",
          "s3:PutObject",
          "secretsmanager:GetSecretValue"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "cost_collector" {
  filename         = "lambda.zip"
  function_name    = "aws-cost-collector"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  source_code_hash = filebase64sha256("lambda.zip")
  timeout          = 120

  environment {
    variables = {
      BUCKET_NAME    = aws_s3_bucket.cost_data.bucket
      COST_THRESHOLD = "10"
    }
  }

  depends_on = [aws_iam_role_policy.lambda_policy]
}

# EventBridge schedule for daily run
resource "aws_cloudwatch_event_rule" "daily_trigger" {
  name                = "daily-cost-trigger"
  schedule_expression = "cron(0 6 * * ? *)"
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_trigger.name
  target_id = "sendToLambda"
  arn       = aws_lambda_function.cost_collector.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_collector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_trigger.arn
}
