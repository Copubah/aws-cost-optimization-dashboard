# AWS Cost Optimization Dashboard - Architecture Diagram

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                AWS Account                                          │
│                                                                                     │
│  ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────────────┐  │
│  │   EventBridge   │────▶│   Lambda Function │────▶│    AWS Cost Explorer       │  │
│  │  (Cron Trigger) │     │  (Cost Collector) │     │      (Billing API)         │  │
│  │                 │     │                  │     │                             │  │
│  │ Daily: 8AM UTC  │     │ Python 3.11      │     │ Service-level cost data     │  │
│  │ Configurable    │     │ 256MB / 300s     │     │ Previous day's spending     │  │
│  └─────────────────┘     └──────────────────┘     └─────────────────────────────┘  │
│                                   │                                                 │
│                                   │                                                 │
│                                   ▼                                                 │
│  ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────────────┐  │
│  │ Secrets Manager │◀────│  Data Processing │────▶│       S3 Bucket             │  │
│  │                 │     │   & Threshold    │     │   (Historical Data)         │  │
│  │ Slack Webhook   │     │     Checking     │     │                             │  │
│  │ URL (Encrypted) │     │                  │     │ JSON cost reports           │  │
│  │                 │     │ Cost Summary     │     │ Lifecycle policies          │  │
│  └─────────────────┘     │ Service Breakdown│     │ Standard → IA → Glacier     │  │
│                          └──────────────────┘     └─────────────────────────────┘  │
│                                   │                                                 │
│                                   │                                                 │
│                                   ▼                                                 │
│  ┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────────────┐  │
│  │ CloudWatch Logs │◀────│ Alert Decision   │────▶│      Slack Channel          │  │
│  │                 │     │     Logic        │     │     (Team Notifications)    │  │
│  │ Function logs   │     │                  │     │                             │  │
│  │ Error tracking  │     │ If cost >        │     │ Rich formatted alerts       │  │
│  │ Performance     │     │ threshold:       │     │ Cost breakdown by service   │  │
│  │ monitoring      │     │ → Send alert     │     │ Threshold overage details   │  │
│  └─────────────────┘     └──────────────────┘     └─────────────────────────────┘  │
│                                                                                     │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

## Detailed Component Architecture

### 1. Trigger Layer
```
┌─────────────────────────────────────────────────────────────────┐
│                    EventBridge (CloudWatch Events)              │
├─────────────────────────────────────────────────────────────────┤
│ • Cron Expression: "cron(0 8 * * ? *)" (8 AM UTC daily)        │
│ • Configurable schedule per environment                         │
│ • Automatic retry on Lambda failures                           │
│ • Dead letter queue for persistent failures                    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
```

### 2. Compute Layer
```
┌─────────────────────────────────────────────────────────────────┐
│                      AWS Lambda Function                        │
├─────────────────────────────────────────────────────────────────┤
│ Runtime: Python 3.11                                           │
│ Memory: 256MB (configurable)                                   │
│ Timeout: 300 seconds                                           │
│ Concurrency: Reserved 1 (prevents overlapping executions)     │
│                                                                │
│ Environment Variables:                                          │
│ • BUCKET_NAME: S3 bucket for cost data                        │
│ • COST_THRESHOLD: Alert threshold in USD                      │
│ • SLACK_SECRET_NAME: Secrets Manager secret name              │
│ • ENVIRONMENT: Deployment environment (dev/staging/prod)      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
```

### 3. Data Flow Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Cost Explorer  │───▶│  Lambda Process │───▶│   S3 Storage    │
│                 │    │                 │    │                 │
│ • GetCostAndUsage│    │ 1. Fetch Data   │    │ • JSON Reports  │
│ • Service Groups │    │ 2. Process      │    │ • Daily Files   │
│ • Daily Granular│    │ 3. Calculate    │    │ • Lifecycle     │
│ • Previous Day   │    │ 4. Store        │    │ • Versioning    │
└─────────────────┘    │ 5. Check Thresh │    └─────────────────┘
                       │ 6. Alert if >   │
                       └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Secrets Manager │◀───│ Alert Decision  │───▶│ Slack Webhook   │
│                 │    │                 │    │                 │
│ • Webhook URL   │    │ • Threshold     │    │ • Rich Messages │
│ • KMS Encrypted │    │   Comparison    │    │ • Service List  │
│ • IAM Protected │    │ • Format Message│    │ • Cost Details  │
└─────────────────┘    │ • Send Alert    │    └─────────────────┘
                       └─────────────────┘
