# AWS Cost Optimization Dashboard

An automated cost monitoring solution that tracks daily AWS spending, stores historical cost data in S3, calculates week-over-week trends, and sends Slack alerts when spending exceeds defined thresholds.

Repository: https://github.com/Copubah/aws-cost-optimization-dashboard

[![CI/CD Pipeline](https://github.com/Copubah/aws-cost-optimization-dashboard/actions/workflows/ci.yml/badge.svg)](https://github.com/Copubah/aws-cost-optimization-dashboard/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Terraform](https://img.shields.io/badge/Terraform-1.5+-purple.svg)](https://www.terraform.io/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)

## Table of Contents

- [Project Goals](#project-goals)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration Options](#configuration-options)
- [Sample Outputs](#sample-outputs)
- [How the Lambda Function Works](#how-the-lambda-function-works)
- [Best Practices](#best-practices)
- [Testing and Monitoring](#testing-and-monitoring)
- [Cleanup](#cleanup)
- [Learning Outcomes](#learning-outcomes)

## Project Goals

Cost visibility matters because unmonitored cloud spend leads to budget overruns that compound before anyone notices. This project addresses that by running a daily automated check, storing historical data for trend analysis, and routing alerts directly to Slack where engineering teams already work.

Specific goals:

- Catch unexpected spending before it becomes a budget problem
- Identify which AWS services are driving costs at a service level
- Surface week-over-week cost changes so trends are visible, not just point-in-time values
- Keep the alerting system itself observable through a Dead Letter Queue and CloudWatch alarms
- Complement Lambda-based reporting with AWS Budgets for native forecasted-spend enforcement

## Architecture

```
+-----------------+     +------------------+     +-------------------------+
|   EventBridge   |---->|  Lambda Function |---->|   AWS Cost Explorer     |
|  (Daily Cron)   |     |  (Cost Collector)|     |   (Billing API)         |
+-----------------+     +------------------+     +-------------------------+
                                 |
                                 v
                    +---------------------------+
                    |   Data Processing         |
                    |   - Totals & breakdown    |
                    |   - Week-over-week delta  |
                    |   - Threshold check       |
                    +---------------------------+
                          |              |
                          v              v
               +----------+       +---------------------+
               | S3 Bucket |       | Secrets Manager     |
               | (JSON)    |       | (Slack webhook URL) |
               +----------+       +---------------------+
                                          |
                                          v
                               +--------------------+
                               | Slack Channel      |
                               | (Cost Alerts)      |
                               +--------------------+
                                          |
                               (on failure)
                                          v
                               +--------------------+
                               | SQS Dead Letter    |
                               | Queue + CloudWatch |
                               | Alarm              |
                               +--------------------+
```

Detailed architecture documentation:

- [Architecture Diagrams](docs/ARCHITECTURE_DIAGRAM.md) - Component breakdown and data flow
- [Mermaid Diagrams](docs/MERMAID_DIAGRAMS.md) - Visual flowcharts rendered on GitHub
- [Architecture Deep Dive](docs/ARCHITECTURE.md) - Technical design decisions

### Components

- Terraform: Infrastructure as Code for all AWS resources
- AWS Lambda: Serverless function running Python 3.11 for cost collection and alerting
- AWS Cost Explorer: Official AWS billing API providing service-level daily cost data
- AWS Budgets: Native budget enforcement with actual and forecasted spend alerts
- S3 Bucket: Encrypted storage for historical cost data in JSON format
- Secrets Manager: Secure storage for the Slack webhook URL
- EventBridge: Scheduled daily trigger at 8 AM UTC
- SQS Dead Letter Queue: Captures failed Lambda invocations so delivery failures are not silent
- CloudWatch Alarms: Fires on DLQ depth and Lambda errors
- IAM Roles: Least-privilege access scoped to specific resource ARNs

## Project Structure

```
aws-cost-optimization-dashboard/
├── terraform.tf              # Provider configuration
├── variables.tf              # Input variables with validation
├── outputs.tf                # Deployment outputs
├── s3.tf                     # S3 bucket and lifecycle policies
├── iam.tf                    # IAM roles and policies
├── lambda.tf                 # Lambda function, DLQ, CloudWatch alarms
├── eventbridge.tf            # EventBridge scheduling
├── budgets.tf                # AWS Budgets (actual + forecasted)
├── lambda/
│   ├── handler.py            # Lambda function code
│   └── requirements.txt      # Python dependencies
├── tests/
│   └── test_handler.py       # Unit tests (24 tests, zero AWS calls)
├── scripts/
│   ├── setup.sh              # Interactive setup
│   ├── deploy.sh             # Deployment automation
│   └── test.sh               # Smoke tests against deployed resources
├── docs/
│   ├── ARCHITECTURE.md
│   ├── ARCHITECTURE_DIAGRAM.md
│   ├── DEPLOYMENT_GUIDE.md
│   └── MERMAID_DIAGRAMS.md
└── terraform.tfvars.example  # Configuration template
```

## Quick Start

### Prerequisites

- AWS CLI configured with appropriate permissions
- Terraform 1.5 or later
- Slack webhook URL
- Python 3.11 or later (for running tests locally)

### Step 1: Clone and configure

```bash
git clone https://github.com/Copubah/aws-cost-optimization-dashboard.git
cd aws-cost-optimization-dashboard

cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your thresholds and email addresses
```

### Step 2: Store the Slack webhook

```bash
aws secretsmanager create-secret \
  --name "slack/webhook/aws-cost-dashboard" \
  --description "Slack webhook for AWS cost alerts" \
  --secret-string '{"SLACK_WEBHOOK_URL":"https://hooks.slack.com/services/YOUR/WEBHOOK/URL"}'
```

### Step 3: Run unit tests

```bash
pip install pytest boto3 urllib3
pytest tests/ -v
```

### Step 4: Deploy

```bash
terraform init
terraform plan
terraform apply
```

### Step 5: Verify

```bash
# Invoke the Lambda manually and inspect the response
aws lambda invoke \
  --function-name $(terraform output -raw lambda_function_name) \
  --payload '{}' \
  response.json

cat response.json
```

## Configuration Options

All options are set in `terraform.tfvars`. Copy `terraform.tfvars.example` as a starting point.

```hcl
environment          = "prod"
aws_region           = "us-east-1"
cost_threshold       = 100.0        # Daily Lambda alert threshold in USD
monthly_budget_limit = "2000"       # Monthly AWS Budgets limit in USD
budget_alert_emails  = ["ops@example.com"]
alert_schedule       = "cron(0 8 * * ? *)"  # 8 AM UTC daily
```

Schedule examples:

```hcl
# Twice daily
alert_schedule = "cron(0 8,20 * * ? *)"

# Weekdays only
alert_schedule = "cron(0 9 * * MON-FRI *)"
```

## Sample Outputs

### Terraform apply

```
Apply complete! Resources: 14 added, 0 changed, 0 destroyed.

Outputs:
environment          = "dev"
cost_threshold       = 50
monthly_budget_limit = "500"
lambda_function_name = "aws-cost-collector-dev"
lambda_dlq_url       = "https://sqs.us-east-1.amazonaws.com/123456789012/cost-collector-dlq-dev"
s3_bucket_name       = "aws-cost-data-dev-a1b2c3d4"
eventbridge_rule_name = "daily-cost-check-dev"
```

### Slack alert

```
AWS Cost Alert - PROD

Date:              2024-01-15
Total Spend:       $125.43
Threshold:         $100.00
Overage:           $25.43
Week-over-Week:    up 12.3% vs same day last week
Services with spend: 12

Top 5 Services:
1. Amazon EC2: $65.20
2. Amazon S3: $25.15
3. Amazon RDS: $18.50
4. Amazon CloudFront: $12.30
5. AWS Lambda: $4.28
```

### S3 cost data (JSON)

```json
{
  "ResultsByTime": [
    {
      "TimePeriod": { "Start": "2024-01-15", "End": "2024-01-16" },
      "Total": {
        "BlendedCost": { "Amount": "125.43", "Unit": "USD" }
      },
      "Groups": [
        {
          "Keys": ["Amazon EC2"],
          "Metrics": {
            "BlendedCost": { "Amount": "65.20", "Unit": "USD" }
          }
        }
      ]
    }
  ]
}
```

## How the Lambda Function Works

The handler runs these steps in sequence on each invocation:

1. Fetch yesterday's cost data from Cost Explorer, grouped by AWS service
2. Store the raw API response to S3 as `cost_data/daily/YYYY-MM-DD.json`
3. Process the response: calculate total, rank services by cost, filter zero-spend services
4. Read last week's S3 file (same weekday minus 7 days) and compute the week-over-week delta
5. Compare the total against the configured threshold
6. If the threshold is exceeded, retrieve the Slack webhook from Secrets Manager and post the alert
7. If Slack returns a non-200 response, raise an exception so the failed invocation routes to the DLQ

The DLQ alarm fires within 5 minutes of any failure, so the alerting pipeline is itself monitored.

## Best Practices

### Security

IAM permissions follow least privilege. Each statement is scoped to a specific resource ARN:

- Cost Explorer access: `ce:GetCostAndUsage`, `ce:GetUsageReport`, `ce:GetDimensionValues`
- S3 write: `s3:PutObject` scoped to the cost data bucket ARN
- S3 read: `s3:GetObject` scoped to `cost_data/*` for week-over-week lookups
- Secrets Manager: `secretsmanager:GetSecretValue` scoped to the specific secret ARN
- SQS: `sqs:SendMessage` scoped to the DLQ ARN

The Slack webhook URL is stored in Secrets Manager, not in environment variables or source code.

S3 is configured with server-side encryption (AES256), public access blocked on all four settings, and versioning enabled.

For production, deploy the Lambda inside a VPC with private subnets and VPC endpoints for S3, Secrets Manager, and Cost Explorer to eliminate traffic over the public internet.

### Infrastructure

Use a remote Terraform backend in production:

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

Pin provider versions. The `.terraform.lock.hcl` file is committed to the repository to ensure reproducible deployments.

### Observability

Two CloudWatch alarms are deployed alongside the Lambda:

- DLQ depth alarm: fires when any message lands in the DLQ (catches failed Slack delivery and unhandled exceptions)
- Lambda errors alarm: fires when the function itself returns an error

Both alarms use `treat_missing_data = "notBreaching"` to avoid false positives on days with no invocations.

Log retention is set to 14 days to balance operational visibility against cost.

### AWS Budgets vs Lambda threshold

These serve different purposes and complement each other:

- The Lambda threshold triggers on daily actual spend with a service-level breakdown and week-over-week context
- AWS Budgets triggers on monthly actual spend (at 80% and 100%) and monthly forecasted spend (at 100%)

The forecasted alert is the most operationally valuable: it fires before the month ends, giving time to respond.

### Testing

Run the unit test suite before deploying:

```bash
pytest tests/ -v
```

The 24 tests cover all handler functions using mocks. No AWS credentials or network access are required.

## Testing and Monitoring

### Run unit tests

```bash
pytest tests/ -v --tb=short
```

### Invoke the Lambda manually

```bash
aws lambda invoke \
  --function-name $(terraform output -raw lambda_function_name) \
  --payload '{}' \
  response.json

cat response.json
```

### Tail CloudWatch logs

```bash
aws logs tail /aws/lambda/$(terraform output -raw lambda_function_name) --follow
```

### Check the DLQ

```bash
aws sqs get-queue-attributes \
  --queue-url $(terraform output -raw lambda_dlq_url) \
  --attribute-names ApproximateNumberOfMessages
```

### List stored cost files

```bash
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/cost_data/daily/ --recursive
```

## Cleanup

```bash
# Destroy all provisioned resources
terraform destroy

# Delete the Slack webhook secret
aws secretsmanager delete-secret \
  --secret-id "slack/webhook/aws-cost-dashboard" \
  --force-delete-without-recovery

# Remove local build artifacts
rm -f lambda_deployment.zip response.json
```

## Learning Outcomes

This project covers the following areas relevant to cloud and DevOps engineering roles:

Infrastructure as Code: Modular Terraform with resource-scoped IAM, lifecycle policies, and input validation.

AWS Cost Management: Practical use of the Cost Explorer API and AWS Budgets, including the difference between actual-spend and forecasted-spend alerting.

Serverless Architecture: Event-driven Lambda with scheduled triggers, environment-variable configuration, and DLQ-based failure handling.

Observability: CloudWatch alarms on both Lambda errors and DLQ depth, structured logging, and log retention policies.

Testing: Unit test suite with mocked AWS clients covering all handler functions, including failure paths.

Security: Secrets Manager integration, least-privilege IAM, S3 encryption, and VPC deployment patterns.

DevOps: CI/CD pipeline with Black formatting, Flake8 linting, pytest, Terraform validation, Checkov IaC security scanning, and Trivy vulnerability scanning.
