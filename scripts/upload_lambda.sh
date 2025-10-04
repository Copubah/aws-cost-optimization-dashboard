#!/bin/bash

# AWS Cost Optimization Dashboard - Lambda Deployment Script
set -e

echo "📦 Packaging Lambda function..."

# Create temporary directory for packaging
mkdir -p temp_lambda
cp -r lambda/* temp_lambda/

# Navigate to temp directory
cd temp_lambda

# Install dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt -t .

# Create deployment package
echo "Creating deployment package..."
zip -r ../lambda.zip . -x "*.pyc" "__pycache__/*"

# Cleanup
cd ..
rm -rf temp_lambda

echo "✅ Lambda package created: lambda.zip"
echo "Ready for Terraform deployment!"