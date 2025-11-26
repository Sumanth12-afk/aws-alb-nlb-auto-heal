terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Backend configuration (optional - uncomment to use S3 backend)
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "auto-heal/terraform.tfstate"
  #   region = "us-east-1"
  # }
  # 
  # To use S3 backend, uncomment above and run:
  # terraform init -backend-config="bucket=your-bucket-name" -backend-config="key=auto-heal/terraform.tfstate" -backend-config="region=us-east-1"
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = "Dynamic-Auto-Heal"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

locals {
  project_name = "auto-heal"
  common_tags = {
    Project     = "Dynamic-Auto-Heal"
    Environment = var.environment
  }
}

