# AWS Cost Optimization Dashboard - Deployment Guide

This guide provides step-by-step instructions for deploying the AWS Cost Optimization Dashboard in different environments.

## Prerequisites

### Required Tools
- AWS CLI v2.x configured with appropriate permissions
- Terraform >= 1.5.0
- Git
- Python 3.11+ (for local testing)

### AWS Permissions Required
Your AWS user/role needs the following permissions:
- `iam:CreateRole`, `iam:AttachRolePolicy`, `iam:PassRole`
- `lambda:CreateFunction`, `lambda:UpdateFunctionCode`, `lambda:InvokeFunction`
- `s3:CreateBucket`, `s3:PutObject`, `s3:PutBucketPolicy`
- `events:PutRule`, `events:PutTargets`
- `secretsmanager:CreateSecret`, `secretsmanager:GetSecretValue`
- `ce:GetCostAndUsage`
- `logs:CreateLogGroup`, `logs:CreateLogStream`

## Environment Setup

### 1. Development Environment

```bash
# Clone the repository
git clone https://github.com/Copubah/aws-cost-optimization-dashboard.git
cd aws-cost-optimization-dashboard

# Create development configuration
cp terraform.tfvars.example terraform.tfvars

# Edit configuration for development
cat > terraform.tfvars << EOF
environment = "dev"
aws_region = "us-east-1"
cost_threshold = 25.0
alert_schedule = "cron(0 9 * * ? *)"
EOF

# Run setup script
./scripts/setup.sh

# Deploy infrastructure
./scripts/deploy.sh --environment dev
```

### 2. Staging Environment

```bash
# Create staging configuration
cat > terraform.tfvars << EOF
environment = "staging"
aws_region = "us-east-1"
cost_threshold = 100.0
alert_schedule = "cron(0 8 * * ? *)"
EOF

# Deploy to staging
./scripts/deploy.sh --environment staging
```

### 3. Production Environment

```bash
# Create production configuration
cat > terraform.tfvars << EOF
environment = "prod"
aws_region = "us-east-1"
cost_threshold = 500.0
alert_schedule = "cron(0 8 * * ? *)"
EOF

# Deploy to production
./scripts/deploy.sh --environment prod --auto-approve
```

## Slack Integration Setup

### 1. Create Slack App
1. Go to https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name your app "AWS Cost Monitor"
4. Select your workspace

### 2. Configure Incoming Webhooks
1. In your app settings, go to "Incoming Webhooks"
2. Toggle "Activate Incoming Webhooks" to On
3. Click "Add New Webhook to Workspace"
4. Select the channel for cost alerts
5. Copy the webhook URL

### 3. Store Webhook in AWS Secrets Manager
```bash
# Create the secret
aws secretsmanager create-secret \
  --name "slack/webhook/aws-cost-dashboard" \
  --description "Slack webhook for AWS cost alerts" \
  --secret-string '{"SLACK_WEBHOOK_URL":"YOUR_WEBHOOK_URL_HERE"}' \
  --region us-east-1
```

## Multi-Account Deployment

For organizations with multiple AWS accounts:

### 1. Cross-Account Role Setup
```hcl
# In each monitored account
resource "aws_iam_role" "cost_monitoring_role" {
  name = "CostMonitoringRole"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::MONITORING_ACCOUNT_ID:role/cost-optimization-lambda-role-prod"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "cost_monitoring_policy" {
  name = "CostMonitoringPolicy"
  role = aws_iam_role.cost_monitoring_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage",
          "ce:GetUsageReport"
        ]
        Resource = "*"
      }
    ]
  })
}
```

### 2. Update Lambda Function
```python
# Add to lambda/handler.py
def assume_role(account_id, role_name):
    """Assume role in target account"""
    sts_client = boto3.client('sts')
    
    response = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role_name}",
        RoleSessionName="CostMonitoring"
    )
    
    credentials = response['Credentials']
    return boto3.client(
        'ce',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )
```

## Monitoring and Alerting

### CloudWatch Dashboard
```hcl
resource "aws_cloudwatch_dashboard" "cost_monitoring" {
  dashboard_name = "AWS-Cost-Monitoring-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.cost_collector.function_name],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."]
          ]
          view    = "timeSeries"
          stacked = false
          region  = var.aws_region
          title   = "Lambda Metrics"
          period  = 300
        }
      }
    ]
  })
}
```

### SNS Notifications
```hcl
resource "aws_sns_topic" "cost_alerts" {
  name = "cost-alerts-${var.environment}"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.cost_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
```

## Troubleshooting

### Common Issues

#### 1. Lambda Timeout
```bash
# Check CloudWatch logs
aws logs tail /aws/lambda/aws-cost-collector-prod --follow

# Increase timeout in lambda.tf
timeout = 300  # 5 minutes
```

#### 2. Cost Explorer API Limits
```python
# Add retry logic in handler.py
import time
from botocore.exceptions import ClientError

def get_cost_data_with_retry(ce_client, max_retries=3):
    for attempt in range(max_retries):
        try:
            return ce_client.get_cost_and_usage(...)
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                time.sleep(2 ** attempt)
                continue
            raise
```

#### 3. S3 Permissions
```bash
# Check S3 bucket policy
aws s3api get-bucket-policy --bucket $(terraform output -raw s3_bucket_name)

# Test S3 access
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/cost_data/
```

### Debugging Commands
```bash
# Test Lambda function
aws lambda invoke \
  --function-name $(terraform output -raw lambda_function_name) \
  --payload '{}' \
  response.json && cat response.json

# Check EventBridge rule
aws events describe-rule --name $(terraform output -raw eventbridge_rule_name)

# View recent cost data
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/cost_data/daily/ --recursive | tail -5
```

## Cleanup

### Complete Removal
```bash
# Destroy infrastructure
terraform destroy

# Delete Slack webhook secret
aws secretsmanager delete-secret \
  --secret-id "slack/webhook/aws-cost-dashboard" \
  --force-delete-without-recovery

# Clean up local files
rm -f lambda_deployment.zip response.json tfplan terraform.tfvars
```

### Partial Cleanup
```bash
# Remove only Lambda and EventBridge (keep S3 data)
terraform destroy -target=aws_lambda_function.cost_collector
terraform destroy -target=aws_cloudwatch_event_rule.daily_cost_check
```

## Security Considerations

### Production Hardening
1. **Enable CloudTrail** for audit logging
2. **Use KMS encryption** for S3 bucket
3. **Deploy Lambda in VPC** for network isolation
4. **Enable GuardDuty** for threat detection
5. **Implement resource-based policies** for additional security

### Compliance
- **SOC 2**: Implement logging and monitoring controls
- **PCI DSS**: Use encryption and access controls
- **GDPR**: Implement data retention policies
- **HIPAA**: Use dedicated tenancy and encryption

## Performance Optimization

### Lambda Optimization
```hcl
# Optimize Lambda configuration
resource "aws_lambda_function" "cost_collector" {
  memory_size                    = 512  # Increase for better performance
  timeout                       = 300
  reserved_concurrent_executions = 1    # Prevent concurrent executions
  
  environment {
    variables = {
      PYTHONPATH = "/var/runtime"
    }
  }
}
```

### Cost Explorer Optimization
```python
# Optimize API calls
def get_cost_data(ce_client):
    # Use specific date ranges
    # Group by service only when needed
    # Cache results when possible
    pass
```