"""
AWS Cost Optimization Dashboard - Lambda Handler
Collects daily cost data, stores in S3, and sends Slack alerts
"""

import boto3
import json
import datetime
import os
import urllib3
import logging
from typing import Dict

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Main Lambda handler function
    """
    try:
        # Initialize AWS clients
        s3_client = boto3.client('s3')
        ce_client = boto3.client('ce')
        secrets_client = boto3.client('secretsmanager')

        # Get environment variables
        bucket_name = os.environ['BUCKET_NAME']
        cost_threshold = float(os.environ.get('COST_THRESHOLD', 50.0))
        slack_secret_name = os.environ['SLACK_SECRET_NAME']
        environment = os.environ.get('ENVIRONMENT', 'dev')

        logger.info(f"Starting cost collection for environment: {environment}")
        logger.info(f"Cost threshold: ${cost_threshold}")

        # Get cost data from Cost Explorer
        cost_data = get_cost_data(ce_client)

        # Store cost data in S3
        s3_key = store_cost_data(s3_client, bucket_name, cost_data)
        logger.info(f"Cost data stored in S3: {s3_key}")

        # Process cost data and check threshold
        cost_summary = process_cost_data(cost_data)
        logger.info(f"Total daily cost: ${cost_summary['total_cost']:.2f}")

        # Send Slack alert if threshold exceeded
        if cost_summary['total_cost'] > cost_threshold:
            slack_webhook_url = get_slack_webhook(secrets_client, slack_secret_name)
            send_slack_alert(slack_webhook_url, cost_summary, cost_threshold, environment)
            alert_sent = True
        else:
            alert_sent = False
            logger.info(
                f"Cost ${cost_summary['total_cost']:.2f} within threshold ${cost_threshold:.2f}"
            )

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Cost collection completed successfully',
                'total_cost': cost_summary['total_cost'],
                'threshold': cost_threshold,
                'alert_sent': alert_sent,
                's3_key': s3_key
            })
        }

    except Exception as e:
        logger.error(f"Error in cost collection: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }


def get_cost_data(ce_client) -> Dict:
    """
    Fetch cost data from AWS Cost Explorer
    """
    # Calculate date range (yesterday's costs)
    today = datetime.date.today()
    start_date = (today - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')

    logger.info(f"Fetching cost data for period: {start_date} to {end_date}")

    try:
        response = ce_client.get_cost_and_usage(
            TimePeriod={
                'Start': start_date,
                'End': end_date
            },
            Granularity='DAILY',
            Metrics=['BlendedCost', 'UnblendedCost', 'UsageQuantity'],
            GroupBy=[
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        )

        return response

    except Exception as e:
        logger.error(f"Error fetching cost data: {str(e)}")
        raise


def store_cost_data(s3_client, bucket_name: str, cost_data: Dict) -> str:
    """
    Store cost data in S3 bucket
    """
    # Generate S3 key with timestamp
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d')
    s3_key = f"cost_data/daily/{timestamp}.json"

    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=json.dumps(cost_data, indent=2, default=str),
            ContentType='application/json'
        )

        return s3_key

    except Exception as e:
        logger.error(f"Error storing cost data in S3: {str(e)}")
        raise


def process_cost_data(cost_data: Dict) -> Dict:
    """
    Process cost data and extract key metrics
    """
    try:
        results = cost_data['ResultsByTime'][0]
        total_cost = float(results['Total']['BlendedCost']['Amount'])

        # Process service-level costs
        services = []
        for group in results.get('Groups', []):
            service_name = group['Keys'][0]
            service_cost = float(group['Metrics']['BlendedCost']['Amount'])

            if service_cost > 0:  # Only include services with actual costs
                services.append({
                    'name': service_name,
                    'cost': service_cost
                })

        # Sort services by cost (highest first)
        services.sort(key=lambda x: x['cost'], reverse=True)

        return {
            'total_cost': total_cost,
            'date': results['TimePeriod']['Start'],
            'services': services[:10],  # Top 10 services
            'service_count': len(services)
        }

    except Exception as e:
        logger.error(f"Error processing cost data: {str(e)}")
        raise


def get_slack_webhook(secrets_client, secret_name: str) -> str:
    """
    Retrieve Slack webhook URL from Secrets Manager
    """
    try:
        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])
        return secret_data['SLACK_WEBHOOK_URL']

    except Exception as e:
        logger.error(f"Error retrieving Slack webhook: {str(e)}")
        raise


def send_slack_alert(webhook_url: str, cost_summary: Dict, threshold: float, environment: str):
    """
    Send cost alert to Slack
    """
    try:
        # Format top services for display
        top_services = ""
        for i, service in enumerate(cost_summary['services'][:5], 1):
            top_services += f"{i}. {service['name']}: ${service['cost']:.2f}\n"

        # Create Slack message (removed emojis for professional appearance)
        message = {
            "text": f"AWS Cost Alert - {environment.upper()}",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"AWS Cost Alert - {environment.upper()}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Date:* {cost_summary['date']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Spend:* ${cost_summary['total_cost']:.2f}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Threshold:* ${threshold:.2f}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Overage:* ${cost_summary['total_cost'] - threshold:.2f}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Top 5 Services:*\n{top_services}"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Total services with costs: {cost_summary['service_count']}"
                        }
                    ]
                }
            ]
        }

        # Send to Slack
        http = urllib3.PoolManager()
        response = http.request(
            'POST',
            webhook_url,
            body=json.dumps(message),
            headers={'Content-Type': 'application/json'}
        )

        if response.status == 200:
            logger.info("Slack alert sent successfully")
        else:
            logger.error(f"Failed to send Slack alert: {response.status}")

    except Exception as e:
        logger.error(f"Error sending Slack alert: {str(e)}")
        raise
