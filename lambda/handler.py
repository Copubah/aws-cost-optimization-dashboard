"""
AWS Cost Optimization Dashboard - Lambda Handler

Collects daily cost data, stores in S3, computes week-over-week
delta, checks static threshold, and sends a rich Slack alert.
Failures in Slack delivery raise so the Lambda DLQ captures them.
"""

import boto3
import datetime
import json
import logging
import os
import urllib3
from typing import Dict, List, Optional

logger = logging.getLogger()
logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def lambda_handler(event, context):
    """Main Lambda handler."""
    s3_client = boto3.client("s3")
    ce_client = boto3.client("ce")
    secrets_client = boto3.client("secretsmanager")

    bucket_name = os.environ["BUCKET_NAME"]
    cost_threshold = float(os.environ.get("COST_THRESHOLD", 50.0))
    slack_secret_name = os.environ["SLACK_SECRET_NAME"]
    environment = os.environ.get("ENVIRONMENT", "dev")

    logger.info(
        f"Starting cost collection | env={environment} threshold=${cost_threshold}"
    )

    # Fetch and store yesterday's costs
    cost_data = get_cost_data(ce_client)
    s3_key = store_cost_data(s3_client, bucket_name, cost_data)
    logger.info(f"Cost data stored | s3_key={s3_key}")

    # Build today's summary
    cost_summary = process_cost_data(cost_data)
    logger.info(f"Total daily cost: ${cost_summary['total_cost']:.2f}")

    # Week-over-week comparison using data already in S3
    wow_delta = get_wow_delta(s3_client, bucket_name, cost_summary)

    # Alert if threshold exceeded
    alert_sent = False
    if cost_summary["total_cost"] > cost_threshold:
        webhook_url = get_slack_webhook(secrets_client, slack_secret_name)
        # Raises on non-200 so the DLQ captures failed deliveries
        send_slack_alert(
            webhook_url, cost_summary, cost_threshold, environment, wow_delta
        )
        alert_sent = True
        logger.info(
            f"Alert sent | cost=${cost_summary['total_cost']:.2f}"
            f" threshold=${cost_threshold:.2f}"
        )
    else:
        logger.info(
            f"Cost within threshold | cost=${cost_summary['total_cost']:.2f}"
            f" threshold=${cost_threshold:.2f}"
        )

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Cost collection completed successfully",
                "date": cost_summary["date"],
                "total_cost": cost_summary["total_cost"],
                "threshold": cost_threshold,
                "wow_delta_pct": wow_delta,
                "alert_sent": alert_sent,
                "s3_key": s3_key,
            }
        ),
    }


# ---------------------------------------------------------------------------
# Cost Explorer
# ---------------------------------------------------------------------------


