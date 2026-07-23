variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, prod)"
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "cost_threshold" {
  description = "Daily cost threshold in USD — Lambda alerts when exceeded"
  type        = number
  default     = 50.0

  validation {
    condition     = var.cost_threshold > 0
    error_message = "cost_threshold must be greater than 0."
  }
}

variable "monthly_budget_limit" {
  description = "Monthly budget limit in USD for AWS Budgets (actual + forecasted alerts)"
  type        = string
  default     = "500"
}

variable "budget_alert_emails" {
  description = "Email addresses to notify when AWS Budgets thresholds are breached"
  type        = list(string)
  default     = []
}

variable "alert_schedule" {
  description = "Cron expression for cost check schedule (UTC)"
  type        = string
  default     = "cron(0 8 * * ? *)" # 8 AM UTC daily
}

variable "slack_secret_name" {
  description = "AWS Secrets Manager secret name for Slack webhook"
  type        = string
  default     = "slack/webhook/aws-cost-dashboard"
}
