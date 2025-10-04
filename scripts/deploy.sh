#!/bin/bash

# AWS Cost Optimization Dashboard - Deployment Script
set -e

echo "🚀 Deploying AWS Cost Optimization Dashboard"
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse command line arguments
ENVIRONMENT="dev"
AUTO_APPROVE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -y|--auto-approve)
            AUTO_APPROVE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -e, --environment ENV    Set environment (default: dev)"
            echo "  -y, --auto-approve       Skip interactive approval"
            echo "  -h, --help              Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            exit 1
            ;;
    esac
done

echo "Environment: $ENVIRONMENT"

# Create terraform.tfvars if it doesn't exist
if [ ! -f terraform.tfvars ]; then
    echo -e "${YELLOW}Creating terraform.tfvars...${NC}"
    cat > terraform.tfvars << EOF
environment = "$ENVIRONMENT"
cost_threshold = 50.0
alert_schedule = "cron(0 8 * * ? *)"
EOF
    echo -e "${GREEN}✅ terraform.tfvars created${NC}"
fi

# Initialize Terraform if needed
if [ ! -d .terraform ]; then
    echo -e "${YELLOW}Initializing Terraform...${NC}"
    terraform init
fi

# Format Terraform files
echo -e "${YELLOW}Formatting Terraform files...${NC}"
terraform fmt

# Validate configuration
echo -e "${YELLOW}Validating Terraform configuration...${NC}"
terraform validate

# Plan deployment
echo -e "${YELLOW}Planning deployment...${NC}"
terraform plan -out=tfplan

# Apply deployment
if [ "$AUTO_APPROVE" = true ]; then
    echo -e "${YELLOW}Applying deployment (auto-approved)...${NC}"
    terraform apply tfplan
else
    echo -e "${YELLOW}Applying deployment...${NC}"
    terraform apply tfplan
fi

# Clean up plan file
rm -f tfplan

echo ""
echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo ""

# Show outputs
echo -e "${YELLOW}Deployment outputs:${NC}"
terraform output

echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Test the Lambda function: aws lambda invoke --function-name \$(terraform output -raw lambda_function_name) response.json"
echo "2. Check CloudWatch logs for any issues"
echo "3. Verify cost data appears in S3 bucket: \$(terraform output -raw s3_bucket_name)"
echo "4. Wait for the next scheduled run or trigger manually"