```

## Security Architecture

### IAM Permissions Model
```
┌─────────────────────────────────────────────────────────────────┐
│                    Lambda Execution Role                        │
├─────────────────────────────────────────────────────────────────┤
│ Cost Explorer Permissions:                                      │
│ • ce:GetCostAndUsage                                           │
│ • ce:GetUsageReport                                            │
│                                                                │
│ S3 Permissions:                                                │
│ • s3:PutObject (specific bucket/prefix only)                  │
│ • s3:PutObjectAcl                                             │
│                                                                │
│ Secrets Manager Permissions:                                   │
│ • secretsmanager:GetSecretValue (specific secret ARN)         │
│                                                                │
│ CloudWatch Logs Permissions:                                   │
│ • logs:CreateLogGroup                                          │
│ • logs:CreateLogStream                                         │
│ • logs:PutLogEvents                                            │
└─────────────────────────────────────────────────────────────────┘
```

### Data Encryption
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   At Rest       │    │   In Transit    │    │   In Memory     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ S3: AES256      │    │ HTTPS/TLS 1.2+  │    │ Lambda Runtime  │
│ Secrets: KMS    │    │ AWS API calls   │    │ Secure handling │
│ Logs: CloudWatch│    │ Slack webhook   │    │ No persistence  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Data Storage Architecture

### S3 Bucket Structure
```
s3://aws-cost-data-{env}-{random}/
├── cost_data/
│   └── daily/
│       ├── 2024-01-15.json
│       ├── 2024-01-16.json
│       ├── 2024-01-17.json
│       └── ...
└── (lifecycle policies applied)
```

### Lifecycle Management
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Standard      │───▶│  Standard-IA    │───▶│    Glacier      │
│   (0-30 days)   │    │  (30-90 days)   │    │  (90+ days)     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Immediate     │    │ • 40% cost      │    │ • 80% cost      │
│   access        │    │   reduction     │    │   reduction     │
│ • Full cost     │    │ • Quick access  │    │ • Archive       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
                                              ┌─────────────────┐
                                              │   Expiration    │
                                              │  (7 years)      │
                                              ├─────────────────┤
                                              │ • Compliance    │
                                              │ • Cost optimal  │
                                              └─────────────────┘
```

## Monitoring and Observability

### CloudWatch Integration
```
┌─────────────────────────────────────────────────────────────────┐
│                      CloudWatch Metrics                         │
├─────────────────────────────────────────────────────────────────┤
│ Lambda Metrics:                                                 │
│ • Duration (execution time)                                     │
│ • Errors (function failures)                                   │
│ • Invocations (execution count)                                │
│ • Throttles (concurrency limits)                              │
│                                                                │
│ Custom Metrics:                                                │
│ • Daily cost amounts                                           │
│ • Threshold breaches                                           │
│ • Alert success/failure rates                                 │
│ • Service cost trends                                          │
└─────────────────────────────────────────────────────────────────┘
```

### Alerting Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ CloudWatch      │───▶│ SNS Topics      │───▶│ Multiple        │
│ Alarms          │    │                 │    │ Destinations    │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Lambda errors │    │ • Cost alerts   │    │ • Email         │
│ • High duration │    │ • System health │    │ • Slack         │
│ • Failed alerts │    │ • Operational   │    │ • PagerDuty     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Network Architecture (Optional VPC Deployment)

### VPC Integration
```
┌─────────────────────────────────────────────────────────────────┐
│                           VPC                                   │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────┐  │
│  │ Private Subnet  │    │ Private Subnet  │    │   NAT GW    │  │
│  │      AZ-A       │    │      AZ-B       │    │             │  │
│  │                 │    │                 │    │             │  │
│  │ ┌─────────────┐ │    │                 │    │             │  │
│  │ │   Lambda    │ │    │                 │    │             │  │
│  │ │  Function   │ │    │                 │    │             │  │
│  │ └─────────────┘ │    │                 │    │             │  │
│  └─────────────────┘    └─────────────────┘    └─────────────┘  │
│                                                       │         │
└───────────────────────────────────────────────────────┼─────────┘
                                                        │
                                                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                      VPC Endpoints                              │
├─────────────────────────────────────────────────────────────────┤
│ • S3 Endpoint (Gateway)                                        │
│ • Secrets Manager Endpoint (Interface)                        │
│ • Cost Explorer Endpoint (Interface)                          │
│ • CloudWatch Logs Endpoint (Interface)                        │
└─────────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

### Multi-Environment Strategy
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Development    │    │    Staging      │    │   Production    │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Low threshold │    │ • Medium thresh │    │ • High threshold│
│ • Frequent runs │    │ • Daily runs    │    │ • Daily runs    │
│ • Test data     │    │ • Staging costs │    │ • Prod costs    │
│ • Dev Slack     │    │ • Team Slack    │    │ • Ops Slack     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Terraform State       │
                    │                         │
                    │ • Remote S3 backend     │
                    │ • DynamoDB locking      │
                    │ • Environment isolation │
                    │ • Version control       │
                    └─────────────────────────┘
```

## Cost Optimization Features

### Built-in Cost Controls
```
┌─────────────────────────────────────────────────────────────────┐
│                    Cost Optimization                            │
├─────────────────────────────────────────────────────────────────┤
│ Lambda Optimization:                                            │
│ • Right-sized memory allocation (256MB)                        │
│ • Efficient timeout settings (300s)                           │
│ • Reserved concurrency (prevents cost spikes)                 │
│                                                                │
│ S3 Optimization:                                               │
│ • Intelligent tiering                                          │
│ • Lifecycle policies (Standard → IA → Glacier)                │
│ • Automatic expiration (7 years)                              │
│                                                                │
│ API Optimization:                                              │
│ • Single daily Cost Explorer call                             │
│ • Efficient query parameters                                  │
│ • Minimal data transfer                                       │
└─────────────────────────────────────────────────────────────────┘
```

## Integration Points

### External Integrations
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Slack API     │    │  AWS APIs       │    │  Monitoring     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ • Webhook POST  │    │ • Cost Explorer │    │ • CloudWatch    │
│ • Rich messages │    │ • S3            │    │ • X-Ray tracing │
│ • Block kit     │    │ • Secrets Mgr   │    │ • Custom metrics│
│ • Error handling│    │ • CloudWatch    │    │ • Dashboards    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

This architecture provides a comprehensive view of the AWS Cost Optimization Dashboard, showing all components, data flows, security measures, and integration points in a scalable, maintainable, and cost-effective design.