def get_cost_data(ce_client) -> Dict:
    """Fetch yesterday's cost-and-usage data grouped by AWS service."""
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")

    logger.info(f"Fetching CE data | {start_date} -> {end_date}")

    return ce_client.get_cost_and_usage(
        TimePeriod={"Start": start_date, "End": end_date},
        Granularity="DAILY",
        Metrics=["BlendedCost", "UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
    )


# ---------------------------------------------------------------------------
# Data processing
# ---------------------------------------------------------------------------


def process_cost_data(cost_data: Dict) -> Dict:
    """Extract total cost and per-service breakdown from a CE response."""
    results = cost_data["ResultsByTime"][0]
    total_cost = float(results["Total"]["BlendedCost"]["Amount"])

    services: List[Dict] = []
    for group in results.get("Groups", []):
        service_cost = float(group["Metrics"]["BlendedCost"]["Amount"])
        if service_cost > 0:
            services.append({"name": group["Keys"][0], "cost": service_cost})

    services.sort(key=lambda x: x["cost"], reverse=True)

    return {
        "total_cost": total_cost,
        "date": results["TimePeriod"]["Start"],
        "services": services[:10],
        "service_count": len(services),
    }


def get_wow_delta(
    s3_client,
    bucket_name: str,
    cost_summary: Dict,
) -> Optional[float]:
    """
    Return week-over-week percentage change vs the same day last week.
    Returns None if last week's file does not exist yet.
    """
    try:
        report_date = datetime.date.fromisoformat(cost_summary["date"])
        last_week_date = (report_date - datetime.timedelta(days=7)).strftime("%Y-%m-%d")
        last_week_key = f"cost_data/daily/{last_week_date}.json"

        obj = s3_client.get_object(Bucket=bucket_name, Key=last_week_key)
        last_week_data = json.loads(obj["Body"].read())
        last_week_summary = process_cost_data(last_week_data)
        prior_cost = last_week_summary["total_cost"]

        if prior_cost == 0:
            return None

        delta_pct = ((cost_summary["total_cost"] - prior_cost) / prior_cost) * 100
        logger.info(
            f"WoW delta: ${prior_cost:.2f} -> ${cost_summary['total_cost']:.2f}"
            f" ({delta_pct:+.1f}%)"
        )
        return round(delta_pct, 1)

    except s3_client.exceptions.NoSuchKey:
        logger.info("No prior-week data available for WoW comparison")
        return None
    except Exception as e:
        # Non-fatal: alert still goes out without WoW context
        logger.warning(f"WoW delta calculation failed: {e}")
        return None


# ---------------------------------------------------------------------------
# S3 storage
# ---------------------------------------------------------------------------


def store_cost_data(s3_client, bucket_name: str, cost_data: Dict) -> str:
    """Persist the raw CE response to S3 as JSON."""
    today = datetime.date.today()
    yesterday = (today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    s3_key = f"cost_data/daily/{yesterday}.json"

    s3_client.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=json.dumps(cost_data, indent=2, default=str),
        ContentType="application/json",
    )
    return s3_key


# ---------------------------------------------------------------------------
# Secrets Manager
# ---------------------------------------------------------------------------


def get_slack_webhook(secrets_client, secret_name: str) -> str:
    """Retrieve the Slack webhook URL from Secrets Manager."""
    response = secrets_client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])["SLACK_WEBHOOK_URL"]


# ---------------------------------------------------------------------------
# Slack alerting
# ---------------------------------------------------------------------------


def build_wow_text(wow_delta: Optional[float]) -> str:
    """Return a human-readable WoW change string."""
    if wow_delta is None:
        return "N/A (first week of data)"
    direction = "up" if wow_delta > 0 else "down"
    return f"{direction} {abs(wow_delta):.1f}% vs same day last week"


def send_slack_alert(
    webhook_url: str,
    cost_summary: Dict,
    threshold: float,
    environment: str,
    wow_delta: Optional[float] = None,
) -> None:
    """
    Send a formatted cost alert to Slack.

    Raises RuntimeError if Slack returns a non-200 status so that
    the Lambda DLQ captures failed deliveries instead of silently
    dropping them.
    """
    top_services = "\n".join(
        f"{i}. {s['name']}: ${s['cost']:.2f}"
        for i, s in enumerate(cost_summary["services"][:5], 1)
    )

    overage = cost_summary["total_cost"] - threshold
    wow_text = build_wow_text(wow_delta)

    message = {
        "text": (
            f"[{environment.upper()}] AWS Cost Alert"
            f" - ${cost_summary['total_cost']:.2f}"
        ),
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"AWS Cost Alert - {environment.upper()}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Date:* {cost_summary['date']}"},
                    {
                        "type": "mrkdwn",
                        "text": f"*Total Spend:* ${cost_summary['total_cost']:.2f}",
                    },
                    {"type": "mrkdwn", "text": f"*Threshold:* ${threshold:.2f}"},
                    {"type": "mrkdwn", "text": f"*Overage:* ${overage:.2f}"},
                    {"type": "mrkdwn", "text": f"*Week-over-Week:* {wow_text}"},
                    {
                        "type": "mrkdwn",
                        "text": (
                            f"*Services with spend:* {cost_summary['service_count']}"
                        ),
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Top 5 Services:*\n{top_services}",
                },
            },
        ],
    }

    http = urllib3.PoolManager()
    response = http.request(
        "POST",
        webhook_url,
        body=json.dumps(message),
        headers={"Content-Type": "application/json"},
    )

    if response.status != 200:
        raise RuntimeError(
            f"Slack delivery failed | status={response.status}"
            f" body={response.data.decode()[:200]}"
        )

    logger.info("Slack alert delivered successfully")
