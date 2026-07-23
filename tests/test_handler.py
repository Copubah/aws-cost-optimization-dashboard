"""
Unit tests for the Lambda cost collection handler.

Uses unittest.mock to avoid any real AWS or Slack calls.
Run with: pytest tests/ -v
"""

import json
import os
import sys
import pytest
from datetime import date, timedelta
from io import BytesIO
from unittest.mock import MagicMock, patch

# Add the lambda directory to sys.path because "lambda" is a reserved
# keyword in Python so it cannot be used as a package name for imports.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda"))

# Set required environment variables before importing the module
os.environ.setdefault("BUCKET_NAME", "test-bucket")
os.environ.setdefault("COST_THRESHOLD", "50.0")
os.environ.setdefault("SLACK_SECRET_NAME", "slack/test")
os.environ.setdefault("ENVIRONMENT", "test")

from handler import (  # noqa: E402
    build_wow_text,
    get_slack_webhook,
    get_wow_delta,
    process_cost_data,
    send_slack_alert,
    store_cost_data,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

YESTERDAY = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
TODAY = date.today().strftime("%Y-%m-%d")


def _ce_response(total: float, groups: list) -> dict:
    """Build a minimal Cost Explorer GetCostAndUsage response."""
    return {
        "ResultsByTime": [
            {
                "TimePeriod": {"Start": YESTERDAY, "End": TODAY},
                "Total": {"BlendedCost": {"Amount": str(total), "Unit": "USD"}},
                "Groups": groups,
            }
        ]
    }


def _group(service: str, cost: float) -> dict:
    return {
        "Keys": [service],
        "Metrics": {"BlendedCost": {"Amount": str(cost), "Unit": "USD"}},
    }


# ---------------------------------------------------------------------------
# process_cost_data
# ---------------------------------------------------------------------------


class TestProcessCostData:
    def test_total_cost_parsed_correctly(self):
        data = _ce_response(123.45, [])
        result = process_cost_data(data)
        assert result["total_cost"] == pytest.approx(123.45)

    def test_services_sorted_by_cost_descending(self):
        data = _ce_response(
            30.0,
            [
                _group("Amazon S3", 5.0),
                _group("Amazon EC2", 20.0),
                _group("AWS Lambda", 5.0),
            ],
        )
        result = process_cost_data(data)
        costs = [s["cost"] for s in result["services"]]
        assert costs == sorted(costs, reverse=True)

    def test_zero_cost_services_excluded(self):
        data = _ce_response(
            10.0,
            [_group("Amazon EC2", 10.0), _group("Amazon S3", 0.0)],
        )
        result = process_cost_data(data)
        names = [s["name"] for s in result["services"]]
        assert "Amazon S3" not in names

    def test_top_10_services_capped(self):
        groups = [_group(f"Service-{i}", float(i)) for i in range(1, 15)]
        data = _ce_response(100.0, groups)
        result = process_cost_data(data)
        assert len(result["services"]) == 10

    def test_date_field_matches_period_start(self):
        data = _ce_response(10.0, [])
        result = process_cost_data(data)
        assert result["date"] == YESTERDAY

    def test_service_count_reflects_nonzero_services(self):
        data = _ce_response(
            10.0,
            [_group("A", 5.0), _group("B", 0.0), _group("C", 5.0)],
        )
        result = process_cost_data(data)
        assert result["service_count"] == 2


# ---------------------------------------------------------------------------
# store_cost_data
# ---------------------------------------------------------------------------


class TestStoreCostData:
    def test_writes_to_correct_s3_key(self):
        s3 = MagicMock()
        data = _ce_response(10.0, [])
        key = store_cost_data(s3, "my-bucket", data)

        expected_key = f"cost_data/daily/{YESTERDAY}.json"
        assert key == expected_key
        s3.put_object.assert_called_once()
        call_kwargs = s3.put_object.call_args.kwargs
        assert call_kwargs["Bucket"] == "my-bucket"
        assert call_kwargs["Key"] == expected_key
        assert call_kwargs["ContentType"] == "application/json"

    def test_body_is_valid_json(self):
        s3 = MagicMock()
        data = _ce_response(42.0, [_group("EC2", 42.0)])
        store_cost_data(s3, "my-bucket", data)
        body = s3.put_object.call_args.kwargs["Body"]
        parsed = json.loads(body)
        assert "ResultsByTime" in parsed


# ---------------------------------------------------------------------------
# get_wow_delta
# ---------------------------------------------------------------------------


class TestGetWowDelta:
    def _last_week_key(self):
        report_date = date.fromisoformat(YESTERDAY)
        lw = (report_date - timedelta(days=7)).strftime("%Y-%m-%d")
        return f"cost_data/daily/{lw}.json"

    def test_returns_positive_delta_when_cost_increased(self):
        last_week_data = _ce_response(80.0, [_group("EC2", 80.0)])
        s3 = MagicMock()
        s3.get_object.return_value = {
            "Body": BytesIO(json.dumps(last_week_data).encode())
        }
        summary = {
            "total_cost": 100.0,
            "date": YESTERDAY,
            "services": [],
            "service_count": 0,
        }
        delta = get_wow_delta(s3, "bucket", summary)
        assert delta == pytest.approx(25.0)

    def test_returns_negative_delta_when_cost_decreased(self):
        last_week_data = _ce_response(100.0, [_group("EC2", 100.0)])
        s3 = MagicMock()
        s3.get_object.return_value = {
            "Body": BytesIO(json.dumps(last_week_data).encode())
        }
        summary = {
            "total_cost": 75.0,
            "date": YESTERDAY,
            "services": [],
            "service_count": 0,
        }
        delta = get_wow_delta(s3, "bucket", summary)
        assert delta == pytest.approx(-25.0)

    def test_returns_none_when_prior_file_missing(self):
        s3 = MagicMock()
        s3.get_object.side_effect = s3.exceptions.NoSuchKey = Exception("NoSuchKey")
        # Simulate S3 NoSuchKey by making get_object raise
        s3.exceptions = MagicMock()
        s3.exceptions.NoSuchKey = KeyError
        s3.get_object.side_effect = KeyError("NoSuchKey")
        summary = {
            "total_cost": 50.0,
            "date": YESTERDAY,
            "services": [],
            "service_count": 0,
        }
        delta = get_wow_delta(s3, "bucket", summary)
        assert delta is None

    def test_returns_none_when_prior_cost_is_zero(self):
        last_week_data = _ce_response(0.0, [])
        s3 = MagicMock()
        s3.get_object.return_value = {
            "Body": BytesIO(json.dumps(last_week_data).encode())
        }
        summary = {
            "total_cost": 50.0,
            "date": YESTERDAY,
            "services": [],
            "service_count": 0,
        }
        delta = get_wow_delta(s3, "bucket", summary)
        assert delta is None


# ---------------------------------------------------------------------------
# build_wow_text
# ---------------------------------------------------------------------------


class TestBuildWowText:
    def test_none_returns_first_week_message(self):
        assert "first week" in build_wow_text(None)

    def test_positive_delta_says_up(self):
        assert "up" in build_wow_text(15.5)

    def test_negative_delta_says_down(self):
        assert "down" in build_wow_text(-8.3)

    def test_percentage_is_formatted_in_output(self):
        text = build_wow_text(12.3)
        assert "12.3" in text


# ---------------------------------------------------------------------------
# get_slack_webhook
# ---------------------------------------------------------------------------


class TestGetSlackWebhook:
    def test_returns_webhook_url_from_secret(self):
        url = "https://hooks.slack.com/services/TEST"
        secrets = MagicMock()
        secrets.get_secret_value.return_value = {
            "SecretString": json.dumps({"SLACK_WEBHOOK_URL": url})
        }
        result = get_slack_webhook(secrets, "slack/test")
        assert result == url


# ---------------------------------------------------------------------------
# send_slack_alert
# ---------------------------------------------------------------------------


class TestSendSlackAlert:
    def _summary(self):
        return {
            "total_cost": 75.0,
            "date": YESTERDAY,
            "services": [{"name": "Amazon EC2", "cost": 60.0}],
            "service_count": 1,
        }

    @patch("handler.urllib3.PoolManager")
    def test_sends_post_to_webhook_url(self, mock_pm):
        mock_http = MagicMock()
        mock_pm.return_value = mock_http
        mock_http.request.return_value = MagicMock(status=200, data=b"ok")

        send_slack_alert("https://hooks.slack.com/test", self._summary(), 50.0, "prod")

        mock_http.request.assert_called_once()
        call_args = mock_http.request.call_args
        assert call_args.args[0] == "POST"
        assert call_args.args[1] == "https://hooks.slack.com/test"

    @patch("handler.urllib3.PoolManager")
    def test_raises_on_non_200_response(self, mock_pm):
        mock_http = MagicMock()
        mock_pm.return_value = mock_http
        mock_http.request.return_value = MagicMock(
            status=500, data=b"Internal Server Error"
        )

        with pytest.raises(RuntimeError, match="Slack delivery failed"):
            send_slack_alert(
                "https://hooks.slack.com/test", self._summary(), 50.0, "prod"
            )

    @patch("handler.urllib3.PoolManager")
    def test_message_body_is_valid_json(self, mock_pm):
        mock_http = MagicMock()
        mock_pm.return_value = mock_http
        mock_http.request.return_value = MagicMock(status=200, data=b"ok")

        send_slack_alert("https://hooks.slack.com/test", self._summary(), 50.0, "prod")

        body = mock_http.request.call_args.kwargs["body"]
        parsed = json.loads(body)
        assert "blocks" in parsed

    @patch("handler.urllib3.PoolManager")
    def test_wow_delta_included_in_message_when_provided(self, mock_pm):
        mock_http = MagicMock()
        mock_pm.return_value = mock_http
        mock_http.request.return_value = MagicMock(status=200, data=b"ok")

        send_slack_alert(
            "https://hooks.slack.com/test",
            self._summary(),
            50.0,
            "prod",
            wow_delta=12.5,
        )

        body = json.loads(mock_http.request.call_args.kwargs["body"])
        full_text = json.dumps(body)
        assert "12.5" in full_text

    @patch("handler.urllib3.PoolManager")
    def test_wow_none_shows_first_week_message(self, mock_pm):
        mock_http = MagicMock()
        mock_pm.return_value = mock_http
        mock_http.request.return_value = MagicMock(status=200, data=b"ok")

        send_slack_alert(
            "https://hooks.slack.com/test",
            self._summary(),
            50.0,
            "prod",
            wow_delta=None,
        )

        body = json.loads(mock_http.request.call_args.kwargs["body"])
        full_text = json.dumps(body)
        assert "first week" in full_text


# ---------------------------------------------------------------------------
# lambda_handler integration (mocked)
# ---------------------------------------------------------------------------


class TestLambdaHandler:
    @patch("handler.boto3.client")
    def test_returns_200_when_cost_below_threshold(self, mock_boto):
        ce = MagicMock()
        s3 = MagicMock()
        secrets = MagicMock()

        # Return clients in call order: s3, ce, secretsmanager
        mock_boto.side_effect = [s3, ce, secrets]

        ce.get_cost_and_usage.return_value = _ce_response(30.0, [_group("EC2", 30.0)])
        s3.put_object.return_value = {}
        # WoW lookup: last week file missing
        s3.get_object.side_effect = Exception("NoSuchKey")
        s3.exceptions = MagicMock()
        s3.exceptions.NoSuchKey = Exception

        from handler import lambda_handler

        result = lambda_handler({}, {})
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["alert_sent"] is False
        assert body["total_cost"] == pytest.approx(30.0)

    @patch("handler.boto3.client")
    @patch("handler.urllib3.PoolManager")
    def test_alert_sent_when_cost_exceeds_threshold(self, mock_pm, mock_boto):
        ce = MagicMock()
        s3 = MagicMock()
        secrets = MagicMock()
        mock_boto.side_effect = [s3, ce, secrets]

        mock_http = MagicMock()
        mock_pm.return_value = mock_http
        mock_http.request.return_value = MagicMock(status=200, data=b"ok")

        ce.get_cost_and_usage.return_value = _ce_response(80.0, [_group("EC2", 80.0)])
        s3.put_object.return_value = {}
        s3.get_object.side_effect = Exception("NoSuchKey")
        s3.exceptions = MagicMock()
        s3.exceptions.NoSuchKey = Exception
        secrets.get_secret_value.return_value = {
            "SecretString": json.dumps(
                {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}
            )
        }

        from handler import lambda_handler

        result = lambda_handler({}, {})
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["alert_sent"] is True
