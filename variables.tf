variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "cost_threshold" {
  description = "Daily cost threshold in USD for alerts"
  type        = number
  default     = 50.0
}

variable "alert_schedule" {
  description = "Cron expression for cost check schedule (UTC)"
  type        = string
  default     = "cron(0 8 * * ? *)"  # 8 AM UTC daily
}

variable "slack_secret_name" {
  description = "AWS Secrets Manager secret name for Slack webhook"
  type        = string
  default     = "slack/webhook/aws-cost-dashboard"
}
