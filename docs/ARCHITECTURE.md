# AWS Cost Optimization Dashboard - Architecture Documentation

This document provides detailed architectural information about the AWS Cost Optimization Dashboard solution.

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              AWS Account                                     │
│                                                                             │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────────┐ │
│  │   EventBridge   │───▶│   Lambda Function │───▶│    Cost Explorer API    │ │
│  │  (Cron Trigger) │    │  (Cost Collector) │    │   (Billing Data)       │ │
│  └─────────────────┘    └──────────────────┘    └─────────────────────────┘ │
│                                   │                                         │
│                                   ▼                                         │
│  ┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────────┐ │
│  │ Secrets Manager │    │    S3 Bucket     │    │    CloudWatch Logs     │ │
│  │ (Slack Webhook) │    │ (Historical Data)│    │   (Function Logs)      │ │
│  └─────────────────┘    └──────────────────┘    └─────────────────────────┘ │
│                                   │                                         │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    ▼
                          ┌─────────────────┐
                          │ Slack Channel   │
                          │   (Alerts)      │
                          └─────────────────┘
```

### Component Details

#### 1. EventBridge (CloudWatch Events)
- **Purpose**: Scheduled trigger for daily cost collection
- **Configuration**: Cron expression for flexible scheduling
- **Reliability**: Built-in retry mechanism and error handling

#### 2. Lambda Function
- **Runtime**: Python 3.11
- **Memory**: 256MB (configurable)
- **Timeout**: 300 seconds
- **Concurrency**: Reserved concurrency of 1 to prevent overlapping executions

#### 3. Cost Explorer API
- **Data Source**: Official AWS billing and cost data
- **Granularity**: Daily cost breakdown by service
- **Metrics**: BlendedCost, UnblendedCost, UsageQuantity

#### 4. S3 Bucket
- **Storage**: Historical cost data in JSON format
- **Encryption**: AES256 server-side encryption
- **Lifecycle**: Automatic transition to cheaper storage classes

#### 5. Secrets Manager
- **Purpose**: Secure storage of Slack webhook URL
- **Encryption**: KMS encryption at rest
- **Access**: IAM-controlled access

## Data Flow

### 1. Scheduled Execution
```
EventBridge Rule (Cron) → Lambda Function Invocation
```

### 2. Cost Data Collection
```
Lambda Function → Cost Explorer API → Raw Cost Data (JSON)
```

### 3. Data Processing
```
Raw Data → Processing Logic → Cost Summary + Service Breakdown
```

### 4. Data Storage
```
Processed Data → S3 Bucket (cost_data/daily/YYYY-MM-DD.json)
```

### 5. Threshold Evaluation
```
Cost Summary → Threshold Check → Alert Decision
```

### 6. Alert Delivery
```
Alert Decision → Secrets Manager (Webhook) → Slack API → Channel Notification
```

## Security Architecture

### Identity and Access Management (IAM)

#### Lambda Execution Role Permissions
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ce:GetCostAndUsage",
        "ce:GetUsageReport"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::cost-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:region:account:secret:slack/webhook/*"
    }
  ]
}
```

### Data Encryption

#### At Rest
- **S3 Bucket**: AES256 server-side encryption
- **Secrets Manager**: KMS encryption with AWS managed keys
- **CloudWatch Logs**: Encrypted with CloudWatch Logs service key

#### In Transit
- **HTTPS**: All API communications use TLS 1.2+
- **Slack Webhook**: HTTPS POST requests to Slack API

### Network Security

#### VPC Deployment (Optional)
```hcl
resource "aws_lambda_function" "cost_collector" {
  vpc_config {
    subnet_ids         = var.private_subnet_ids
    security_group_ids = [aws_security_group.lambda_sg.id]
  }
}

resource "aws_security_group" "lambda_sg" {
  name_prefix = "cost-lambda-sg"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
```

## Scalability and Performance

### Lambda Performance Optimization

#### Memory and CPU Allocation
- **Memory**: 256MB provides optimal price/performance ratio
- **CPU**: Scales proportionally with memory allocation
- **Execution Time**: Typically 30-60 seconds for standard workloads

#### Concurrency Management
```hcl
resource "aws_lambda_function" "cost_collector" {
  reserved_concurrent_executions = 1
  # Prevents overlapping executions
}
```

### Cost Explorer API Optimization

#### Request Optimization
```python
# Efficient API usage
response = ce_client.get_cost_and_usage(
    TimePeriod={
        'Start': start_date,
        'End': end_date
    },
    Granularity='DAILY',  # Most efficient granularity
    Metrics=['BlendedCost'],  # Only required metrics
    GroupBy=[{
        'Type': 'DIMENSION',
        'Key': 'SERVICE'  # Service-level breakdown
    }]
)
```

#### Rate Limiting and Retry Logic
```python
import time
from botocore.exceptions import ClientError

def retry_with_exponential_backoff(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                time.sleep(wait_time)
                continue
            raise
```

