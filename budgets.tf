# AWS Budgets - native budget enforcement alongside Cost Explorer reporting
#
# This complements the Lambda threshold check: Budgets uses AWS's own
# billing engine (more accurate, handles forecasted spend) while the
# Lambda adds service-level breakdown and WoW trend context to alerts.

data "aws_caller_identity" "current" {}

resource "aws_budgets_budget" "monthly_actual" {
  name         = "monthly-actual-cost-${var.environment}"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # Alert at 80% of budget (early warning)
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }

  # Alert at 100% of budget (threshold breached)
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = var.budget_alert_emails
  }
}

resource "aws_budgets_budget" "monthly_forecasted" {
  name         = "monthly-forecasted-cost-${var.environment}"
  budget_type  = "COST"
  limit_amount = var.monthly_budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # Alert when AWS forecasts the month will exceed budget — fires before it happens
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = var.budget_alert_emails
  }
}