# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-07-23

### Added

- Unit test suite: 24 tests covering all handler functions with mocked AWS clients.
  No AWS credentials required to run tests.
- Week-over-week cost delta: Lambda reads the prior week's S3 file and includes
  the percentage change in every Slack alert.
- SQS Dead Letter Queue wired to the Lambda dead_letter_config so failed
  invocations are captured rather than silently dropped.
- CloudWatch alarm on DLQ depth (fires when any message appears in the queue).
- CloudWatch alarm on Lambda errors (fires on any function error).
- AWS Budgets resources: one for actual monthly spend (alerts at 80% and 100%)
  and one for forecasted monthly spend (alert at 100%).
- IAM statements for sqs:SendMessage (DLQ) and s3:GetObject (week-over-week
  lookups), both scoped to specific resource ARNs.
- Checkov IaC security scan job in CI/CD pipeline with SARIF upload.
- pytest job added to CI/CD pipeline as a required step.
- Input validation on environment and cost_threshold variables.
- budget_alert_emails and monthly_budget_limit variables.

### Fixed

- send_slack_alert now raises RuntimeError on non-200 Slack responses instead of
  logging silently and returning HTTP 200. Failed deliveries now route to the DLQ.

### Changed

- CI/CD pipeline reorganised: python-checks job consolidates formatting, linting,
  and unit tests. Security scan split into separate checkov-scan and trivy-scan jobs.
- store_cost_data now keys files by the date of the data (yesterday) rather than
  the execution date to prevent off-by-one issues.

## [1.0.0] - 2024-01-15

### Added

- Initial release of the AWS Cost Optimization Dashboard.
- Terraform infrastructure: S3, Lambda, IAM, EventBridge, Secrets Manager,
  CloudWatch log group, and S3 lifecycle policies.
- Lambda function collecting daily cost data from Cost Explorer and posting to Slack.
- S3 bucket with AES256 encryption, versioning, and lifecycle transitions
  (Standard to IA at 30 days, Glacier at 90 days, expiration at 7 years).
- IAM role with least-privilege permissions scoped to specific resource ARNs.
- EventBridge cron rule for daily execution at 8 AM UTC.
- Configurable cost threshold via Terraform variable.
- Multi-environment support through the environment variable.
- CI/CD pipeline with Terraform validation, Black formatting, Flake8 linting,
  Trivy vulnerability scanning, and CodeQL upload.
- Deployment and setup shell scripts.
- Architecture diagrams and Mermaid flowcharts.
