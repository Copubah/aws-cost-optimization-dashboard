# AWS Cost Optimization Dashboard

A comprehensive, automated cost monitoring solution that tracks daily AWS spending, stores historical cost data in S3, and sends intelligent Slack alerts when spending exceeds defined thresholds.

**🔗 Repository:** https://github.com/Copubah/aws-cost-optimization-dashboard

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
- [Customization Examples](#customization-examples)
- [Best Practices](#best-practices)
- [Cost Efficiency Tips](#cost-efficiency-tips)
- [Testing & Monitoring](#testing--monitoring)
- [Cleanup](#cleanup)
- [Learning Outcomes](#learning-outcomes)

## Project Goals

**Why Cost Visibility Matters for Cloud Engineers:**
- **Prevent Budget Overruns**: Catch unexpected spending before it impacts your budget
- **Resource Accountability**: Identify which services and teams are driving costs
- **Proactive Management**: Get real-time alerts before costs spiral out of control
- **Data-Driven Decisions**: Historical cost data enables better resource optimization
- **Team Awareness**: Slack integration keeps engineering teams informed about spending patterns

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   EventBridge   │───▶│   Lambda Function │───▶│  Cost Explorer  │
│  (Daily Cron)   │    │  (Cost Collector) │    │      API        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   S3 Bucket     │    │ Secrets Manager │
                       │ (Cost Data JSON)│    │ (Slack Webhook) │
                       └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ Slack Channel   │
                       │   (Alerts)      │
                       └─────────────────┘
```

**📋 Detailed Architecture Documentation:**
- [Complete Architecture Diagrams](docs/ARCHITECTURE_DIAGRAM.md) - Comprehensive system architecture with detailed component breakdown
- [Interactive Mermaid Diagrams](docs/MERMAID_DIAGRAMS.md) - Visual flowcharts and sequence diagrams
- [Architecture Deep Dive](docs/ARCHITECTURE.md) - Technical implementation details and design decisions

### Components Explained

- **Terraform**: Infrastructure as Code for reproducible deployments
- **AWS Lambda**: Serverless function for cost collection and alerting logic
- **AWS Cost Explorer**: Official AWS API for cost and usage data
- **S3 Bucket**: Encrypted storage for historical cost data (JSON format)
- **Secrets Manager**: Secure storage for Slack webhook URL
- **EventBridge**: Scheduled triggers for daily cost checks
- **IAM Roles**: Least-privilege security for AWS service access

## Project Structure

```
aws-cost-optimization-dashboard/
├── terraform.tf          # Terraform provider configuration
├── variables.tf          # Input variables and defaults
├── outputs.tf            # Output values after deployment
├── s3.tf                 # S3 bucket and lifecycle policies
├── iam.tf                # IAM roles and policies
├── lambda.tf             # Lambda function configuration
├── eventbridge.tf        # EventBridge scheduling rules
├── lambda/
│   ├── handler.py        # Main Lambda function code
│   └── requirements.txt  # Python dependencies
├── scripts/
│   ├── setup.sh          # Initial setup and prerequisites
│   ├── deploy.sh         # Deployment automation
│   └── test.sh           # Testing and validation
└── terraform.tfvars.example  # Configuration template
```

## Quick Start

### Prerequisites
- AWS CLI configured with appropriate permissions
- Terraform >= 1.5.0
- Slack webhook URL for notifications
- Python 3.11+ (for local testing)

### Step 1: Initial Setup
```bash
# Clone the repository
git clone https://github.com/Copubah/aws-cost-optimization-dashboard.git
cd aws-cost-optimization-dashboard

# Run setup script (interactive)
./scripts/setup.sh
```

### Step 2: Configure Variables
```bash
# Copy example configuration
cp terraform.tfvars.example terraform.tfvars

# Edit configuration
nano terraform.tfvars
```

### Step 3: Deploy Infrastructure
```bash
# Deploy with default settings
./scripts/deploy.sh

# Or deploy to specific environment
./scripts/deploy.sh --environment prod
```

### Step 4: Test Deployment
```bash
# Test Lambda function and check logs
./scripts/test.sh
```

## Configuration Options

### Environment Variables (terraform.tfvars)

```hcl
# Environment name (dev, staging, prod)
environment = "prod"

# Daily cost threshold in USD for alerts
cost_threshold = 100.0

# Cron expression for cost check schedule (UTC)
alert_schedule = "cron(0 8 * * ? *)"  # Daily at 8 AM UTC

# AWS region for deployment
aws_region = "us-east-1"
```

### Schedule Examples
```hcl
# Daily at 8 AM UTC
alert_schedule = "cron(0 8 * * ? *)"

# Twice daily (8 AM and 8 PM UTC)
alert_schedule = "cron(0 8,20 * * ? *)"

# Weekly on Mondays at 8 AM UTC
alert_schedule = "cron(0 8 * * MON *)"

# Business days only at 9 AM UTC
alert_schedule = "cron(0 9 * * MON-FRI *)"
```

## Sample Outputs

### Terraform Deployment
```
Apply complete! Resources: 12 added, 0 changed, 0 destroyed.

Outputs:
environment = "dev"
cost_threshold = 50
eventbridge_rule_name = "daily-cost-check-dev"
iam_role_arn = "arn:aws:iam::123456789012:role/cost-optimization-lambda-role-dev"
lambda_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:aws-cost-collector-dev"
lambda_function_name = "aws-cost-collector-dev"
s3_bucket_arn = "arn:aws:s3:::aws-cost-data-dev-a1b2c3d4"
s3_bucket_name = "aws-cost-data-dev-a1b2c3d4"
slack_secret_name = "slack/webhook/aws-cost-dashboard"
```

### Enhanced Slack Alert
```
AWS Cost Alert - PROD

Date: 2024-01-15
Total Spend: $125.43
Threshold: $100.00
Overage: $25.43

Top 5 Services:
1. Amazon Elastic Compute Cloud - Compute: $65.20
2. Amazon Simple Storage Service: $25.15
3. Amazon Relational Database Service: $18.50
4. Amazon CloudFront: $12.30
5. AWS Lambda: $4.28

Total services with costs: 12
```

### S3 Cost Data Structure
```json
{
  "ResultsByTime": [
    {
      "TimePeriod": {
        "Start": "2024-01-15",
        "End": "2024-01-16"
      },
      "Total": {
        "BlendedCost": {
          "Amount": "125.43",
          "Unit": "USD"
        }
      },
      "Groups": [
        {
          "Keys": ["Amazon Elastic Compute Cloud - Compute"],
          "Metrics": {
            "BlendedCost": {
              "Amount": "65.20",
              "Unit": "USD"
            }
          }
        }
      ]
    }
  ]
}
```

## How the Lambda Function Works

### Step-by-Step Process

1. **Triggered Daily**: EventBridge triggers Lambda at scheduled time
2. **Fetch Cost Data**: Calls Cost Explorer API for previous day's costs
3. **Process Data**: Calculates totals and identifies top spending services
4. **Store in S3**: Saves raw cost data as JSON for historical analysis
5. **Check Threshold**: Compares total cost against configured threshold
6. **Send Alert**: If threshold exceeded, formats and sends Slack message
7. **Log Results**: Records execution details in CloudWatch Logs

### Key Features

- **Service-Level Breakdown**: Shows which AWS services are driving costs
- **Historical Storage**: All cost data stored in S3 with lifecycle policies
- **Error Handling**: Comprehensive error handling and logging
- **Security**: Uses IAM roles and Secrets Manager for secure access
- **Customizable**: Easy to modify thresholds, schedules, and alert formats

## Customization Examples

### Enhanced Alert Logic
```python
# Add to Lambda handler.py
def should_send_alert(cost_summary, threshold, historical_data):
    """Enhanced alerting logic with trend analysis"""
    current_cost = cost_summary['total_cost']
    
    # Basic threshold check
    if current_cost > threshold:
        return True
    
    # Trend-based alerting (30% increase from average)
    if historical_data:
        avg_cost = sum(historical_data) / len(historical_data)
        if current_cost > avg_cost * 1.3:
            return True
    
    return False
```

### Multi-Environment Support
```hcl
# Deploy multiple environments
module "cost_dashboard_dev" {
  source = "./modules/cost-dashboard"
  environment = "dev"
  cost_threshold = 25.0
}

module "cost_dashboard_prod" {
  source = "./modules/cost-dashboard"
  environment = "prod"
  cost_threshold = 200.0
}
```

## Best Practices

### Security Best Practices

#### IAM Least Privilege
- **Lambda Execution Role**: Minimal required permissions only
- **Cost Explorer Access**: Limited to `GetCostAndUsage` and `GetUsageReport`
- **S3 Access**: Restricted to specific bucket and `cost_data/` prefix
- **Secrets Manager**: Access limited to specific webhook secret
- **Resource-Based Policies**: Use resource ARNs instead of wildcards

#### Data Protection
- **Encryption at Rest**: S3 bucket encryption with AES256 or KMS
- **Encryption in Transit**: HTTPS for all API calls and Slack webhooks
- **Secrets Management**: Store sensitive data in AWS Secrets Manager
- **Access Logging**: Enable CloudTrail for audit trail
- **Data Retention**: Implement lifecycle policies for cost data

#### Network Security
```hcl
# Deploy Lambda in VPC for enhanced security
resource "aws_lambda_function" "cost_collector" {
  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}

# Use VPC endpoints for AWS services
resource "aws_vpc_endpoint" "s3" {
  vpc_id       = var.vpc_id
  service_name = "com.amazonaws.${var.aws_region}.s3"
}
```

### Infrastructure Best Practices

#### Terraform Organization
- **State Management**: Use remote state with S3 backend and DynamoDB locking
- **Module Structure**: Organize code into reusable modules
- **Variable Validation**: Implement input validation for critical parameters
- **Resource Tagging**: Consistent tagging strategy for all resources
- **Version Pinning**: Pin provider and module versions

```hcl
# terraform.tf - Remote state configuration
terraform {
  backend "s3" {
    bucket         = "your-terraform-state-bucket"
    key            = "cost-dashboard/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-state-lock"
    encrypt        = true
  }
}

# variables.tf - Input validation
variable "cost_threshold" {
  description = "Daily cost threshold in USD for alerts"
  type        = number
  validation {
    condition     = var.cost_threshold > 0 && var.cost_threshold <= 10000
    error_message = "Cost threshold must be between 0 and 10000."
  }
}
```

#### Resource Naming
- **Consistent Naming**: Use standardized naming conventions
- **Environment Prefixes**: Include environment in resource names
- **Resource Suffixes**: Use descriptive suffixes for resource types

```hcl
# Naming convention examples
resource "aws_lambda_function" "cost_collector" {
  function_name = "${var.project_name}-cost-collector-${var.environment}"
}

resource "aws_s3_bucket" "cost_data" {
  bucket = "${var.project_name}-cost-data-${var.environment}-${random_id.suffix.hex}"
}
```

### Operational Best Practices

#### Monitoring and Alerting
- **CloudWatch Alarms**: Monitor Lambda errors, duration, and throttles
- **Log Aggregation**: Centralized logging with structured log format
- **Metrics Dashboard**: Create CloudWatch dashboard for cost trends
- **Dead Letter Queues**: Handle failed Lambda executions

```hcl
# CloudWatch alarms for operational monitoring
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Lambda function errors"
  
  alarm_actions = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.project_name}-lambda-duration-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "240000"  # 4 minutes
  alarm_description   = "Lambda function duration"
}
```

#### Error Handling and Resilience
- **Retry Logic**: Implement exponential backoff for API calls
- **Circuit Breaker**: Prevent cascading failures
- **Graceful Degradation**: Continue operation with partial data
- **Dead Letter Queue**: Handle persistent failures

```python
# Enhanced error handling in Lambda
import time
import random
from botocore.exceptions import ClientError

def retry_with_backoff(func, max_retries=3, base_delay=1):
    """Retry function with exponential backoff"""
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as e:
            if attempt == max_retries - 1:
                raise
            
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
            time.sleep(delay)
```

#### Cost Optimization
- **Lambda Right-Sizing**: Monitor and adjust memory allocation
- **S3 Storage Classes**: Use appropriate storage classes for different data ages
- **API Call Optimization**: Minimize Cost Explorer API calls
- **Resource Cleanup**: Implement automated cleanup for temporary resources

```hcl
# S3 intelligent tiering for cost optimization
resource "aws_s3_bucket_intelligent_tiering_configuration" "cost_data" {
  bucket = aws_s3_bucket.cost_data.id
  name   = "EntireBucket"

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}
```

### Development Best Practices

#### Code Quality
- **Linting**: Use tools like `pylint`, `black`, and `terraform fmt`
- **Testing**: Unit tests for Lambda functions, integration tests for infrastructure
- **Documentation**: Comprehensive README and inline code documentation
- **Version Control**: Semantic versioning and conventional commits

#### CI/CD Pipeline
```yaml
# .github/workflows/deploy.yml
name: Deploy Cost Dashboard
on:
  push:
    branches: [main]
    
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        
      - name: Terraform Format Check
        run: terraform fmt -check
        
      - name: Terraform Validate
        run: terraform validate
        
      - name: Terraform Plan
        run: terraform plan
        
      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve
```

#### Environment Management
- **Environment Separation**: Separate AWS accounts or regions for dev/staging/prod
- **Configuration Management**: Environment-specific variable files
- **Promotion Strategy**: Automated promotion through environments
- **Rollback Procedures**: Quick rollback capabilities for failed deployments

## Cost Efficiency Tips

### Lambda Optimization
- **Memory**: 256MB is sufficient for Cost Explorer API calls
- **Timeout**: 300 seconds handles API delays gracefully
- **Runtime**: Python 3.11 for latest performance improvements

### S3 Storage Optimization
```hcl
# Lifecycle policy in s3.tf
rule {
  id     = "cost_data_lifecycle"
  status = "Enabled"

  transition {
    days          = 30
    storage_class = "STANDARD_IA"  # Cheaper after 30 days
  }

  transition {
    days          = 90
    storage_class = "GLACIER"      # Archive after 90 days
  }

  expiration {
    days = 2555  # Delete after 7 years
  }
}
```

### Cost Explorer API Optimization
- Single daily API call minimizes costs
- Service-level grouping provides maximum insight
- Efficient date range queries (previous day only)

## Testing & Monitoring

### Manual Testing
```bash
# Test Lambda function
aws lambda invoke \
  --function-name $(terraform output -raw lambda_function_name) \
  --payload '{}' \
  response.json

# Check CloudWatch logs
aws logs tail /aws/lambda/$(terraform output -raw lambda_function_name) --follow

# List S3 cost files
aws s3 ls s3://$(terraform output -raw s3_bucket_name)/cost_data/daily/
```

### Monitoring Setup
```hcl
# CloudWatch alarms for Lambda errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "cost-collector-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "This metric monitors lambda errors"

  dimensions = {
    FunctionName = aws_lambda_function.cost_collector.function_name
  }
}
```

## Cleanup

### Complete Removal
```bash
# Destroy all resources
terraform destroy

# Delete Slack webhook secret
aws secretsmanager delete-secret \
  --secret-id "slack/webhook/aws-cost-dashboard" \
  --force-delete-without-recovery

# Clean up local files
rm -f lambda_deployment.zip response.json tfplan
```

## Learning Outcomes

This project teaches essential cloud engineering skills:

### 1. Infrastructure as Code (IaC)
- **Terraform Mastery**: Resource management, state handling, modules
- **AWS Provider**: Understanding AWS resource relationships
- **Best Practices**: Code organization, variable management, outputs

### 2. AWS Cost Management
- **Cost Explorer API**: Programmatic access to billing data
- **Cost Dimensions**: Understanding AWS billing structure
- **Budget Governance**: Implementing automated cost controls

### 3. Serverless Architecture
- **Lambda Functions**: Event-driven computing patterns
- **EventBridge**: Scheduled automation and event routing
- **IAM Security**: Role-based access control for serverless

### 4. DevOps Integration
- **Slack Integration**: Team notification workflows
- **Monitoring**: CloudWatch logs and metrics
- **Automation**: CI/CD considerations for infrastructure

### 5. Data Management
- **JSON Processing**: Handling structured cost data
- **S3 Lifecycle**: Storage optimization strategies
- **Historical Analysis**: Building data lakes for cost trends

### 6. Security Implementation
- **Secrets Management**: AWS Secrets Manager integration
- **Encryption**: Data protection at rest and in transit
- **Least Privilege**: Minimal permission strategies

### 7. Operational Excellence
- **Error Handling**: Robust failure management
- **Logging**: Comprehensive operational visibility
- **Testing**: Automated validation and monitoring

This project provides a solid foundation for building more sophisticated cost management solutions, including budget forecasting, anomaly detection, and automated resource optimization based on spending patterns.