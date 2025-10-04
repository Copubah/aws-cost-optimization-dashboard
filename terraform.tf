# AWS Cost Optimization Dashboard - Terraform Configuration
terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.1"
    }
  }
}

# Configure AWS Provider
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "AWS Cost Optimization Dashboard"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}