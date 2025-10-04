#!/bin/bash

# AWS Cost Optimization Dashboard - Setup Script
set -e

echo "🚀 AWS Cost Optimization Dashboard Setup"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install AWS CLI first.${NC}"
    exit 1
fi

# Check Terraform
if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform not found. Please install Terraform first.${NC}"
    exit 1
fi

# Check AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS credentials not configured. Please run 'aws configure' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Get Slack webhook URL
echo ""
echo -e "${YELLOW}Setting up Slack integration...${NC}"
read -p "Enter your Slack webhook URL: " SLACK_WEBHOOK_URL

if [ -z "$SLACK_WEBHOOK_URL" ]; then
    echo -e "${RED}❌ Slack webhook URL is required${NC}"
    exit 1
fi

# Create Slack webhook secret in AWS Secrets Manager
SECRET_NAME="slack/webhook/aws-cost-dashboard"
echo "Creating Slack webhook secret in AWS Secrets Manager..."

aws secretsmanager create-secret \
    --name "$SECRET_NAME" \
    --description "Slack webhook URL for AWS cost alerts" \
    --secret-string "{\"SLACK_WEBHOOK_URL\":\"$SLACK_WEBHOOK_URL\"}" \
    --region us-east-1 || {
    echo "Secret might already exist, updating..."
    aws secretsmanager update-secret \
        --secret-id "$SECRET_NAME" \
        --secret-string "{\"SLACK_WEBHOOK_URL\":\"$SLACK_WEBHOOK_URL\"}" \
        --region us-east-1
}

echo -e "${GREEN}✅ Slack webhook secret created/updated${NC}"

# Initialize Terraform
echo ""
echo -e "${YELLOW}Initializing Terraform...${NC}"
terraform init

# Validate Terraform configuration
echo -e "${YELLOW}Validating Terraform configuration...${NC}"
terraform validate

echo -e "${GREEN}✅ Terraform validation passed${NC}"

# Show Terraform plan
echo ""
echo -e "${YELLOW}Generating Terraform plan...${NC}"
terraform plan

echo ""
echo -e "${GREEN}🎉 Setup completed successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Review the Terraform plan above"
echo "2. Run 'terraform apply' to deploy the infrastructure"
echo "3. Test the Lambda function manually if needed"
echo ""
echo "Configuration:"
echo "- Environment: dev (default)"
echo "- Cost threshold: $50 (default)"
echo "- Schedule: Daily at 8 AM UTC"
echo ""
echo "To customize these settings, edit variables.tf or use terraform.tfvars"