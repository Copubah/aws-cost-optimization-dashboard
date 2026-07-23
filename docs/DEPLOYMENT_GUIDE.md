# Deployment Guide

This guide covers deploying the AWS Cost Optimization Dashboard across environments.

## Prerequisites

Required tools:

- AWS CLI v2 configured with appropriate permissions
- Terraform 1.5 or later
- Git
- Python 3.11 or later (for running tests before deployment)

Required AWS permissions for the deploying user or role:

- iam:CreateRole, iam:AttachRolePolicy, iam:PassRole
- lambda:CreateFunction, lambda:UpdateFunctionCode, lambda:InvokeFunction
- s3:CreateBucket, s3:PutObject, s3:PutBucketPolicy
- events:PutRule, events:PutTargets
- secretsmanager:CreateSecret, secretsmanager:GetSecretValue
- ce:GetCostAndUsage
- logs:CreateLogGroup, logs:CreateLogStream
- sqs:CreateQueue
- budgets:CreateBudget

## Slack Webhook Setup

Go to https://api.slack.com/apps, create a new app, enable Incoming Webhooks,
add a webhook to your target channel, and copy the webhook URL.

Store it in Secrets Manager:

```bash
aws secretsmanager create-secret \
  --name "slack/webhook/aws-cost-dashboard" \
  --description "Slack webhook for AWS cost alerts" \
  --secret-string '{"SLACK_WEBHOOK_URL":"https://hooks.slack.com/services/YOUR/WEBHOOK/URL"}'
```

## Configuration

Copy the example and edit it:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Key variables:

```hcl
environment          = "dev"
aws_region           = "us-east-1"
cost_threshold       = 50.0
monthly_budget_limit = "500"
budget_alert_emails  = ["your-email@example.com"]
alert_schedule       = "cron(0 8 * * ? *)"
slack_secret_name    = "slack/webhook/aws-cost-dashboard"
```

## Deploying

```bash
terraform init
terraform plan
terraform apply
```

For production, add an S3 backend to terraform.tf before running init:

```hcl
terraform {
  backend "s3" {
    bucket         = "your-tfstate-bucket"
    key            = "cost-dashboard/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}
```

## Verifying

Invoke the Lambda manually:

```bash
aws lambda invoke \
  --function-name $(terraform output -raw lambda_function_name) \
  --payload '{}' \
  response.json

cat response.json
```

Check CloudWatch logs:

```bash
aws logs tail /aws/lambda/$(terraform output -raw lambda_function_name) --follow
```

Check the DLQ is empty:

```bash
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw lambda_dlq_url) \
  --attribute-names ApproximateNumberOfMessages
```

## Troubleshooting

Lambda timeout: increase the timeout in lambda.tf if the function consistently
hits 300 seconds. Large Cost Explorer result sets (from many services or long
date ranges) are the most common cause.

Slack delivery failing: check the DLQ for messages. The message body contains the
original invocation event and the failure reason.

S3 access denied: verify the Lambda role has s3:PutObject on the bucket ARN and
s3:GetObject on the cost_data/* prefix.

Cost Explorer throttling: the default rate is 5 requests per second. A single
daily invocation is well within limits. Add exponential backoff using the
botocore retry configuration if you extend the function to query multiple accounts.

## Cleanup

```bash
terraform destroy

aws secretsmanager delete-secret \
  --secret-id "slack/webhook/aws-cost-dashboard" \
  --force-delete-without-recovery

rm -f lambda_deployment.zip response.json
```

To remove only Lambda and EventBridge while retaining the S3 cost history:

```bash
terraform destroy \
  -target=aws_lambda_function.cost_collector \
  -target=aws_cloudwatch_event_rule.daily_cost_check
```
