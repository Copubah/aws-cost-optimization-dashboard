# AWS Cost Optimization Dashboard - Mermaid Diagrams

## System Architecture Flow

```mermaid
graph TB
    subgraph "AWS Account"
        EB[EventBridge<br/>Daily Cron Trigger<br/>8 AM UTC]
        LF[Lambda Function<br/>Python 3.11<br/>256MB / 300s]
        CE[Cost Explorer API<br/>Service-level costs<br/>Previous day data]
        S3[S3 Bucket<br/>Historical cost data<br/>JSON format]
        SM[Secrets Manager<br/>Slack webhook URL<br/>KMS encrypted]
        CW[CloudWatch Logs<br/>Function logs<br/>Error tracking]
    end
    
    subgraph "External"
        SL[Slack Channel<br/>Team notifications<br/>Rich alerts]
    end
    
    EB -->|Triggers| LF
    LF -->|Fetches costs| CE
    LF -->|Stores data| S3
    LF -->|Retrieves webhook| SM
    LF -->|Logs events| CW
    LF -->|Sends alerts| SL
    
    style EB fill:#ff9999
    style LF fill:#99ccff
    style CE fill:#99ff99
    style S3 fill:#ffcc99
    style SM fill:#cc99ff
    style SL fill:#ffff99
```

## Data Flow Sequence

```mermaid
sequenceDiagram
    participant EB as EventBridge
    participant LF as Lambda Function
    participant CE as Cost Explorer
    participant S3 as S3 Bucket
    participant SM as Secrets Manager
    participant SL as Slack
    participant CW as CloudWatch
    
    EB->>LF: Daily trigger (8 AM UTC)
    LF->>CW: Log: Starting cost collection
    LF->>CE: GetCostAndUsage (previous day)
    CE-->>LF: Cost data by service
    LF->>S3: Store raw cost data (JSON)
    LF->>LF: Process data & calculate totals
    LF->>CW: Log: Total daily cost
    
    alt Cost > Threshold
        LF->>SM: Get Slack webhook URL
        SM-->>LF: Encrypted webhook URL
        LF->>SL: Send formatted alert
        SL-->>LF: HTTP 200 OK
        LF->>CW: Log: Alert sent successfully
    else Cost <= Threshold
        LF->>CW: Log: Cost within threshold
    end
    
    LF-->>EB: Return success/failure
```

## Infrastructure Components

```mermaid
graph LR
    subgraph "Compute"
        LF[Lambda Function<br/>- Python 3.11<br/>- 256MB RAM<br/>- 300s timeout<br/>- Reserved concurrency: 1]
    end
    
    subgraph "Storage"
        S3[S3 Bucket<br/>- AES256 encryption<br/>- Versioning enabled<br/>- Lifecycle policies<br/>- 7-year retention]
    end
    
    subgraph "Security"
        IAM[IAM Role<br/>- Least privilege<br/>- Cost Explorer access<br/>- S3 write permissions<br/>- Secrets read access]
        SM[Secrets Manager<br/>- KMS encryption<br/>- Slack webhook URL<br/>- Automatic rotation]
    end
    
    subgraph "Scheduling"
        EB[EventBridge<br/>- Cron expression<br/>- Configurable schedule<br/>- Automatic retry<br/>- Dead letter queue]
    end
    
    subgraph "Monitoring"
        CW[CloudWatch<br/>- Function logs<br/>- Custom metrics<br/>- Error alarms<br/>- Performance tracking]
    end
    
    EB --> LF
    LF --> S3
    LF --> SM
    LF --> CW
    IAM --> LF
    
    style LF fill:#e1f5fe
    style S3 fill:#f3e5f5
    style IAM fill:#fff3e0
    style SM fill:#fff3e0
    style EB fill:#e8f5e8
    style CW fill:#fce4ec
```

## Security Architecture

```mermaid
graph TB
    subgraph "IAM Security Model"
        LR[Lambda Execution Role]
        
        subgraph "Permissions"
            CE_PERM[Cost Explorer<br/>- ce:GetCostAndUsage<br/>- ce:GetUsageReport]
            S3_PERM[S3 Permissions<br/>- s3:PutObject<br/>- s3:PutObjectAcl]
            SM_PERM[Secrets Manager<br/>- secretsmanager:GetSecretValue]
            CW_PERM[CloudWatch Logs<br/>- logs:CreateLogGroup<br/>- logs:CreateLogStream<br/>- logs:PutLogEvents]
        end
    end
    
    subgraph "Data Encryption"
        AT_REST[At Rest<br/>- S3: AES256<br/>- Secrets: KMS<br/>- Logs: CloudWatch]
        IN_TRANSIT[In Transit<br/>- HTTPS/TLS 1.2+<br/>- AWS API calls<br/>- Slack webhook]
    end
    
    subgraph "Network Security"
        VPC[VPC Deployment<br/>- Private subnets<br/>- VPC endpoints<br/>- Security groups<br/>- NACLs]
    end
    
    LR --> CE_PERM
    LR --> S3_PERM
    LR --> SM_PERM
    LR --> CW_PERM
    
    style LR fill:#ffebee
    style CE_PERM fill:#e3f2fd
    style S3_PERM fill:#e8f5e8
    style SM_PERM fill:#fff3e0
    style CW_PERM fill:#f3e5f5
```

## Cost Optimization Strategy

