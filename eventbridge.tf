# EventBridge Rule for Daily Cost Check
resource "aws_cloudwatch_event_rule" "daily_cost_check" {
  name                = "daily-cost-check-${var.environment}"
  description         = "Trigger cost collection and alerting daily"
  schedule_expression = var.alert_schedule
}

# EventBridge Target - Lambda Function
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_cost_check.name
  target_id = "CostCollectorLambdaTarget"
  arn       = aws_lambda_function.cost_collector.arn
}

# Lambda Permission for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_collector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_cost_check.arn
}