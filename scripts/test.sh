#!/bin/bash

# AWS Cost Optimization Dashboard - Test Script
set -e

echo "🧪 Testing AWS Cost Optimization Dashboard"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get Lambda function name from Terraform output
FUNCTION_NAME=$(terraform output -raw lambda_function_name 2>/dev/null || echo "")

if [ -z "$FUNCTION_NAME" ]; then
    echo -e "${RED}❌ Could not get Lambda function name. Make sure Terraform is deployed.${NC}"
    exit 1
fi

echo "Lambda function: $FUNCTION_NAME"

# Test Lambda function
echo -e "${YELLOW}Invoking Lambda function...${NC}"
aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --payload '{}' \
    response.json

# Check response
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Lambda function invoked successfully${NC}"
    echo ""
    echo -e "${YELLOW}Response:${NC}"
    cat response.json | python3 -m json.tool
    echo ""
else
    echo -e "${RED}❌ Lambda function invocation failed${NC}"
    exit 1
fi

# Check CloudWatch logs
echo -e "${YELLOW}Fetching recent CloudWatch logs...${NC}"
LOG_GROUP="/aws/lambda/$FUNCTION_NAME"

# Get the latest log stream
LATEST_STREAM=$(aws logs describe-log-streams \
    --log-group-name "$LOG_GROUP" \
    --order-by LastEventTime \
    --descending \
    --limit 1 \
    --query 'logStreams[0].logStreamName' \
    --output text 2>/dev/null || echo "")

if [ -n "$LATEST_STREAM" ] && [ "$LATEST_STREAM" != "None" ]; then
    echo "Latest log stream: $LATEST_STREAM"
    echo ""
    echo -e "${YELLOW}Recent log events:${NC}"
    aws logs get-log-events \
        --log-group-name "$LOG_GROUP" \
        --log-stream-name "$LATEST_STREAM" \
        --limit 10 \
        --query 'events[].message' \
        --output text
else
    echo -e "${YELLOW}No log streams found yet. The function may not have run.${NC}"
fi

# Check S3 bucket for cost data
echo ""
echo -e "${YELLOW}Checking S3 bucket for cost data...${NC}"
BUCKET_NAME=$(terraform output -raw s3_bucket_name 2>/dev/null || echo "")

if [ -n "$BUCKET_NAME" ]; then
    echo "S3 bucket: $BUCKET_NAME"
    
    # List recent cost data files
    aws s3 ls "s3://$BUCKET_NAME/cost_data/daily/" --recursive | tail -5 || {
        echo -e "${YELLOW}No cost data files found yet. This is normal for a new deployment.${NC}"
    }
else
    echo -e "${RED}❌ Could not get S3 bucket name${NC}"
fi

# Clean up response file
rm -f response.json

echo ""
echo -e "${GREEN}🎉 Testing completed!${NC}"
echo ""
echo -e "${YELLOW}Monitoring tips:${NC}"
echo "1. Check CloudWatch logs: aws logs tail /aws/lambda/$FUNCTION_NAME --follow"
echo "2. List S3 cost files: aws s3 ls s3://$BUCKET_NAME/cost_data/daily/ --recursive"
echo "3. View EventBridge rule: aws events describe-rule --name \$(terraform output -raw eventbridge_rule_name)"