### S3 Storage Optimization

#### Lifecycle Policies
```hcl
resource "aws_s3_bucket_lifecycle_configuration" "cost_data_lifecycle" {
  bucket = aws_s3_bucket.cost_data.id

  rule {
    id     = "cost_data_lifecycle"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "STANDARD_IA"  # 40% cost reduction
    }

    transition {
      days          = 90
      storage_class = "GLACIER"      # 80% cost reduction
    }

    transition {
      days          = 365
      storage_class = "DEEP_ARCHIVE" # 95% cost reduction
    }

    expiration {
      days = 2555  # 7 years retention
    }
  }
}
```

## Monitoring and Observability

### CloudWatch Metrics

#### Lambda Metrics
- **Duration**: Function execution time
- **Errors**: Function errors and failures
- **Invocations**: Number of function invocations
- **Throttles**: Concurrency limit throttling

#### Custom Metrics
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def put_custom_metric(metric_name, value, unit='Count'):
    cloudwatch.put_metric_data(
        Namespace='CostOptimization',
        MetricData=[
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Dimensions': [
                    {
                        'Name': 'Environment',
                        'Value': os.environ.get('ENVIRONMENT', 'dev')
                    }
                ]
            }
        ]
    )
```

### Logging Strategy

#### Structured Logging
```python
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def log_structured(level, message, **kwargs):
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'level': level,
        'message': message,
        'environment': os.environ.get('ENVIRONMENT'),
        **kwargs
    }
    logger.log(getattr(logging, level.upper()), json.dumps(log_entry))
```

### Alerting and Notifications

#### CloudWatch Alarms
```hcl
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "cost-collector-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Lambda function errors"
  
  alarm_actions = [aws_sns_topic.alerts.arn]
  
  dimensions = {
    FunctionName = aws_lambda_function.cost_collector.function_name
  }
}
```

## Disaster Recovery and Business Continuity

### Backup Strategy

#### Infrastructure as Code
- **Terraform State**: Stored in S3 with versioning
- **Configuration**: Version controlled in Git
- **Secrets**: Backed up in Secrets Manager with cross-region replication

#### Data Backup
```hcl
resource "aws_s3_bucket_replication_configuration" "cost_data_replication" {
  role   = aws_iam_role.replication.arn
  bucket = aws_s3_bucket.cost_data.id

  rule {
    id     = "replicate_cost_data"
    status = "Enabled"

    destination {
      bucket        = aws_s3_bucket.cost_data_backup.arn
      storage_class = "STANDARD_IA"
    }
  }
}
```

### Recovery Procedures

#### Infrastructure Recovery
```bash
# Restore from Terraform state
terraform init
terraform plan
terraform apply

# Verify deployment
./scripts/test.sh
```

#### Data Recovery
```bash
# Restore from backup bucket
aws s3 sync s3://backup-bucket/cost_data/ s3://primary-bucket/cost_data/
```

## Cost Analysis

### Infrastructure Costs

#### Monthly Cost Breakdown (Estimated)
- **Lambda**: $0.20 (1 execution/day, 60s duration, 256MB)
- **S3 Storage**: $0.50 (1GB historical data)
- **Cost Explorer API**: $0.01 (30 API calls/month)
- **CloudWatch Logs**: $0.10 (log retention)
- **Secrets Manager**: $0.40 (1 secret)
- **EventBridge**: $0.00 (included in free tier)

**Total Monthly Cost**: ~$1.21

#### Cost Optimization Opportunities
1. **S3 Lifecycle Policies**: Reduce storage costs by 80%
2. **Lambda Memory Optimization**: Right-size memory allocation
3. **Log Retention**: Reduce CloudWatch log retention period
4. **API Call Optimization**: Minimize Cost Explorer API calls

### ROI Analysis

#### Cost Savings Potential
- **Early Detection**: Prevent 5-10% budget overruns
- **Resource Optimization**: Identify 15-20% cost reduction opportunities
- **Team Awareness**: Reduce wasteful spending by 10-15%

#### Break-Even Analysis
- **Monthly Infrastructure Cost**: $1.21
- **Break-Even Savings**: $15-20/month
- **Typical ROI**: 1000-2000% for medium-sized AWS accounts

## Future Enhancements

### Planned Features
1. **Multi-Account Support**: Consolidated billing across accounts
2. **Anomaly Detection**: ML-based cost anomaly detection
3. **Budget Forecasting**: Predictive cost modeling
4. **Custom Dashboards**: Real-time cost visualization
5. **Integration APIs**: REST API for external integrations

### Scalability Roadmap
1. **Microservices Architecture**: Break down into smaller functions
2. **Event-Driven Processing**: Use SQS/SNS for decoupling
3. **Caching Layer**: Redis/ElastiCache for performance
4. **Data Lake Integration**: Integration with AWS Lake Formation