```mermaid
graph TD
    subgraph "Lambda Optimization"
        LO1[Right-sized Memory<br/>256MB optimal]
        LO2[Efficient Timeout<br/>300s maximum]
        LO3[Reserved Concurrency<br/>Prevents cost spikes]
    end
    
    subgraph "S3 Optimization"
        SO1[Lifecycle Policies<br/>Standard → IA → Glacier]
        SO2[Intelligent Tiering<br/>Automatic optimization]
        SO3[Data Expiration<br/>7-year retention]
    end
    
    subgraph "API Optimization"
        AO1[Single Daily Call<br/>Cost Explorer API]
        AO2[Efficient Queries<br/>Service-level grouping]
        AO3[Minimal Data Transfer<br/>Previous day only]
    end
    
    subgraph "Cost Monitoring"
        CM1[Daily Threshold Checks<br/>Configurable limits]
        CM2[Service-level Breakdown<br/>Identify cost drivers]
        CM3[Historical Trending<br/>Cost pattern analysis]
    end
    
    LO1 --> CM1
    SO1 --> CM2
    AO1 --> CM3
    
    style LO1 fill:#e1f5fe
    style SO1 fill:#f3e5f5
    style AO1 fill:#e8f5e8
    style CM1 fill:#fff3e0
```

## Multi-Environment Deployment

```mermaid
graph LR
    subgraph "Development"
        DEV_LF[Lambda Function<br/>- Low threshold: $25<br/>- Frequent testing<br/>- Dev Slack channel]
        DEV_S3[S3 Bucket<br/>dev-environment]
    end
    
    subgraph "Staging"
        STG_LF[Lambda Function<br/>- Medium threshold: $100<br/>- Daily runs<br/>- Team Slack channel]
        STG_S3[S3 Bucket<br/>staging-environment]
    end
    
    subgraph "Production"
        PROD_LF[Lambda Function<br/>- High threshold: $500<br/>- Daily runs<br/>- Ops Slack channel]
        PROD_S3[S3 Bucket<br/>prod-environment]
    end
    
    subgraph "Shared Infrastructure"
        TF_STATE[Terraform State<br/>- Remote S3 backend<br/>- DynamoDB locking<br/>- Environment isolation]
        CI_CD[CI/CD Pipeline<br/>- GitHub Actions<br/>- Automated testing<br/>- Security scanning]
    end
    
    DEV_LF --> TF_STATE
    STG_LF --> TF_STATE
    PROD_LF --> TF_STATE
    
    CI_CD --> DEV_LF
    CI_CD --> STG_LF
    CI_CD --> PROD_LF
    
    style DEV_LF fill:#e8f5e8
    style STG_LF fill:#fff3e0
    style PROD_LF fill:#ffebee
    style TF_STATE fill:#f3e5f5
    style CI_CD fill:#e1f5fe
```

## Alert Flow Decision Tree

```mermaid
flowchart TD
    START([Lambda Triggered]) --> FETCH[Fetch Cost Data]
    FETCH --> PROCESS[Process & Calculate Total]
    PROCESS --> STORE[Store in S3]
    STORE --> CHECK{Cost > Threshold?}
    
    CHECK -->|Yes| GET_WEBHOOK[Get Slack Webhook]
    CHECK -->|No| LOG_OK[Log: Within Threshold]
    
    GET_WEBHOOK --> FORMAT[Format Alert Message]
    FORMAT --> SEND[Send to Slack]
    SEND --> VERIFY{Slack Response OK?}
    
    VERIFY -->|Yes| LOG_SUCCESS[Log: Alert Sent]
    VERIFY -->|No| LOG_ERROR[Log: Alert Failed]
    
    LOG_OK --> END([Complete])
    LOG_SUCCESS --> END
    LOG_ERROR --> END
    
    style START fill:#e8f5e8
    style CHECK fill:#fff3e0
    style VERIFY fill:#fff3e0
    style END fill:#f3e5f5
    style LOG_ERROR fill:#ffebee
```

## Integration Architecture

```mermaid
graph TB
    subgraph "AWS Services"
        CE[Cost Explorer<br/>Billing data source]
        S3[S3<br/>Data storage]
        SM[Secrets Manager<br/>Secure config]
        CW[CloudWatch<br/>Monitoring & logs]
        EB[EventBridge<br/>Scheduling]
        LF[Lambda<br/>Core processing]
    end
    
    subgraph "External Services"
        SLACK[Slack<br/>Team notifications]
        GH[GitHub<br/>Source control & CI/CD]
    end
    
    subgraph "Infrastructure"
        TF[Terraform<br/>Infrastructure as Code]
        GHA[GitHub Actions<br/>CI/CD Pipeline]
    end
    
    LF <--> CE
    LF <--> S3
    LF <--> SM
    LF <--> CW
    EB --> LF
    LF --> SLACK
    
    TF --> CE
    TF --> S3
    TF --> SM
    TF --> CW
    TF --> EB
    TF --> LF
    
    GH --> GHA
    GHA --> TF
    
    style LF fill:#e1f5fe
    style SLACK fill:#ffff99
    style TF fill:#e8f5e8
    style GHA fill:#f3e5f5
```

These diagrams provide multiple perspectives on the AWS Cost Optimization Dashboard architecture, from high-level system flow to detailed security and deployment strategies. They can be rendered directly in GitHub README files and documentation platforms that support Mermaid syntax.