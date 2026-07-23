# Architecture Documentation

This document describes the technical architecture of the AWS Cost Optimization Dashboard.

## System Overview

```
+-----------------+     +------------------+     +-------------------------+
|   EventBridge   |---->|  Lambda Function |---->|   AWS Cost Explorer     |
|  (Daily Cron)   |     |  (Cost Collector)|     |   (Billing API)         |
+-----------------+     +------------------+     +-------------------------+
                                 |
                                 v
                    +---------------------------+
                    |   Data Processing         |
                    |   - Totals and breakdown  |
                    |   - Week-over-week delta  |
                    |   - Threshold check       |
                    +---------------------------+
                          |              |
                          v              v
               +----------+     +--------------------+
               | S3 Bucket |     | Secrets Manager    |
               | JSON data |     | Slack webhook URL  |
               +----------+     +--------------------+
                                          |
                                          v
                               +--------------------+
                               | Slack Channel      |
                               +--------------------+
                                          |
                               (on failure)
                                          v
                               +--------------------+
                               | SQS Dead Letter    |
                               | Queue              |
                               | CloudWatch Alarm   |
                               +--------------------+
```

## Component Details

### EventBridge

Provides the scheduled trigger. The cron expression is configurable via the
`alert_schedule` Terraform variable. The default runs at 8 AM UTC daily.
EventBridge retries failed invocations twice before routing to the Lambda DLQ.

### Lambda Function

Runtime: Python 3.11
Memory: 256 MB
Timeout: 300 seconds

Environment variables passed at deploy time:

- BUCKET_NAME: S3 bucket for cost data storage
- COST_THRESHOLD: Daily alert threshold in USD
- SLACK_SECRET_NAME: Secrets Manager secret name for the Slack webhook
- ENVIRONMENT: Deployment environment (dev, staging, prod)

The function runs these steps on each invocation:

1. Fetch yesterday's cost data from Cost Explorer grouped by AWS service
2. Store the raw response to S3 as `cost_data/daily/YYYY-MM-DD.json`
3. Calculate total spend and rank services by cost
4. Read the prior week's S3 file and compute week-over-week percentage change
5. Compare total against the threshold
6. If exceeded, retrieve the webhook URL from Secrets Manager and post to Slack
7. Raise on non-200 Slack response so the DLQ captures the failure

### AWS Cost Explorer

The function calls `GetCostAndUsage` with:

- Granularity: DAILY
- Metrics: BlendedCost, UnblendedCost
- GroupBy: SERVICE dimension

This returns a per-service cost breakdown for the previous calendar day.
Cost Explorer data has a 24-hour delay, so the function always operates on
confirmed costs rather than in-progress estimates.

### AWS Budgets

Two budget resources complement the Lambda threshold check:

- Monthly actual spend: alerts at 80% and 100% of the configured monthly limit
- Monthly forecasted spend: alerts at 100% of the monthly limit

The forecasted alert is the more operationally useful one. It fires before the
month ends, giving time to investigate and respond. The Lambda threshold check
operates on daily granularity with service-level context; Budgets operates on
monthly granularity with native AWS billing accuracy.

### S3 Bucket

Cost reports are stored as JSON files under `cost_data/daily/YYYY-MM-DD.json`.
The bucket has:

- AES256 server-side encryption
- Versioning enabled
- All public access blocked
- Lifecycle policy: Standard (0-30 days), Standard-IA (30-90 days),
  Glacier (90+ days), expiration at 7 years

The week-over-week calculation reads from this bucket, so data must be
present for at least 7 days before WoW deltas appear in alerts.

### Secrets Manager

The Slack webhook URL is stored as a JSON string:

```json
{"SLACK_WEBHOOK_URL": "https://hooks.slack.com/services/..."}
```

The Lambda IAM policy grants `secretsmanager:GetSecretValue` scoped to the
specific secret ARN, not `*`.

### SQS Dead Letter Queue

Any Lambda invocation that throws an unhandled exception (including the
`RuntimeError` raised on non-200 Slack responses) routes to the DLQ after
EventBridge exhausts its retries. A CloudWatch alarm fires within 5 minutes
when any message appears in the queue.

A second alarm fires on Lambda Errors, which catches timeouts and any other
error that surfaces in the Lambda metrics namespace.

### IAM

The execution role uses separate policy statements for each service with
resource-scoped ARNs:

- Logs: scoped to `arn:aws:logs:{region}:*:*`
- Cost Explorer: `Resource: "*"` (required by the CE API; no resource-level ARNs exist)
- S3 PutObject: scoped to `{bucket_arn}/*`
- S3 GetObject: scoped to `{bucket_arn}/cost_data/*`
- Secrets Manager: scoped to the specific secret ARN using a wildcard suffix
  for the auto-appended version ID
- SQS SendMessage: scoped to the DLQ ARN

## Data Flow

```
EventBridge trigger
  -> Lambda invoked
  -> GetCostAndUsage (Cost Explorer)
  -> PutObject (S3, raw response)
  -> process_cost_data (in-memory)
  -> GetObject (S3, prior week file) [non-fatal if missing]
  -> threshold check
  -> GetSecretValue (Secrets Manager) [only if threshold exceeded]
  -> HTTP POST (Slack webhook)
  -> return 200 or raise -> DLQ
```

## Security Architecture

### Encryption at rest

- S3: AES256 server-side encryption with bucket key enabled
- Secrets Manager: KMS encryption with AWS-managed keys
- CloudWatch Logs: encrypted with the CloudWatch Logs service key

### Encryption in transit

All AWS SDK calls use HTTPS. The Slack webhook POST uses HTTPS over TLS 1.2+.

### Network isolation (optional)

For production deployments requiring network isolation, deploy the Lambda
inside a VPC using private subnets. Add VPC endpoints for the services the
Lambda accesses:

- S3 Gateway endpoint
- Secrets Manager Interface endpoint
- CloudWatch Logs Interface endpoint

Cost Explorer does not have a VPC endpoint. A NAT gateway is required for
Cost Explorer access from a private subnet.

## Scalability

The Lambda is configured without reserved concurrency. If concurrent executions
become necessary (for example, multi-account deployments triggering multiple
functions simultaneously), add `reserved_concurrent_executions` to the Lambda
resource to prevent throttling.

The Cost Explorer API has a default rate limit of 5 requests per second.
A single daily invocation is well within this limit. If the function is
extended to query multiple accounts or date ranges, add exponential backoff
using botocore's built-in retry configuration.

## Monitoring

CloudWatch alarms deployed by Terraform:

| Alarm | Metric | Threshold | Meaning |
|---|---|---|---|
| cost-collector-dlq-depth | SQS ApproximateNumberOfMessagesVisible | > 0 | A Lambda invocation failed after retries |
| cost-collector-errors | Lambda Errors | > 0 | The function returned an error |

CloudWatch log group: `/aws/lambda/aws-cost-collector-{environment}`, retained 14 days.

## Future Architecture Considerations

Multi-account support: add a cross-account IAM role in each monitored account,
use `sts:AssumeRole` in the Lambda to fetch costs per account, and aggregate
results before threshold evaluation.

Cost anomaly detection: the Cost Explorer Anomaly Detection API
(`ce:GetAnomalies`) provides ML-based detection that handles seasonality and
gradual drift. This is a drop-in enhancement to the threshold check.

Historical trend visualisation: the S3 bucket already contains structured daily
JSON. An Athena table over this data, combined with a QuickSight dataset, would
provide a visual cost trend dashboard without additional ingestion infrastructure.
